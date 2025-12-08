import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI

# --- 1. アプリ設定 & DB初期化 ---
st.set_page_config(page_title="Owl v1.3", page_icon="🦉", layout="wide")

DB_PATH = "owl.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            project_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            domain TEXT,
            goal TEXT,
            status TEXT DEFAULT 'active',
            created_at DATETIME
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            title TEXT,
            status TEXT DEFAULT 'TODO',
            priority TEXT DEFAULT 'Middle',
            created_at DATETIME
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- 2. データ操作関数 ---

def get_projects():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM projects", conn)
    conn.close()
    return df

def create_project(p_id, name, domain, goal):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO projects (project_id, name, domain, goal, created_at) VALUES (?, ?, ?, ?, ?)",
                  (p_id, name, domain, goal, datetime.now()))
        conn.commit()
        st.success(f"✅ プロジェクト『{name}』を作成しました！")
    except sqlite3.IntegrityError:
        st.error("⚠️ そのIDは既に使用されています。")
    except Exception as e:
        st.error(f"エラー: {e}")
    finally:
        conn.close()

def get_tasks(project_id):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(f"SELECT * FROM tasks WHERE project_id = '{project_id}' ORDER BY CASE status WHEN 'DOING' THEN 1 WHEN 'TODO' THEN 2 ELSE 3 END, priority DESC, created_at DESC", conn)
    conn.close()
    return df

def add_task(project_id, title, priority):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO tasks (project_id, title, status, priority, created_at) VALUES (?, ?, 'TODO', ?, ?)",
              (project_id, title, priority, datetime.now()))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
    conn.commit()
    conn.close()

# --- 3. UI構築 ---

st.title("🦉 Athenalink OS v1.3")

# サイドバー
st.sidebar.header("🔑 System Access")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")

st.sidebar.header("📂 Project Selector")
df_projects = get_projects()

if df_projects.empty:
    st.sidebar.warning("プロジェクトを作成してください")
    current_project_id = None
else:
    project_options = {row['project_id']: f"{row['name']}" for index, row in df_projects.iterrows()}
    current_project_id = st.sidebar.selectbox(
        "現在のプロジェクト",
        options=list(project_options.keys()),
        format_func=lambda x: project_options[x]
    )

with st.sidebar.expander("➕ 新規プロジェクト作成"):
    with st.form("create_project_form"):
        new_id = st.text_input("ID", placeholder="love_note_01")
        new_name = st.text_input("プロジェクト名")
        new_domain = st.selectbox("事業ドメイン", ["love_content", "owl_dev", "marketing", "other"])
        new_goal = st.text_area("目標")
        submitted = st.form_submit_button("作成")
        if submitted and new_id and new_name:
            create_project(new_id, new_name, new_domain, new_goal)
            st.rerun()

st.sidebar.header("🚀 Modules")
menu = st.sidebar.radio("Menu", [
    "🏠 ダッシュボード",
    "✅ タスク管理 (ToDo)",
    "🧠 M4 参謀本部",
    "📱 M1 SNS集客",
    "📝 M2 記事制作",
    "💰 M3 セールス"
])

# --- 4. メイン処理 & モジュール統合 ---

if not current_project_id:
    st.stop()

# プロジェクト情報ロード
conn = sqlite3.connect(DB_PATH)
project_data = pd.read_sql("SELECT * FROM projects WHERE project_id = ?", conn, params=(current_project_id,)).iloc[0]
conn.close()

p_name = project_data['name']
p_goal = project_data['goal']
p_domain = project_data['domain']

# === AIクライアント準備 ===
client = None
if api_key:
    client = OpenAI(api_key=api_key)

# === 共通チャット機能 ===
def render_chat(module_name, system_prompt):
    if not client:
        st.warning("👈 サイドバーにAPIキーを入力してください")
        return

    # 履歴キーを (プロジェクトID + モジュール名) で一意にする
    session_key = f"chat_{current_project_id}_{module_name}"
    
    if session_key not in st.session_state:
        st.session_state[session_key] = [{"role": "system", "content": system_prompt}]
        # 初回挨拶
        greeting = "起動しました。指示をください。"
        if module_name == "M4": greeting = f"参謀モード起動。プロジェクト『{p_name}』の戦略について相談しましょう。"
        if module_name == "M1": greeting = f"SNSモード起動。『{p_name}』のターゲットに向けた発信を作ります。"
        st.session_state[session_key].append({"role": "assistant", "content": greeting})

    # チャット表示
    for msg in st.session_state[session_key]:
        if msg["role"] != "system":
            st.chat_message(msg["role"]).write(msg["content"])

    # 入力
    user_input = st.chat_input("ここに入力...")
    if user_input:
        st.chat_message("user").write(user_input)
        st.session_state[session_key].append({"role": "user", "content": user_input})
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=st.session_state[session_key]
            )
            ai_text = response.choices[0].message.content
            st.chat_message("assistant").write(ai_text)
            st.session_state[session_key].append({"role": "assistant", "content": ai_text})
        except Exception as e:
            st.error(f"エラー: {e}")

