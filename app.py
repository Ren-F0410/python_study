import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI

# --- 設定 ---
st.set_page_config(page_title="Owl v2.1", page_icon="🦉", layout="wide")
DB_PATH = "owl.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        project_id TEXT PRIMARY KEY, name TEXT, domain TEXT, goal TEXT,
        status TEXT DEFAULT 'active', created_at DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, title TEXT,
        status TEXT DEFAULT 'TODO', priority TEXT DEFAULT 'Middle', created_at DATETIME)''')
    conn.commit()
    conn.close()

init_db()

# --- 関数 ---
def get_projects():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM projects", conn)
    conn.close()
    return df

def create_project(p_id, name, domain, goal):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?)",
                  (p_id, name, domain, goal, 'active', datetime.now()))
        conn.commit()
        st.success(f"作成完了: {name}")
    except:
        st.error("IDが重複しています")
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
    c.execute("INSERT INTO tasks (project_id, title, status, priority, created_at) VALUES (?, ?, 'TODO', ?, ?)",
              (pid, title, prio, datetime.now()))
    conn.commit()
    conn.close()

def delete_task(tid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE task_id = ?", (tid,))
    conn.commit()
    conn.close()

# --- UI ---
st.title("🦉 Athenalink OS v2.1")
st.caption("Safe Mode: Professional Counselor")

st.sidebar.header("🔑 System Access")
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
    st.sidebar.success("✅ Auto-Login")
else:
    api_key = st.sidebar.text_input("API Key", type="password")

st.sidebar.header("📂 Projects")
df_projects = get_projects()

if df_projects.empty:
    st.warning("プロジェクトを作成してください")
    current_project_id = None
else:
    opts = {row['project_id']: row['name'] for i, row in df_projects.iterrows()}
    current_project_id = st.sidebar.selectbox("選択", options=list(opts.keys()), format_func=lambda x: opts[x])

with st.sidebar.expander("➕ 新規作成"):
    with st.form("new_proj"):
        new_id = st.text_input("ID (例: love01)")
        new_name = st.text_input("名前")
        new_domain = st.selectbox("分野", ["love_content", "owl_dev", "other"])
        new_goal = st.text_area("目標")
        if st.form_submit_button("作成") and new_id:
            create_project(new_id, new_name, new_domain, new_goal)
            st.rerun()

st.sidebar.header("🚀 Menu")
menu = st.sidebar.radio("Go to", ["🏠 Home", "✅ Tasks", "🧠 M4戦略", "📱 M1集客", "📝 M2制作", "💰 M3販売"])

# --- AI ---
STYLE = """
【Style Guide: Professional Counselor】
1. 自分語り禁止 (私の経験では〜NG)。
2. ポエム禁止。
3. 説教禁止。
4. 常に「受容(肯定)」→「分析(脳科学)」→「処方(解決策)」の流れで書く。
"""

prompts = {
    "M4": f"あなたは戦略参謀です。{STYLE} 目標達成のためのタスクを8-15個提案して。",
    "M1": f"あなたはSNS担当です。{STYLE} 読者の心を代弁するポストを3案作成して。",
    "M2": f"あなたは編集者です。{STYLE} 読者が納得する記事構成を作って。",
    "M3": f"あなたは解決型セールスライターです。{STYLE} 悩み(Problem)→分析(Affinity)→解決(Solution)→未来(Action)の順で、2000文字級のレターを書いて。"
}

if not current_project_id:
    st.stop()

conn = sqlite3.connect(DB_PATH)
p_data = pd.read_sql("SELECT * FROM projects WHERE project_id = ?", conn, params=(current_project_id,)).iloc[0]
conn.close()
p_info = f"Project: {p_data['name']}, Goal: {p_data['goal']}"

client = OpenAI(api_key=api_key) if api_key else None

def render_chat(role, prompt):
    if not client:
        st.warning("API Key needed")
        return
    
    key = f"chat_{current_project_id}_{role}"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": prompt + "\n" + p_info}]
        st.session_state[key].append({"role": "assistant", "content": "起動しました。"})
    
    for msg in st.session_state[key]:
        if msg["role"] != "system":
            st.chat_message(msg["role"]).write(msg["content"])
    
    st.markdown("---")
    # ★ここがエラーの原因だった箇所（短く修正済み）
    with st.form(key=f"form_{role}", clear_on_submit=True):
        user_input = st.text_area("指示を入力", height=150)
        send = st.form_submit_button("送信")
    
    if send and user_input:
        st.session_state[key].append({"role": "user", "content": user_input})
        try:
            with st.spinner("Writing..."):
                res = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=st.session_state[key],
                    temperature=0.7
                )
            st.session_state[key].append({"role": "assistant", "content": res.choices[0].message.content})
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- 画面 ---
if menu == "🏠 Home":
    st.header(p_data['name'])
    st.info(p_data['goal'])
elif menu == "✅ Tasks":
    st.header("Tasks")
    with st.form("add_t"):
        t = st.text_input("タスク")
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
elif menu == "🧠 M4戦略":
    render_chat("M4", prompts["M4"])
elif menu == "📱 M1集客":
    render_chat("M1", prompts["M1"])
elif menu == "📝 M2制作":
    render_chat("M2", prompts["M2"])
elif menu == "💰 M3販売":
    render_chat("M3", prompts["M3"])
