import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI
import base64
import time

# --- 1. アプリ設定 & Gemini風デザイン ---
st.set_page_config(page_title="Owl v3.1", page_icon="🦉", layout="wide")

# カスタムCSS (Gemini Style)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
    
    :root {
        --bg-color: #ffffff; /* 背景：白 */
        --sidebar-bg: #f0f4f9; /* サイドバー：薄いグレー（Gemini風） */
        --input-bg: #f0f4f9; /* 入力欄背景：薄いグレー */
        --text-color: #1f1f1f; /* 文字色：ほぼ黒 */
        --primary-accent: #0056d2; /* アクセント：Geminiブルー */
        --border-radius: 24px; /* 丸み */
    }

    html, body, [class*="css"] {
        font-family: 'Noto Sans JP', sans-serif;
        color: var(--text-color);
        background-color: var(--bg-color);
    }

    /* 全体の背景 */
    .stApp {
        background-color: var(--bg-color);
        background-image: none; /* 画像なし、シンプルに */
    }

    /* --- サイドバー --- */
    [data-testid="stSidebar"] {
        background-color: var(--sidebar-bg);
        border-right: none;
    }
    [data-testid="stSidebar"] * {
        color: var(--text-color) !important;
    }
    
    /* --- 入力欄 (Gemini風) --- */
    /* テキスト入力、エリア、セレクトボックス */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        background-color: var(--input-bg) !important;
        color: var(--text-color) !important;
        -webkit-text-fill-color: var(--text-color) !important;
        caret-color: var(--text-color) !important;
        border: 1px solid transparent !important; /* 枠線なし */
        border-radius: 20px !important; /* Geminiのような丸み */
        padding: 15px 20px !important;
        font-size: 16px !important;
    }
    
    /* 入力時のフォーカス（青い枠ではなく、背景を少し濃くする感じor枠線を出す） */
    .stTextInput input:focus, .stTextArea textarea:focus {
        background-color: #e8ecf2 !important; /* フォーカス時に少し濃く */
        border: 1px solid #d0d7de !important;
        box-shadow: none !important;
    }

    /* --- ヘッダー --- */
    .main-header {
        background: transparent;
        padding: 1rem 0;
        margin-bottom: 2rem;
        border-bottom: 1px solid #eee;
    }
    .main-header h1 {
        color: var(--text-color) !important;
        font-size: 2.2rem;
        font-weight: 500;
        letter-spacing: -0.05rem;
    }
    .main-header p {
        color: #555555 !important;
        font-size: 1rem;
    }

    /* --- ボタン --- */
    div.stButton > button {
        background-color: var(--input-bg);
        color: var(--text-color);
        border: none;
        border-radius: 24px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #dbe0e8; /* ホバー時のグレー */
        color: #000;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* 送信ボタンの特別色（もし必要なら） */
    /* div.stButton > button:active {
        background-color: #0056d2;
        color: white;
    }
    */

    /* --- カードデザイン --- */
    .card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 16px;
        margin-bottom: 1rem;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    
    /* ログインボックス */
    .login-box {
        background-color: #ffffff;
        padding: 40px;
        border-radius: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        text-align: center;
        border: 1px solid #f0f0f0;
    }
    
    /* チャットメッセージのスタイル */
    /* ユーザー（右） */
    [data-testid="stChatMessage"]:nth-child(odd) {
        background-color: transparent; 
    }
    /* アシスタント（左） */
    [data-testid="stChatMessage"]:nth-child(even) {
        background-color: transparent;
    }
    
    /* タグ */
    span[data-baseweb="tag"] {
        background-color: #e0e4e9 !important;
    }
    span[data-baseweb="tag"] span {
        color: #1f1f1f !important;
    }
</style>
""", unsafe_allow_html=True)

DB_PATH = "owl_v3.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, name TEXT, role TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS projects (project_id TEXT PRIMARY KEY, name TEXT, goal TEXT, created_at DATETIME)")
    c.execute("CREATE TABLE IF NOT EXISTS tasks (task_id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, title TEXT, assignee TEXT, status TEXT DEFAULT 'TODO', priority TEXT, created_at DATETIME)")
    c.execute("CREATE TABLE IF NOT EXISTS team_chat (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, message TEXT, created_at DATETIME)")
    c.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, module TEXT, content TEXT, rating TEXT, created_at DATETIME)")
    c.execute("INSERT OR IGNORE INTO users VALUES ('ren', 'Ren', 'Owner')")
    c.execute("INSERT OR IGNORE INTO users VALUES ('shu', 'Shu', 'Member')")
    conn.commit()
    conn.close()

init_db()

# --- 2. データ関数 ---
def get_user_name(uid):
    conn = sqlite3.connect(DB_PATH)
    res = conn.execute("SELECT name FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    return res[0] if res else uid

def get_tasks(uid=None):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM tasks WHERE status != 'DONE' "
    params = []
    if uid:
        query += "AND assignee = ? "
        params.append(uid)
    query += "ORDER BY priority DESC, created_at DESC"
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def add_task(pid, title, assignee, prio):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO tasks (project_id, title, assignee, status, priority, created_at) VALUES (?, ?, ?, 'TODO', ?, ?)", (pid, title, assignee, prio, datetime.now()))
    conn.commit()
    conn.close()

def complete_task(tid):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE tasks SET status='DONE' WHERE task_id=?", (tid,))
    conn.commit()
    conn.close()

def send_team_chat(uid, msg):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO team_chat (user_id, message, created_at) VALUES (?, ?, ?)", (uid, msg, datetime.now()))
    conn.commit()
    conn.close()

def get_team_chat():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM team_chat ORDER BY created_at DESC LIMIT 50", conn)
    conn.close()
    return df

def save_feedback(pid, module, content, rating):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO feedback (project_id, module, content, rating, created_at) VALUES (?, ?, ?, ?, ?)", (pid, module, content, rating, datetime.now()))
    conn.commit()
    conn.close()
    st.toast(f"Feedback saved: {rating}")

# --- 3. ログイン処理 ---
if 'user' not in st.session_state:
    st.session_state['user'] = None

if not st.session_state['user']:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
        <div class="login-box">
            <h1>🦉 Owl v3.1</h1>
            <p>Athenalink Director AI</p>
        </div>
        <br>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            uid = st.selectbox("ユーザーを選択", ["ren", "shu"])
            if st.form_submit_button("ログイン"):
                st.session_state['user'] = uid
                st.rerun()
    st.stop()

current_user = st.session_state['user']
user_name = get_user_name(current_user)

# --- 4. メインUI ---

# サイドバー
st.sidebar.markdown(f"## 👤 {user_name}")
if st.sidebar.button("ログアウト"):
    st.session_state['user'] = None
    st.rerun()

st.sidebar.markdown("---")
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")

# メニュー名もシンプルに
menu = st.sidebar.radio("MENU", ["ダッシュボード", "チームチャット", "キャンペーン設計", "戦略 (Owl)", "SNS運用", "セールス"])

client = OpenAI(api_key=api_key) if api_key else None

# OwlチャットUI
def render_owl_chat(mode, system_prompt):
    if not client: st.warning("API Key Required"); return
    
    st.markdown(f"### {mode}")
    key = f"chat_{current_user}_{mode}"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": system_prompt}]
        st.session_state[key].append({"role": "assistant", "content": "準備完了。指示をください。"})
    
    for i, msg in enumerate(st.session_state[key]):
        if msg["role"] != "system":
            # シンプルなアイコン表示
            avatar = "🦉" if msg["role"] == "assistant" else "👤"
            with st.chat_message(msg["role"], avatar=avatar):
                st.write(msg["content"])
                if msg["role"] == "assistant" and i > 0:
                    c1, c2 = st.columns([1, 10])
                    with c1:
                        if st.button("👍", key=f"up_{key}_{i}"): save_feedback("GEN", mode, msg["content"], "good")
                    with c2:
                        if st.button("👎", key=f"down_{key}_{i}"): save_feedback("GEN", mode, msg["content"], "bad")
    
    st.markdown("---")
    # Gemini風の入力フォーム
    with st.form(key=f"form_{mode}", clear_on_submit=True):
        # テキストエリアの高さを少し抑え、丸みのあるCSSを適用済み
        prompt = st.text_area("Owlにメッセージを送信 (Enterで改行)", height=80, label_visibility="collapsed")
        c1, c2 = st.columns([6, 1])
        with c2:
            st.write("") # スペース調整
            submit = st.form_submit_button("送信")
    
    if submit and prompt:
        st.session_state[key].append({"role": "user", "content": prompt})
        
        try:
            with st.spinner("Generating..."):
                stream = client.chat.completions.create(model="gpt-3.5-turbo", messages=st.session_state[key], stream=True)
                response_text = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        response_text += chunk.choices[0].delta.content
                
                st.session_state[key].append({"role": "assistant", "content": response_text})
                st.rerun()
        except Exception as e: st.error(str(e))

# コンテンツ
if menu == "ダッシュボード":
    st.markdown(f"""
    <div class="main-header">
        <h1>Hello, {user_name}</h1>
        <p>Athenalink Operation System</p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 今日のタスク")
        my_tasks = get_tasks(current_user).head(3)
        if not my_tasks.empty:
            for i, task in my_tasks.iterrows():
                st.markdown(f'<div class="card"><b>{task["title"]}</b> <span style="float:right; color:#d9534f;">{task["priority"]}</span></div>', unsafe_allow_html=True)
                if st.button("完了", key=f"d_{task['task_id']}"): complete_task(task['task_id']); st.rerun()
        else: st.info("タスクはありません")
            
    with c2:
        st.markdown("#### チームチャット")
        chats = get_team_chat().head(3)
        for i, chat in chats.iterrows():
            st.caption(f"{chat['user_id']} • {chat['created_at']}")
            st.markdown(f'<div class="card" style="padding:10px; background-color:#f9f9f9; border:none;">{chat["message"]}</div>', unsafe_allow_html=True)

elif menu == "チームチャット":
    st.markdown("### Team Chat")
    
    with st.form("chat_form", clear_on_submit=True):
        c1, c2 = st.columns([5, 1])
        # Gemini風入力
        msg = c1.text_area("メッセージを入力...", height=60, label_visibility="collapsed")
        with c2:
            st.write("")
            submit = st.form_submit_button("送信")
        
        if submit and msg:
            send_team_chat(current_user, msg)
            st.rerun()
    
    chats = get_team_chat()
    for i, chat in chats.iterrows():
        is_me = chat['user_id'] == current_user
        align = "text-align: right;" if is_me else ""
        # 自分のメッセージは薄い青（Gemini風）、相手はグレー
        bg = "#e8f0fe" if is_me else "#f1f3f4"
        
        st.markdown(f"""
        <div style="{align} margin-bottom: 10px;">
            <small style="color:#666;">{chat['user_id']}</small><br>
            <span style="background-color: {bg}; color: #1f1f1f; padding: 10px 16px; border-radius: 18px; display: inline-block;">
                {chat['message']}
            </span>
        </div>
        """, unsafe_allow_html=True)

elif menu == "キャンペーン設計":
    st.markdown("### Campaign Planner")
    
    with st.form("campaign_form"):
        c1, c2 = st.columns(2)
        goal = c1.text_input("目的", "例：note販売")
        period = c2.selectbox("期間", ["7日間", "14日間"])
        media = st.multiselect("媒体", ["X", "note", "LINE"], default=["X"])
        
        st.write("")
        submitted = st.form_submit_button("計画を生成")
        
    if submitted:
        prompt = f"目的：{goal}、期間：{period}、媒体：{media} の計画を作成せよ。"
        render_owl_chat("Planner", prompt)
    else:
        render_owl_chat("Planner", "マーケティングプランナーです。")

elif menu == "戦略 (Owl)": render_owl_chat("M4 Strategy", "戦略参謀です。")
elif menu == "SNS運用": render_owl_chat("M1 SNS", "SNS担当です。")
elif menu == "セールス": render_owl_chat("M3 Sales", "セールスライターです。")
