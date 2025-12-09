import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI
import base64
import time

# --- 1. アプリ設定 & デザイン刷新 ---
st.set_page_config(page_title="Owl v3.0", page_icon="🦉", layout="wide")

# カスタムCSS (文字色修正版)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
    
    :root {
        --bg-pink-pale: #fff3f5;
        --bg-pink-muted: #f3e0e6;
        --text-black: #333333;
        --border-color: #e0c0d0;
    }

    html, body, [class*="css"] {
        font-family: 'Noto Sans JP', sans-serif;
        color: var(--text-black);
    }

    /* 背景設定 */
    .stApp {
        background-color: var(--bg-pink-pale);
        background-image: linear-gradient(to bottom, rgba(255,243,245,0.9), rgba(255,255,255,0.6));
        background-attachment: fixed;
        background-size: cover;
    }

    /* ヘッダー */
    .main-header {
        background: rgba(255, 255, 255, 0.85);
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        border: 1px solid var(--border-color);
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .main-header h1 {
        color: #333333 !important;
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    }
    .main-header p {
        color: #555555 !important;
        margin-top: 0.5rem;
        font-size: 1rem;
    }

    /* --- 重要：入力欄の文字色修正 --- */
    /* テキスト入力、エリア、セレクトボックスの文字を強制的に黒くする */
    .stTextInput input, .stTextArea textarea {
        color: #333333 !important;
        -webkit-text-fill-color: #333333 !important;
        caret-color: #333333 !important;
        background-color: #ffffff !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 15px !important;
    }
    
    /* セレクトボックスの選択値 */
    .stSelectbox div[data-baseweb="select"] div {
        color: #333333 !important;
        -webkit-text-fill-color: #333333 !important;
    }
    
    /* チャット入力欄 */
    .stChatInput textarea {
        background-color: #ffffff !important;
        color: #333333 !important;
        border-radius: 20px !important;
    }

    /* サイドバー */
    [data-testid="stSidebar"] {
        background-color: var(--bg-pink-muted);
        border-right: 1px solid var(--border-color);
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span {
        color: #333333 !important;
    }

    /* ボタン */
    div.stButton > button {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid var(--border-color);
        border-radius: 20px;
        font-weight: bold;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #e0c0d0;
        border-color: #333333;
    }
    
    /* カード */
    .card {
        background-color: rgba(255, 255, 255, 0.9);
        padding: 1rem;
        border-radius: 15px;
        margin-bottom: 10px;
        border: 1px solid var(--border-color);
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

# --- 3. ログイン処理 ---
if 'user' not in st.session_state:
    st.session_state['user'] = None

if not st.session_state['user']:
    # ログイン画面の表記追加
    st.markdown("""
    <div style='text-align: center; margin-top: 50px; background: rgba(255,255,255,0.8); padding: 30px; border-radius: 20px;'>
        <h1>🦉 Owl v3.0</h1>
        <p>Director AI for Athenalink</p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.form("login_form"):
            uid = st.selectbox("ユーザーを選択してください", ["ren", "shu"])
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
# APIキー設定（サイドバーの最初に入力欄を配置）
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password", help="ここにAPIキーを入力")

menu = st.sidebar.radio("MENU", ["ダッシュボード", "チームチャット", "キャンペーン設計", "戦略 (Owl)", "SNS運用", "セールス"])

client = None
if api_key:
    try:
        client = OpenAI(api_key=api_key)
    except:
        st.sidebar.error("APIキーが無効です")

# 共通チャットUI
def render_owl_chat(mode, system_prompt):
    if not client:
        st.warning("👈 左のサイドバーにOpenAI APIキーを入力してください。")
        return
    
    st.markdown(f"### {mode}")
    key = f"chat_{current_user}_{mode}"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": system_prompt}]
        st.session_state[key].append({"role": "assistant", "content": f"{user_name}さん、準備完了です。指示をください。"})
    
    for msg in st.session_state[key]:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
    
    if prompt := st.chat_input("ここに指示を入力..."):
        st.session_state[key].append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        
        with st.chat_message("assistant"):
            try:
                stream = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=st.session_state[key],
                    stream=True,
                )
                response = st.write_stream(stream)
                st.session_state[key].append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

# コンテンツ
if menu == "ダッシュボード":
    # ホーム画面の表記追加
    st.markdown(f"""
    <div class="main-header">
        <h1>🦉 Owl v3.0</h1>
        <p>Welcome back, <b>{user_name}</b>.</p>
        <p style="font-size: 0.8rem; color: #777 !important;">Athenalink Operation System</p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 今日のタスク (Top 3)")
        my_tasks = get_tasks(current_user).head(3)
        if not my_tasks.empty:
            for i, task in my_tasks.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="card">
                        <b>{task['title']}</b><br>
                        <span style="font-size:0.8em; color:#d9534f;">優先度: {task['priority']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"完了 (ID:{task['task_id']})", key=f"done_{task['task_id']}"):
                        complete_task(task['task_id'])
                        st.rerun()
        else:
            st.info("現在タスクはありません。")
            
    with c2:
        st.markdown("### チームチャット (最新)")
        chats = get_team_chat().head(3)
        for i, chat in chats.iterrows():
            st.caption(f"{chat['user_id']} ({chat['created_at']})")
            st.write(chat['message'])
            st.markdown("---")

elif menu == "チームチャット":
    st.markdown("### Team Room (Ren & Shu)")
    
    with st.form("chat_form", clear_on_submit=True):
        c1, c2 = st.columns([4, 1])
        msg = c1.text_input("メッセージ", placeholder="連絡事項を入力...")
        if c2.form_submit_button("送信") and msg:
            send_team_chat(current_user, msg)
            st.rerun()
    
    chats = get_team_chat()
    for i, chat in chats.iterrows():
        is_me = chat['user_id'] == current_user
        align = "text-align: right;" if is_me else ""
        bg = "#f0c0d0" if is_me else "#ffffff" 
        st.markdown(f"""
        <div style="{align} margin-bottom: 10px;">
            <small style="color:#666;">{chat['user_id']} {chat['created_at']}</small><br>
            <span style="background-color: {bg}; padding: 8px 12px; border-radius: 15px; display: inline-block; border: 1px solid #ddd;">
                {chat['message']}
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    if st.button("Owlにこのチャットを要約させる"):
        chat_text = "\n".join([f"{r['user_id']}: {r['message']}" for i, r in chats.iterrows()])
        render_owl_chat("Chat Summary", f"以下のチームチャットのログを要約し、TODOがあれば抽出してください。\n\n{chat_text}")

elif menu == "キャンペーン設計":
    st.markdown("### Campaign Planner")
    c1, c2, c3 = st.columns(3)
    goal = c1.text_input("目的", "note販売")
    period = c2.selectbox("期間", ["7日間", "14日間", "30日間"])
    media = c3.multiselect("媒体", ["X", "note", "LINE"], default=["X"])
    
    if st.button("計画を自動生成する"):
        prompt = f"目的：{goal}、期間：{period}、媒体：{', '.join(media)} でのマーケティングキャンペーン計画を立案してください。週ごとのテーマ、投稿内容の比率、具体的なアクションプランを表形式で提示してください。"
        render_owl_chat("Planner", prompt)
    else:
        render_owl_chat("Planner", "あなたはマーケティングプランナーです。")

elif menu == "戦略 (Owl)":
    render_owl_chat("M4 Strategy", "あなたはアテナリンクの最高戦略責任者です。")

elif menu == "SNS運用":
    render_owl_chat("M1 SNS", "あなたはプロのSNSマーケターです。")

elif menu == "セールス":
    render_owl_chat("M3 Sales", "あなたは解決型セールスライターです。")
