import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI
import base64
import time

# --- 1. アプリ設定 & デザイン完全刷新 ---
st.set_page_config(page_title="Owl v3.0", page_icon="🦉", layout="wide")

# カスタムCSS (UI Perfect Edition)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
    
    :root {
        --bg-pink-pale: #fff3f5;
        --bg-pink-muted: #f3e0e6;
        --text-black: #333333;
        --border-color: #e0c0d0;
        --chat-input-bg: #2b2b2b; /* チャット入力欄の背景（黒系） */
        --chat-input-text: #ffffff; /* チャット入力欄の文字（白系） */
    }

    html, body, [class*="css"] {
        font-family: 'Noto Sans JP', sans-serif;
        color: var(--text-black);
    }

    /* 背景: 日本画風の桜イメージ (グラデーションで表現) */
    .stApp {
        background-color: var(--bg-pink-pale);
        background-image: radial-gradient(circle at 10% 20%, rgba(255, 255, 255, 0.8) 0%, rgba(255, 240, 245, 0.6) 90%);
        background-attachment: fixed;
    }

    /* ヘッダー */
    .main-header {
        background: rgba(255, 255, 255, 0.6);
        backdrop-filter: blur(5px);
        padding: 1.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        border: 1px solid white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .main-header h1 { margin: 0; font-size: 2rem; color: #333 !important; }
    .main-header p { margin-top: 0.5rem; color: #555 !important; }

    /* --- 1. 一般的な入力欄 (白背景・黒文字) --- */
    /* プロジェクト名やタスク名など */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        background-color: #ffffff !important;
        color: #333333 !important;
        -webkit-text-fill-color: #333333 !important;
        caret-color: #333333 !important;
        border: 1px solid #d0d0d0 !important;
        border-radius: 25px !important; /* ChatGPT風の強い丸み */
        padding: 10px 15px !important;
    }
    /* 選択肢の文字色 */
    div[data-baseweb="select"] div { color: #333333 !important; }

    /* --- 2. チャット入力欄 & チームチャット入力 (黒背景・白文字) --- */
    /* 統一感を出すために特定のクラスを指定 */
    .chat-style-input input, .stChatInput textarea {
        background-color: var(--chat-input-bg) !important;
        color: var(--chat-input-text) !important;
        -webkit-text-fill-color: var(--chat-input-text) !important;
        caret-color: var(--chat-input-text) !important;
        border: none !important;
        border-radius: 25px !important;
    }
    /* チャット入力の送信ボタン */
    .stChatInput button { color: #ffffff !important; }

    /* --- 3. マルチセレクトのタグ (Xなど) --- */
    span[data-baseweb="tag"] {
        background-color: #ffffff !important; /* 白系 */
        border: 1px solid #ccc !important;
    }
    span[data-baseweb="tag"] span {
        color: #333333 !important; /* 文字は黒（反対色） */
    }

    /* サイドバー */
    [data-testid="stSidebar"] {
        background-color: var(--bg-pink-muted);
        border-right: 1px solid #fff;
    }
    [data-testid="stSidebar"] * { color: #333333 !important; }

    /* ボタン */
    div.stButton > button {
        background-color: #ffffff;
        color: #333333;
        border: none;
        border-radius: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        background-color: #fff0f5;
    }

    /* カードデザイン */
    .card {
        background-color: rgba(255,255,255,0.8);
        padding: 1.2rem;
        border-radius: 20px;
        margin-bottom: 10px;
        border: 1px solid white;
    }
    
    /* ログイン画面のボックス */
    .login-box {
        background: rgba(255,255,255,0.9);
        padding: 40px;
        border-radius: 30px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        text-align: center;
        border: 1px solid #fff;
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
    st.toast(f"評価を保存: {rating}")

# --- 3. ログイン処理 ---
if 'user' not in st.session_state:
    st.session_state['user'] = None

if not st.session_state['user']:
    # ログイン画面デザイン統一
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
        <div class="login-box">
            <h1 style="color:#333;">🦉 Owl v3.0</h1>
            <p style="color:#666;">Athenalink Director AI</p>
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
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg["role"] == "assistant" and i > 0:
                    c1, c2 = st.columns([1, 10])
                    with c1:
                        if st.button("👍", key=f"up_{key}_{i}"): save_feedback("GEN", mode, msg["content"], "good")
                    with c2:
                        if st.button("👎", key=f"down_{key}_{i}"): save_feedback("GEN", mode, msg["content"], "bad")
    
    # チャット入力欄 (CSSで黒背景・白文字・赤枠なしに調整済)
    if prompt := st.chat_input("指示を入力 (Enterで送信)..."):
        st.session_state[key].append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        
        with st.chat_message("assistant"):
            try:
                stream = client.chat.completions.create(model="gpt-3.5-turbo", messages=st.session_state[key], stream=True)
                response = st.write_stream(stream)
                st.session_state[key].append({"role": "assistant", "content": response})
            except Exception as e: st.error(str(e))

# コンテンツ
if menu == "ダッシュボード":
    st.markdown(f"""
    <div class="main-header">
        <h1>🦉 Owl v3.0</h1>
        <p>Welcome back, <b>{user_name}</b>.</p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 今日のタスク")
        my_tasks = get_tasks(current_user).head(3)
        if not my_tasks.empty:
            for i, task in my_tasks.iterrows():
                st.markdown(f'<div class="card"><b>{task["title"]}</b> <span style="float:right; color:red;">{task["priority"]}</span></div>', unsafe_allow_html=True)
                if st.button("完了", key=f"d_{task['task_id']}"): complete_task(task['task_id']); st.rerun()
        else: st.info("タスクなし")
            
    with c2:
        st.markdown("### チームチャット (最新)")
        chats = get_team_chat().head(3)
        for i, chat in chats.iterrows():
            st.caption(f"{chat['user_id']} ({chat['created_at']})")
            st.write(chat['message'])
            st.markdown("---")

elif menu == "チームチャット":
    st.markdown("### Team Room")
    
    # ここもOwlチャットと同じ「黒背景・白文字」にするためのクラス適用
    # Streamlitの仕様上、完全に同じ見た目にするために text_input にCSSクラスを当てるのは難しいが、
    # 可能な限り統一感を出すため、独自のコンテナで囲むか、標準スタイルでいくか。
    # 要望通り「連絡事項」欄も黒背景白文字にトライします。
    
    st.markdown('<div class="chat-style-input">', unsafe_allow_html=True)
    with st.form("chat_form", clear_on_submit=True):
        c1, c2 = st.columns([4, 1])
        # 黒背景にするためCSSで指定したクラスが効くように調整
        msg = c1.text_input("メッセージ", placeholder="連絡事項を入力...", label_visibility="collapsed")
        if c2.form_submit_button("送信") and msg:
            send_team_chat(current_user, msg)
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    chats = get_team_chat()
    for i, chat in chats.iterrows():
        is_me = chat['user_id'] == current_user
        align = "text-align: right;" if is_me else ""
        bg = "#f3e0e6" if is_me else "#ffffff" 
        st.markdown(f"""
        <div style="{align} margin-bottom: 10px;">
            <small style="color:#666;">{chat['user_id']}</small><br>
            <span style="background-color: {bg}; padding: 8px 12px; border-radius: 15px; display: inline-block; border: 1px solid #ddd; color: #333;">
                {chat['message']}
            </span>
        </div>
        """, unsafe_allow_html=True)

elif menu == "キャンペーン設計":
    st.markdown("### Campaign Planner")
    c1, c2, c3 = st.columns(3)
    # 一般入力欄は白背景・黒文字（見やすさ優先）
    goal = c1.text_input("目的", "note販売")
    period = c2.selectbox("期間", ["7日間", "14日間"])
    # Xなどのタグは白背景・黒文字に変更済
    media = c3.multiselect("媒体", ["X", "note", "LINE"], default=["X"])
    
    if st.button("計画を自動生成する"):
        prompt = f"目的：{goal}、期間：{period}、媒体：{media} の計画を作成せよ。"
        render_owl_chat("Planner", prompt)
    else:
        render_owl_chat("Planner", "あなたはマーケティングプランナーです。")

elif menu == "戦略 (Owl)": render_owl_chat("M4 Strategy", "戦略参謀です。")
elif menu == "SNS運用": render_owl_chat("M1 SNS", "SNS担当です。")
elif menu == "セールス": render_owl_chat("M3 Sales", "セールスライターです。")
