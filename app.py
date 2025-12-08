import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI

# --- 1. アプリ設定 & DB初期化 ---
st.set_page_config(page_title="Owl v1.3", page_icon="🦉", layout="wide")

DB_PATH = "owl.db"

def init_db():
    """DBとテーブルの初期化"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # プロジェクト用
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
    # タスク用
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
    """指定プロジェクトのタスク一覧を取得"""
    conn = sqlite3.connect(DB_PATH)
    # ステータス順（TODO -> DOING -> DONE）に並べ替えるための工夫
    df = pd.read_sql(f"SELECT * FROM tasks WHERE project_id = '{project_id}' ORDER BY CASE status WHEN 'DOING' THEN 1 WHEN 'TODO' THEN 2 ELSE 3 END, created_at DESC", conn)
    conn.close()
    return df

def add_task(project_id, title, priority):
    """タスク追加"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO tasks (project_id, title, status, priority, created_at) VALUES (?, ?, 'TODO', ?, ?)",
              (project_id, title, priority, datetime.now()))
    conn.commit()
    conn.close()

def update_task_status(task_id, new_status):
    """ステータス更新"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE tasks SET status = ? WHERE task_id = ?", (new_status, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    """タスク削除"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
    conn.commit()
    conn.close()

# --- 3. UI構築 ---

st.title("🦉 Athenalink OS v1.3")

# サイドバー：APIキー & プロジェクト選択
st.sidebar.header("🔑 System Access")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")

st.sidebar.header("📂 Project Selector")
df_projects = get_projects()

if df_projects.empty:
    st.sidebar.warning("まだプロジェクトがありません。")
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

# --- 4. メイン画面 ---

if not current_project_id:
    st.info("👈 サイドバーからプロジェクトを作成してください。")
    st.stop()

# プロジェクト情報取得
conn = sqlite3.connect(DB_PATH)
current_project = pd.read_sql("SELECT * FROM projects WHERE project_id = ?", conn, params=(current_project_id,)).iloc[0]
conn.close()

# === 🏠 ダッシュボード ===
if menu == "🏠 ダッシュボード":
    st.header(f"Project: {current_project['name']}")
    
    # 基本情報
    with st.expander("ℹ️ プロジェクト詳細", expanded=False):
        st.write(f"**Goal:** {current_project['goal']}")
        st.write(f"**Domain:** {current_project['domain']}")
    
    st.markdown("---")
    
    # 今日のタスク（DOING または High priority の TODO）
    st.subheader("🔥 今日の最優先タスク")
    df_tasks = get_tasks(current_project_id)
    
    # フィルタリング：完了していないタスクを表示
    active_tasks = df_tasks[df_tasks['status'] != 'DONE']
    
    if not active_tasks.empty:
        for index, task in active_tasks.head(5).iterrows():
            # 色分け表示
            status_emoji = "🏃‍♂️" if task['status'] == 'DOING' else "📝"
            priority_color = "red" if task['priority'] == 'High' else "orange" if task['priority'] == 'Middle' else "green"
            
            st.markdown(f"**{status_emoji} [{task['status']}]** <span style='color:{priority_color}'>【{task['priority']}】</span> {task['title']}", unsafe_allow_html=True)
    else:
        st.success("🎉 現在、残っているタスクはありません！素晴らしい！")

# === ✅ タスク管理 (ToDo) ===
elif menu == "✅ タスク管理 (ToDo)":
    st.header("Task Management")
    
    # タスク追加フォーム
    with st.form("add_task_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            task_title = st.text_input("新しいタスク", placeholder="例：第1章の構成案を作る")
        with col2:
            task_priority = st.selectbox("優先度", ["High", "Middle", "Low"])
        with col3:
            add_submitted = st.form_submit_button("追加")
        
        if add_submitted and task_title:
            add_task(current_project_id, task_title, task_priority)
            st.rerun()

    # タスク一覧表示（編集可能）
    df_tasks = get_tasks(current_project_id)
    
    if not df_tasks.empty:
        # データエディタで表示（ここで直接ステータス変更可能にする）
        edited_df = st.data_editor(
            df_tasks[['task_id', 'status', 'priority', 'title']],
            column_config={
                "task_id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "status": st.column_config.SelectboxColumn("状態", options=["TODO", "DOING", "DONE"], required=True),
                "priority": st.column_config.SelectboxColumn("優先度", options=["High", "Middle", "Low"], required=True),
                "title": st.column_config.TextColumn("タスク内容", width="large"),
            },
            hide_index=True,
            use_container_width=True,
            key="task_editor"
        )
        
        # 変更検知とDB更新
        # （簡易実装：ボタンを押して保存ではなく、変更があれば即反映させたいが、
        #  Streamlitのdata_editorは差分取得が少し複雑なので、今回は「削除ボタン」のみ個別実装し、
        #  ステータス変更は次回のPhase 3で自動保存化を強化します。
        #  今の段階では「見た目上の管理」として機能します）
        
        # 削除ボタンの実装（各行に削除ボタンをつけるのは難しいので、ID指定削除）
        with st.expander("🗑 タスクの削除"):
            del_id = st.number_input("削除するタスクID", min_value=0, step=1)
            if st.button("削除実行"):
                delete_task(del_id)
                st.rerun()
    else:
        st.info("タスクがまだありません。「新しいタスク」を追加してください。")

# === 🧠 M4 参謀本部 ===
elif menu == "🧠 M4 参謀本部":
    st.header("参謀本部 (Strategy)")
    # M4コンテキスト注入
    STRATEGY_CONTEXT = f"""
    現在選択中のプロジェクト：{current_project['name']} ({current_project['domain']})
    目標：{current_project['goal']}
    役割：このプロジェクトの成功を導く参謀。
    """
    st.info(f"現在、**{current_project['name']}** の戦略会議中です。")
    # (チャット機能はPhase 3で復活・統合させます)
    st.write("💬 チャット機能はPhase 3でここに統合されます。")

# === その他のモジュール ===
else:
    st.header(menu)
    st.write(f"Project: {current_project['name']}")
    st.info("🚧 Phase 3で機能開放予定")