# === 各画面 ===

if menu == "🏠 ダッシュボード":
    st.header(f"Project: {p_name}")
    with st.expander("ℹ️ プロジェクト目標を確認", expanded=True):
        st.info(f"**GOAL:** {p_goal}")
    
    st.subheader("🔥 今日のタスク (High Priority)")
    df_tasks = get_tasks(current_project_id)
    active_tasks = df_tasks[(df_tasks['status'] != 'DONE') & (df_tasks['priority'] == 'High')]
    
    if not active_tasks.empty:
        for _, task in active_tasks.head(3).iterrows():
            st.warning(f"□ {task['title']}")
    else:
        st.success("High優先度のタスクはありません。")

elif menu == "✅ タスク管理 (ToDo)":
    st.header("Task Management")
    with st.form("add_task_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        t_title = c1.text_input("タスク追加")
        t_prio = c2.selectbox("優先度", ["High", "Middle", "Low"])
        if c3.form_submit_button("追加") and t_title:
            add_task(current_project_id, t_title, t_prio)
            st.rerun()

    df_tasks = get_tasks(current_project_id)
    if not df_tasks.empty:
        edited_df = st.data_editor(
            df_tasks[['task_id', 'status', 'priority', 'title']],
            column_config={
                "task_id": st.column_config.NumberColumn("ID", width="small"),
                "status": st.column_config.SelectboxColumn("状態", options=["TODO", "DOING", "DONE"], required=True),
                "title": st.column_config.TextColumn("タスク", width="large"),
            },
            hide_index=True,
            use_container_width=True,
            key="task_editor_v2" # keyを変更してリセット
        )
        with st.expander("🗑 削除ツール"):
            del_id = st.number_input("IDを指定して削除", step=1)
            if st.button("削除"):
                delete_task(del_id)
                st.rerun()
    else:
        st.info("タスクなし")

elif menu == "🧠 M4 参謀本部":
    st.header("Strategy Room (M4)")
    
    # === ここが統合のキモ！プロジェクト情報を注入 ===
    m4_prompt = f"""
    あなたはプロジェクト『{p_name}』の参謀です。
    【プロジェクト目標】{p_goal}
    【ドメイン】{p_domain}
    
    上記を前提に、具体的かつ戦略的なアドバイスをしてください。
    タスクを提案する際は、優先度（High/Middle/Low）も示唆してください。
    """
    
    # 画面分割：左にチャット、右にタスク登録
    col_chat, col_tool = st.columns([2, 1])
    
    with col_chat:
        render_chat("M4", m4_prompt)
        
    with col_tool:
        st.markdown("### ⚡️ Quick Task Add")
        st.caption("チャットで出た案をここにコピペして登録！")
        with st.form("quick_task_m4"):
            q_title = st.text_input("タスク名")
            q_prio = st.selectbox("優先度", ["High", "Middle", "Low"], key="q_m4")
            if st.form_submit_button("登録"):
                add_task(current_project_id, q_title, q_prio)
                st.success("登録しました！")

elif menu == "📱 M1 SNS集客":
    st.header("SNS Creator (M1)")
    m1_prompt = f"""
    プロジェクト『{p_name}』のSNS担当です。
    ターゲットに向けて、{p_domain}に関する共感・有益ポストを作成してください。
    目標：{p_goal}
    """
    render_chat("M1", m1_prompt)

elif menu == "📝 M2 記事制作":
    st.header("Editor Room (M2)")
    m2_prompt = f"""
    プロジェクト『{p_name}』の専属編集者です。
    noteなどの長文コンテンツの構成、執筆、リライトを行います。
    目標：{p_goal}
    """
    render_chat("M2", m2_prompt)

elif menu == "💰 M3 セールス":
    st.header("Sales Writer (M3)")
    m3_prompt = f"""
    プロジェクト『{p_name}』のセールスライターです。
    {p_goal}を達成するため、PASONAの法則を用いて、
    読み手の感情を揺さぶる販売文章を作成してください。
    """
    render_chat("M3", m3_prompt)
