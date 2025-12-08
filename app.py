import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI

# --- 1. 設定 ---
st.set_page_config(page_title="Owl v2.5", page_icon="🦉", layout="wide")

DB_PATH = "owl.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS projects ("
        "project_id TEXT PRIMARY KEY, name TEXT, domain TEXT, goal TEXT, "
        "status TEXT DEFAULT 'active', created_at DATETIME)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS tasks ("
        "task_id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, title TEXT, "
        "status TEXT DEFAULT 'TODO', priority TEXT DEFAULT 'Middle', created_at DATETIME)"
    )
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
        c.execute(
            "INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?)",
            (p_id, name, domain, goal, 'active', datetime.now())
        )
        conn.commit()
        st.success(f"プロジェクト『{name}』を作成しました")
    except:
        st.error("エラー: IDが重複しています")
    finally:
        conn.close()

def get_tasks(pid):
    conn = sqlite3.connect(DB_PATH)
    q = f"SELECT * FROM tasks WHERE project_id = '{pid}' ORDER BY status DESC, priority DESC"
    df = pd.read_sql(q, conn)
    conn.close()
    return df

def add_task(pid, title, prio):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO tasks (project_id, title, status, priority, created_at) "
        "VALUES (?, ?, 'TODO', ?, ?)",
        (pid, title, prio, datetime.now())
    )
    conn.commit()
    conn.close()

