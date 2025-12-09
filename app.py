import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI
import base64
import time

# --- 1. アプリ設定 & デザイン完全刷新 ---
st.set_page_config(page_title="Owl v3.0", page_icon="🦉", layout="wide")

# カスタムCSS (UI Final Adjustments)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
    
    :root {
        --bg-pink-pale: #fff3f5;
        --bg-pink-muted: #f3e0e6;
        --input-bg-dark: #2b2b2b; /* 入力欄の背景（黒） */
        --input-text-white: #ffffff; /* 入力欄の文字（白） */
        --text-black: #333333; /* 通常の文字（黒） */
        --sidebar-text: #ffffff; /* サイドバー文字（白） */
    }

    html, body, [class*="css"] {
        font-family: 'Noto Sans JP', sans-serif;
        color: var(--text-black);
    }

    /* 背景: 日本画風の桜イメージ */
    .stApp {
        background-color: var(--bg-pink-pale);
        background-image: radial-gradient(circle at 10% 20%, rgba(255, 255, 255, 0.8) 0%, rgba(255, 240, 245, 0.6) 90%);
        background-attachment: fixed;
    }

    /* --- サイドバー --- */
    [data-testid="stSidebar"] {
        background-color: #d8aeb7; /* 少し濃いピンクにして白文字を映えさせる */
        border-right: 1px solid #fff;
    }
    /* サイドバー内の全テキストを白にする */
    [data-testid="stSidebar"] * {
        color: var(--sidebar-text) !important;
    }
    /* サイドバー内の入力欄も統一 */
    [data-testid="stSidebar"] input {
        background-color: var(--input-bg-dark) !important;
        color: var(--input-text-white) !important;
    }

    /* --- 入力欄の統一 (黒背景・白文字・丸枠) --- */
    /* テキスト入力、エリア、セレクトボックス全てに適用 */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        background-color: var(--input-bg-dark) !important;
        color: var(--input-text-white) !important;
        -webkit-text-fill-color: var(--input-text-white) !important; /* Safari対策 */
        caret-color: var(--input-text-white) !important;
        border: 1px solid #555 !important;
        border-radius: 25px !important; /* 強い丸み */
        padding: 12px 15px !important;
    }
    
    /* セレクトボックスの中身（ドロップダウン） */
    div[data-baseweb="popover"] div {
        background-color: var(--input-bg-dark) !important;
        color: var(--input-text-white) !important;
    }
    /* セレクトボックスの表示文字 */
    div[data-baseweb="select"] div {
        color: var(--input-text-white) !important;
    }

    /* --- ヘッダー --- */
    .main-header {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(5px);
        padding: 1.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        border: 1px solid white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .main-header h1 { margin: 0; font-size: 2rem; color: #333 !important; }
    .main-header p { margin-top: 0.5rem; color: #555 !important; }

    /* --- ボタン --- */
    div.stButton > button {
        background-color: #ffffff;
        color: #333333;
        border: none;
        border-radius: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: all 0.2s;
        font-weight: bold;
    }
    div.stButton > button:hover {
        background-color: #fff0f5;
        transform: translateY(-2px);
    }

    /* --- カードデザイン --- */
    .card {
        background-color: rgba(255,255,255,0.85);
        padding: 1.2rem;
        border-radius: 20px;
        margin-bottom: 10px;
        border: 1px solid white;
        color: #333; /* カード内の文字は黒 */
    }
    
    /* ログイン画面 */
    .login-box {
        background: rgba(255,255,255,0.9);
        padding: 40px;
        border-radius: 30px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        text-align: center;
        border: 1px solid #fff;
    }
    
    /* タグの色調整 */
    span[data-baseweb="tag"] {
        background-color: #2b2b2b !important;
        border: 1px solid #555 !important;
    }
    span[data-baseweb="tag"] span {
        color: #ffffff !important;
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

# サイドバー (文字色はCSSで白に指定済み)
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
        st.session_state[key].append({"role": "assistant", "content": f"{user_name}さん、準備完了です。指示をください。"})
    
    for i, msg in enumerate(st.session_state[key]):
        if msg["role"] != "system":
            # ロボットではなく「Owl」アイコンを使用
            avatar = "🦉" if msg["role"] == "assistant" else "👤"
            with st.chat_message(msg["role"], avatar=avatar):
                st.write(msg["content"])
                if msg["role"] == "assistant" and i > 0:
                    c1, c2 = st.columns([1, 10])
                    with c1:
                        if st.button("👍", key=f"up_{key}_{i}"): save_feedback("GEN", mode, msg["content"], "good")
                    with c2:
                        if st.button("👎", key=f"down_{key}_{i}"): save_feedback("GEN", mode, msg["content"], "bad")
    
    # 入力欄 (Enterで改行、Ctrl+Enterで送信にするため text_area + form を使用)
    st.markdown("---")
    with st.form(key=f"form_{mode}", clear_on_submit=True):
        # 高さを少し広げて入力しやすく
        prompt = st.text_area("指示を入力 (Enterで改行)", height=100)
        c1, c2 = st.columns([6, 1])
        with c2:
            submit = st.form_submit_button("送信")
    
    if submit and prompt:
        st.session_state[key].append({"role": "user", "content": prompt})
        # ユーザー発言を即時反映（リラン前に表示）
        # st.rerun() するとフォームの仕様上消えてしまうため、ここでは処理を継続
        
        try:
            with st.spinner("Owl is thinking..."):
                stream = client.chat.completions.create(model="gpt-3.5-turbo", messages=st.session_state[key], stream=True)
                # ストリーミング表示はst.write_streamを使うが、rerunとの兼ね合いが難しいため一括取得
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
                # カード内の文字色は黒で見やすく
                st.markdown(f'<div class="card"><b>{task["title"]}</b> <span style="float:right; color:red;">{task["priority"]}</span></div>', unsafe_allow_html=True)
                if st.button("完了", key=f"d_{task['task_id']}"): complete_task(task['task_id']); st.rerun()
        else: st.info("タスクなし")
            
    with c2:
        st.markdown("### チームチャット (最新)")
        chats = get_team_chat().head(3)
        for i, chat in chats.iterrows():
            st.caption(f"{chat['user_id']} ({chat['created_at']})")
            st.markdown(f'<div class="card" style="padding:10px;">{chat["message"]}</div>', unsafe_allow_html=True)
            st.markdown("---")

elif menu == "チームチャット":
    st.markdown("### Team Room")
    
    # チームチャット入力欄もテキストエリアに変更（Enter誤爆防止）
    with st.form("chat_form", clear_on_submit=True):
        c1, c2 = st.columns([4, 1])
        # 黒背景・白文字のテキストエリア
        msg = c1.text_area("メッセージ (Enterで改行)", height=60)
        with c2:
            st.write("") # スペース調整
            st.write("")
            submit = st.form_submit_button("送信")
        
        if submit and msg:
            send_team_chat(current_user, msg)
            st.rerun()
    
    chats = get_team_chat()
    for i, chat in chats.iterrows():
        is_me = chat['user_id'] == current_user
        align = "text-align: right;" if is_me else ""
        # 吹き出しの背景と文字色調整
        bg = "#f3e0e6" if is_me else "#ffffff"
        text_col = "#333333" # 吹き出し内の文字は黒
        
        st.markdown(f"""
        <div style="{align} margin-bottom: 10px;">
            <small style="color:#666;">{chat['user_id']}</small><br>
            <span style="background-color: {bg}; color: {text_col}; padding: 8px 12px; border-radius: 15px; display: inline-block; border: 1px solid #ccc; text-align: left;">
                {chat['message']}
            </span>
        </div>
        """, unsafe_allow_html=True)

elif menu == "キャンペーン設計":
    st.markdown("### Campaign Planner")
    
    # 全ての入力欄が「黒背景・白文字・丸枠」になっています
    with st.form("campaign_form"):
        c1, c2, c3 = st.columns(3)
        goal = c1.text_input("目的", "note販売")
        period = c2.selectbox("期間", ["7日間", "14日間"])
        media = c3.multiselect("媒体", ["X", "note", "LINE"], default=["X"])
        
        submitted = st.form_submit_button("計画を自動生成する")
        
    if submitted:
        prompt = f"目的：{goal}、期間：{period}、媒体：{media} の計画を作成せよ。"
        render_owl_chat("Planner", prompt)
    else:
        render_owl_chat("Planner", "あなたはマーケティングプランナーです。")

elif menu == "戦略 (Owl)": render_owl_chat("M4 Strategy", "戦略参謀です。")
elif menu == "SNS運用": render_owl_chat("M1 SNS", "SNS担当です。")
elif menu == "セールス": render_owl_chat("M3 Sales", "セールスライターです。")
