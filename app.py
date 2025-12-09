import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI
import base64
import time

# --- 1. アプリ設定 & デザイン刷新 ---
# Owlのアイコンのみ残します
st.set_page_config(page_title="Owl v3.0", page_icon="🦉", layout="wide")

# カスタムCSS (桜テーマ・ミニマル・丸みUI)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
    
    :root {
        /* カラーパレット定義 */
        --bg-pink-pale: #fff3f5; /* 背景：非常に淡いピンク */
        --bg-pink-muted: #f3e0e6; /* ツールバー：少し濃い落ち着いたピンク */
        --text-black: #000000; /* 文字色：黒 */
        --border-color: #e0c0d0; /* 境界線：淡いピンクグレー */
        --input-bg: #ffffff; /* 入力欄背景：白 */
    }

    html, body, [class*="css"] {
        font-family: 'Noto Sans JP', sans-serif;
        color: var(--text-black) !important; /* 基本文字色を黒で統一 */
    }

    /* --- 全体の背景設定 (桜の日本画風) --- */
    .stApp {
        background-color: var(--bg-pink-pale);
        /* 【ここに背景画像を設定します】
           以下の url('...') の中に、使用したい「日本画風の桜の画像URL」を入れてください。
           画像がない場合は、現在の淡いグラデーションが適用されます。
        */
        background-image: linear-gradient(to bottom, rgba(255,243,245,0.9), rgba(255,255,255,0.5));
        background-size: cover;
        background-attachment: fixed;
    }

    /* --- サイドバー (ツールバー) --- */
    [data-testid="stSidebar"] {
        background-color: var(--bg-pink-muted);
        border-right: 1px solid var(--border-color);
    }
    [data-testid="stSidebar"] * {
        color: var(--text-black) !important;
    }

    /* --- ヘッダー --- */
    .main-header {
        background: rgba(255, 255, 255, 0.8); /* 半透明の白で背景を透かす */
        padding: 1.5rem;
        border-radius: 20px; /* 丸み */
        margin-bottom: 2rem;
        border: 1px solid var(--border-color);
    }
    .main-header h1 {
        color: var(--text-black) !important;
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
    }
    .main-header p {
        color: #333333 !important;
        margin-top: 0.5rem;
        font-size: 0.9rem;
    }

    /* --- 入力フィールド (ChatGPT風の丸み) --- */
    /* テキスト入力、テキストエリア、セレクトボックス */
    .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] > div {
        border-radius: 25px !important; /* 強い丸み */
        border: 1px solid var(--border-color) !important;
        background-color: var(--input-bg) !important;
        color: var(--text-black) !important;
        padding: 10px 15px !important;
        box-shadow: none !important;
    }
    /* フォーカス時の強調 */
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #d0a0b0 !important;
        box-shadow: 0 0 0 2px rgba(208, 160, 176, 0.2) !important;
    }
    
    /* チャット入力欄専用のスタイル */
    [data-testid="stChatInput"] textarea {
         border-radius: 25px !important;
    }

    /* --- ボタン --- */
    div.stButton > button {
        background-color: var(--bg-pink-muted);
        color: var(--text-black);
        border: 1px solid var(--border-color);
        border-radius: 20px; /* 丸み */
        padding: 0.5rem 1.5rem;
        font-weight: normal;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #e0c0d0;
        transform: translateY(-1px);
    }

    /* --- カード風コンテナ --- */
    .card {
        background-color: rgba(255, 255, 255, 0.9);
        padding: 1.5rem;
        border-radius: 20px; /* 丸み */
        margin-bottom: 1rem;
        border: 1px solid var(--border-color);
    }
    
    /* --- その他調整 --- */
    /* ラジオボタンの選択肢など */
    .stRadio label {
        color: var(--text-black) !important;
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

# --- 3. ログイン処理 (絵文字削除) ---
if 'user' not in st.session_state:
    st.session_state['user'] = None

if not st.session_state['user']:
    # Owlのアイコンのみ残す
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

# --- 4. メインUI (絵文字削除・デザイン適用) ---

# サイドバー
st.sidebar.markdown(f"### ログイン中: **{user_name}**")
if st.sidebar.button("ログアウト"):
    st.session_state['user'] = None
    st.rerun()

st.sidebar.markdown("---")
# メニューから絵文字を削除
menu = st.sidebar.radio("MENU", ["ダッシュボード", "チームチャット", "キャンペーン設計", "戦略 (Owl)", "SNS運用", "セールス"])

# APIキー設定
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
client = OpenAI(api_key=api_key) if api_key else None

# 共通チャットUI (ヘッダーの絵文字削除)
def render_owl_chat(mode, system_prompt):
    if not client: st.warning("API Keyが必要です"); return
    
    st.markdown(f"### {mode}")
    key = f"chat_{current_user}_{mode}"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": system_prompt}]
        st.session_state[key].append({"role": "assistant", "content": f"{user_name}さん、こんにちは。何かお手伝いしますか？"})
    
    for msg in st.session_state[key]:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
    
    # チャット入力欄のプレースホルダーも変更
    if prompt := st.chat_input("メッセージを送信..."):
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
if menu == "ダッシュボード":
    st.markdown(f"""
    <div class="main-header">
        <h1>Welcome back, {user_name}.</h1>
        <p>今日もアテナリンクの事業を進めましょう。</p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        # 絵文字削除
        st.markdown("### 今日のタスク (Top 3)")
        my_tasks = get_tasks(current_user).head(3)
        if not my_tasks.empty:
            for i, task in my_tasks.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="card">
                        <b>{task['title']}</b><br>
                        <span style="color:var(--text-black); font-size:0.8em;">優先度: {task['priority']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"完了 (ID:{task['task_id']})", key=f"done_{task['task_id']}"):
                        complete_task(task['task_id'])
                        st.rerun()
        else:
            st.info("現在タスクはありません。")
            
    with c2:
        # 絵文字削除
        st.markdown("### チームチャット (最新)")
        chats = get_team_chat().head(3)
        for i, chat in chats.iterrows():
            st.caption(f"{chat['user_id']} ({chat['created_at']})")
            st.write(chat['message'])
            st.markdown("---")

elif menu == "チームチャット":
    # 絵文字削除
    st.markdown("### Team Room (Ren & Shu)")
    
    with st.form("chat_form", clear_on_submit=True):
        msg = st.text_input("メッセージ", placeholder="連絡事項や相談など...")
        if st.form_submit_button("送信") and msg:
            send_team_chat(current_user, msg)
            st.rerun()
    
    chats = get_team_chat()
    for i, chat in chats.iterrows():
        is_me = chat['user_id'] == current_user
        align = "text-align: right;" if is_me else ""
        # チャット吹き出しの色も調整
        bg = "#f0c0d0" if is_me else "#ffffff" 
        border = "none" if is_me else "1px solid #e0c0d0"
        st.markdown(f"""
        <div style="{align} margin-bottom: 10px;">
            <small>{chat['user_id']} {chat['created_at']}</small><br>
            <span style="background-color: {bg}; border: {border}; padding: 8px 12px; border-radius: 15px; display: inline-block; color: var(--text-black);">
                {chat['message']}
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    # ボタンの絵文字も削除
    if st.button("Owlにこのチャットを要約させる"):
        chat_text = "\n".join([f"{r['user_id']}: {r['message']}" for i, r in chats.iterrows()])
        render_owl_chat("Chat Summary", f"以下のチームチャットのログを要約し、TODOがあれば抽出してください。\n\n{chat_text}")

elif menu == "キャンペーン設計":
    # 絵文字削除
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