def delete_task(tid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE task_id = ?", (tid,))
    conn.commit()
    conn.close()

# --- 3. UI設計 ---
st.title("🦉 Athenalink OS v2.5")
st.caption("Quality Tuned: Deep Empathy & High Conversion Mode")

# サイドバー：APIキー
st.sidebar.header("🔑 System Access")
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
    st.sidebar.success("✅ Auto-Login Active")
else:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")

st.sidebar.header("📂 Project Selector")
df_projects = get_projects()

if df_projects.empty:
    st.sidebar.warning("プロジェクトを作成してください")
    current_project_id = None
else:
    opts = {row['project_id']: row['name'] for i, row in df_projects.iterrows()}
    current_project_id = st.sidebar.selectbox(
        "現在のプロジェクト", 
        options=list(opts.keys()), 
        format_func=lambda x: opts[x]
    )

with st.sidebar.expander("➕ 新規プロジェクト作成"):
    with st.form("new_proj"):
        new_id = st.text_input("ID (例: love01)")
        new_name = st.text_input("プロジェクト名")
        new_domain = st.selectbox("事業ドメイン", ["love_content", "owl_dev", "marketing"])
        new_goal = st.text_area("目標")
        if st.form_submit_button("作成") and new_id:
            create_project(new_id, new_name, new_domain, new_goal)
            st.rerun()

st.sidebar.header("🚀 Modules")
menu = st.sidebar.radio(
    "モード選択", 
    ["🏠 ダッシュボード", "✅ タスク管理", "🧠 M4 参謀本部", "📱 M1 SNS集客", "📝 M2 記事制作", "💰 M3 セールス"]
)

# --- 4. AI脳（日本語・高品質プロンプト） ---

# 基本スタイル（改行対策済み）
STYLE = (
    "【Style Guide: Professional Counselor】\n"
    "1. 言語: 必ず日本語で出力すること。\n"
    "2. 禁止: 自分語り、ポエム、説教。\n"
    "3. 構成: 受容(肯定)→分析(脳科学)→処方(解決策)。\n"
    "4. 態度: 冷静で温かいプロフェッショナル。\n"
)

prompts = {
    "M4": (
        f"あなたは戦略参謀です。{STYLE}"
        "目標達成のための具体的タスクを8〜15個提案してください。"
    ),
    "M1": (
        f"あなたはSNS担当です。{STYLE}"
        "読者の心を代弁するポストを3案(各140文字)作成してください。"
    ),
    "M2": (
        f"あなたは編集者です。{STYLE}"
        "読者が納得する記事構成(見出し5-10個)を作成してください。"
    ),
    "M3": (
        f"あなたは解決型セールスライターです。{STYLE}"
        "以下のPASONA構成で2000文字級のレターを書いてください。\n"
        "1. Problem: 現状の苦しみを言語化\n"
        "2. Affinity: 脳の仕組みとして解説(自分語り禁止)\n"
        "3. Solution: メソッドの提示\n"
        "4. Action: 未来への導き"
    )
}

if not current_project_id:
    st.stop()

# プロジェクト情報ロード
conn = sqlite3.connect(DB_PATH)
p_data = pd.read_sql("SELECT * FROM projects WHERE project_id = ?", conn, params=(current_project_id,)).iloc[0]
conn.close()

p_name = project_data['name']
p_goal = project_data['goal']
p_domain = project_data['domain']

client = OpenAI(api_key=api_key) if api_key else None

def render_chat(role, prompt):
    if not client:
        st.warning("API Keyを入力してください")
        return

    session_key = f"chat_{current_project_id}_{role}"
    
    if session_key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": prompt + "\n" + p_info}]
        st.session_state[key].append({"role": "assistant", "content": "起動しました。指示をください。"})
    
    for msg in st.session_state[key]:
        if msg["role"] != "system":
            st.chat_message(msg["role"]).write(msg["content"])
    
    st.markdown("---")
    # 入力フォーム（バグ修正済み）
    with st.form(key=f"form_{role}", clear_on_submit=True):
        user_input = st.text_area("指示を入力 (Enterで改行)", height=150)
        send = st.form_submit_button("送信")
    
    if send and user_input:
        st.session_state[key].append({"role": "user", "content": user_input})
        
        # 思考プロセスを追加 (v1.5/v2.0)
        thinking_instruction = """
        【思考プロセス】
        回答を出力する前に、以下のステップで内容を構築してください（思考過程は出力せず、結果のみを出力すること）。
        1. 感情エミュレーション: ターゲット読者の「痛み」を具体的に想像する。
        2. 具体化: 抽象的な言葉を、映像的な言葉に変換する。
        3. Style Guideに違反していないかチェックする（説教になっていないか？）。
        4. 指定された文字数（M1なら140字、M3なら1200字以上）を満たす構成を組む。
        5. 執筆する。
        """
        
        messages_for_api = st.session_state[key].copy()
        messages_for_api[-1]["content"] += thinking_instruction

        try:
            with st.spinner("Owl v2.5 is thinking..."):
                res = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages_for_api,
                    temperature=0.7,
                    max_tokens=3000
                )
            st.session_state[key].append({"role": "assistant", "content": res.choices[0].message.content})
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- 5. 画面表示 ---
if menu == "🏠 ダッシュボード":
    st.header(f"プロジェクト: {p_data['name']}")
    st.info(p_data['goal'])
    st.subheader("🔥 今日のタスク")
    d = get_tasks(current_project_id)
    if not d.empty:
        st.dataframe(d, use_container_width=True)
    else:
        st.write("タスクなし")

elif menu == "✅ タスク管理":
    st.header("タスク管理")
    with st.form("add_t", clear_on_submit=True):
        t = st.text_input("タスク名")
        p = st.selectbox("優先度", ["High", "Middle"])
        if st.form_submit_button("追加"):
            add_task(current_project_id, t, p)
            st.rerun()
    d = get_tasks(current_project_id)
    if not d.empty:
        st.data_editor(d, key="deditor")
        with st.expander("削除"):
            did = st.number_input("ID", step=1)
            if st.button("削除"):
                delete_task(did)
                st.rerun()

elif menu == "🧠 M4 参謀本部":
    render_chat("M4", prompts["M4"])
elif menu == "📱 M1 SNS集客":
    render_chat("M1", prompts["M1"])
elif menu == "📝 M2 記事制作":
    render_chat("M2", prompts["M2"])
elif menu == "💰 M3 セールス":
    render_chat("M3", prompts["M3"])
