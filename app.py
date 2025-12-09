import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI
import base64
import time

# --- 1. アプリ設定 & PWA対応 & デザイン ---
st.set_page_config(page_title="Owl v3.0", page_icon="🦉", layout="wide")

# カスタムCSS (アテナリンク・ブランド)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
    
    :root {
        --primary-color: #f9dfe7; /* 淡いピンク */
        --text-color: #333333;
        --bg-color: #ffffff;
        --card-bg: #f8f9fa;
    }

    html, body, [class*="css"] {
        font-family: 'Noto Sans JP', sans-serif;
        color: var(--text-color);
    }

    /* ヘッダー */
    .main-header {
        background: linear-gradient(135deg, #f9dfe7 0%, #f3e7e9 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        color: #5d5d5d;
        border-left: 6px solid #e0a3b5;
    }
    .main-header h1 {
        color: #333333 !important;
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
    }
    .main-header p {
        color: #666666;
        margin-top: 0.5rem;
        font-size: 0.9rem;
    }

    /* ボタン */
    div.stButton > button {
        background-color: #333333;
        color: white;
        border: none;
        border-radius: 20px;
        padding: 0.5rem 1.5rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #e0a3b5;
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }

    /* 入力欄 */
    .stTextArea textarea, .stTextInput input {
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        background-color: #ffffff;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #e0a3b5;
        box-shadow: 0 0 0 2px rgba(224, 163, 181, 0.2);
    }

    /* カード風コンテナ */
    .card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
        border: 1px solid #f0f0f0;
    }

    /* サイドバー */
    [data-testid="stSidebar"] {
        background-color: #fbfbfb;
        border-right: 1px solid #f0f0f0;
    }
</style>
""", unsafe_allow_html=True)

DB_PATH = "owl_v3.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # ユーザーテーブル
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, name TEXT, role TEXT)")
    # プロジェクト
    c.execute("CREATE TABLE IF NOT EXISTS projects (project_id TEXT PRIMARY KEY, name TEXT, goal TEXT, created_at DATETIME)")
    # タスク (担当者追加)
    c.execute("CREATE TABLE IF NOT EXISTS tasks (task_id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, title TEXT, assignee TEXT, status TEXT DEFAULT 'TODO', priority TEXT, created_at DATETIME)")
    # チームチャット
    c.execute("CREATE TABLE IF NOT EXISTS team_chat (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, message TEXT, created_at DATETIME)")
    # 初期ユーザー登録（なければ）
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
    st.markdown("<div style='text-align: center; margin-top: 50px;'><h1>🦉 Owl v3.0</h1><p>Director AI for Athenalink</p></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.form("login_form"):
            uid = st.selectbox("ログインユーザーを選択", ["ren", "shu"])
            if st.form_submit_button("ログイン"):
                st.session_state['user'] = uid
                st.rerun()
    st.stop()

current_user = st.session_state['user']
user_name = get_user_name(current_user)

# --- 4. メインUI ---

# サイドバー
st.sidebar.markdown(f"### 👤 **{user_name}** でログイン中")
if st.sidebar.button("ログアウト"):
    st.session_state['user'] = None
    st.rerun()

st.sidebar.markdown("---")
menu = st.sidebar.radio("MENU", ["🏠 ダッシュボード", "💬 チームチャット", "📝 キャンペーン設計", "🧠 戦略 (Owl)", "📱 SNS運用", "💰 セールス"])

# APIキー設定
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
client = OpenAI(api_key=api_key) if api_key else None

# 共通チャットUI
def render_owl_chat(mode, system_prompt):
    if not client: st.warning("API Keyが必要です"); return
    
    st.markdown(f"### 🦉 {mode}")
    key = f"chat_{current_user}_{mode}"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": system_prompt}]
        st.session_state[key].append({"role": "assistant", "content": f"{user_name}さん、こんにちは。何かお手伝いしますか？"})
    
    for msg in st.session_state[key]:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
    
    if prompt := st.chat_input("Owlに指示..."):
        st.session_state[key].append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        
        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=st.session_state[key],
                stream=True,
            )
            response = st.write_stream(stream)
        st.session_state[key].append({"role": "assistant", "content": response})

# コンテンツ
if menu == "🏠 ダッシュボード":
    st.markdown(f"""
    <div class="main-header">
        <h1>Welcome back, {user_name}.</h1>
        <p>今日もアテナリンクの事業を進めましょう。</p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔥 今日のタスク (Top 3)")
        my_tasks = get_tasks(current_user).head(3)
        if not my_tasks.empty:
            for i, task in my_tasks.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="card">
                        <b>{task['title']}</b><br>
                        <small style="color:red;">{task['priority']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"完了 (ID:{task['task_id']})", key=f"done_{task['task_id']}"):
                        complete_task(task['task_id'])
                        st.rerun()
        else:
            st.info("現在タスクはありません。")
            
    with c2:
        st.markdown("### 💬 チームチャット (最新)")
        chats = get_team_chat().head(3)
        for i, chat in chats.iterrows():
            st.caption(f"{chat['user_id']} ({chat['created_at']})")
            st.write(chat['message'])
            st.markdown("---")

elif menu == "💬 チームチャット":
    st.markdown("### 🏢 Team Room (Ren & Shu)")
    
    # 投稿フォーム
    with st.form("chat_form", clear_on_submit=True):
        msg = st.text_input("メッセージ", placeholder="連絡事項や相談など...")
        if st.form_submit_button("送信") and msg:
            send_team_chat(current_user, msg)
            st.rerun()
    
    # 履歴表示
    chats = get_team_chat()
    for i, chat in chats.iterrows():
        is_me = chat['user_id'] == current_user
        align = "text-align: right;" if is_me else ""
        bg = "#f9dfe7" if is_me else "#f0f0f0"
        st.markdown(f"""
        <div style="{align} margin-bottom: 10px;">
            <small>{chat['user_id']} {chat['created_at']}</small><br>
            <span style="background-color: {bg}; padding: 8px 12px; border-radius: 10px; display: inline-block;">
                {chat['message']}
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    if st.button("🦉 Owlにこのチャットを要約させる"):
        # 簡易要約機能
        chat_text = "\n".join([f"{r['user_id']}: {r['message']}" for i, r in chats.iterrows()])
        render_owl_chat("Chat Summary", f"以下のチームチャットのログを要約し、TODOがあれば抽出してください。\n\n{chat_text}")

elif menu == "📝 キャンペーン設計":
    st.markdown("### 📅 Campaign Planner")
    c1, c2, c3 = st.columns(3)
    goal = c1.text_input("目的", "note販売")
    period = c2.selectbox("期間", ["7日間", "14日間", "30日間"])
    media = c3.multiselect("媒体", ["X", "note", "LINE"], default=["X"])
    
    if st.button("計画を自動生成する"):
        prompt = f"目的：{goal}、期間：{period}、媒体：{', '.join(media)} でのマーケティングキャンペーン計画を立案してください。週ごとのテーマ、投稿内容の比率、具体的なアクションプランを表形式で提示してください。"
        render_owl_chat("Planner", prompt)
    else:
        render_owl_chat("Planner", "あなたはマーケティングプランナーです。")

elif menu == "🧠 戦略 (Owl)":
    render_owl_chat("M4 Strategy", "あなたはアテナリンクの最高戦略責任者です。")

elif menu == "📱 SNS運用":
    render_owl_chat("M1 SNS", "あなたはプロのSNSマーケターです。")

elif menu == "💰 セールス":
    render_owl_chat("M3 Sales", "あなたは解決型セールスライターです。")
