import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI
import base64

# --- 1. アプリ設定 & ChatGPT風ダークデザイン ---
st.set_page_config(page_title="Owl v3.5.1", page_icon="🦉", layout="wide")

# カラーパレット定義
COLOR_BG_MAIN = "#0B1020"       # メイン背景 (Deep Navy)
COLOR_BG_SIDE = "#050816"       # サイドバー (Darker)
COLOR_BG_CARD = "#111827"       # カード・入力欄 (Dark Grey)
COLOR_TEXT_MAIN = "#F9FAFB"     # メイン文字 (White/Light Grey)
COLOR_TEXT_SUB = "#9CA3AF"      # サブ文字 (Grey)
COLOR_ACCENT = "#10A37F"        # ChatGPT Green
COLOR_BORDER = "#1F2937"        # 枠線

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Noto Sans JP', sans-serif;
        color: {COLOR_TEXT_MAIN};
        background-color: {COLOR_BG_MAIN};
    }}

    .stApp {{
        background-color: {COLOR_BG_MAIN};
        background-image: none;
    }}

    /* サイドバー */
    [data-testid="stSidebar"] {{
        background-color: {COLOR_BG_SIDE};
        border-right: 1px solid {COLOR_BORDER};
    }}
    [data-testid="stSidebar"] * {{
        color: {COLOR_TEXT_MAIN} !important;
    }}
    [data-testid="stSidebar"] input {{
        background-color: {COLOR_BG_CARD} !important;
        color: {COLOR_TEXT_MAIN} !important;
        border: 1px solid {COLOR_BORDER} !important;
    }}

    /* 入力欄 (ChatGPT風) */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
        background-color: {COLOR_BG_CARD} !important;
        color: {COLOR_TEXT_MAIN} !important;
        -webkit-text-fill-color: {COLOR_TEXT_MAIN} !important;
        caret-color: {COLOR_TEXT_MAIN} !important;
        border: 1px solid {COLOR_BORDER} !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
    }}
    .stTextInput input:focus, .stTextArea textarea:focus {{
        border-color: {COLOR_ACCENT} !important;
        box-shadow: 0 0 0 1px {COLOR_ACCENT} !important;
    }}
    div[data-baseweb="popover"] div {{
        background-color: {COLOR_BG_CARD} !important;
        color: {COLOR_TEXT_MAIN} !important;
    }}
    div[data-baseweb="select"] div {{
        color: {COLOR_TEXT_MAIN} !important;
    }}

    /* ボタン (Primary Green) */
    div.stButton > button {{
        background-color: {COLOR_ACCENT} !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        padding: 0.6rem 1.2rem !important;
        transition: background-color 0.2s;
    }}
    div.stButton > button:hover {{
        background-color: #0D8C6D !important;
    }}

    /* チャットバブル */
    .chat-user {{
        background-color: {COLOR_BG_CARD};
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        color: {COLOR_TEXT_MAIN};
        border: 1px solid {COLOR_BORDER};
    }}
    .chat-owl {{
        background-color: transparent;
        padding: 20px;
        margin-bottom: 20px;
        color: {COLOR_TEXT_MAIN};
        border-bottom: 1px solid {COLOR_BORDER};
    }}
    
    /* 評価ボタン */
    .feedback-btn {{
        background: transparent;
        border: 1px solid {COLOR_BORDER};
        color: {COLOR_TEXT_SUB};
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 0.8rem;
        cursor: pointer;
        margin-right: 8px;
    }}

    /* ヘッダー・テキスト */
    h1, h2, h3 {{ color: {COLOR_TEXT_MAIN} !important; }}
    p, div, span {{ color: {COLOR_TEXT_MAIN}; }}
    .sub-text {{ color: {COLOR_TEXT_SUB} !important; font-size: 0.9rem; }}

    /* カード */
    .card {{
        background-color: {COLOR_BG_CARD};
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }}
    
    /* ログイン画面 */
    .login-container {{
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        background-color: {COLOR_BG_CARD};
        border-radius: 12px;
        border: 1px solid {COLOR_BORDER};
        text-align: center;
    }}
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

# --- データ関数 ---
def get_user_name(uid):
    conn = sqlite3.connect(DB_PATH)
    res = conn.execute("SELECT name FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    return res[0] if res else uid

def get_tasks(uid=None):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM tasks WHERE status != 'DONE' "
    if uid: query += f"AND assignee = '{uid}' "
    query += "ORDER BY priority DESC, created_at DESC"
    df = pd.read_sql(query, conn)
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

def analyze_image(client, image_file):
    image_file.seek(0)
    b64 = base64.b64encode(image_file.read()).decode('utf-8')
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": [{"type": "text", "text": "画像を分析してください。"}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]
    )
    return res.choices[0].message.content

def save_feedback(pid, module, content, rating):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO feedback (project_id, module, content, rating, created_at) VALUES (?, ?, ?, ?, ?)", (pid, module, content, rating, datetime.now()))
    conn.commit()
    conn.close()
    st.toast("Feedback Saved")

# --- ログイン ---
if 'user' not in st.session_state: st.session_state['user'] = None
if not st.session_state['user']:
    st.markdown(f"""
    <div class="login-container">
        <h1>🦉 Owl v3.5</h1>
        <p style="color:#9CA3AF;">Athenalink Director AI</p>
        <br>
    </div>
    """, unsafe_allow_html=True)
    _, c2, _ = st.columns([1,1,1])
    with c2:
        with st.form("login"):
            uid = st.selectbox("Select User", ["ren", "shu"])
            if st.form_submit_button("Login"):
                st.session_state['user'] = uid
                st.rerun()
    st.stop()

current_user = st.session_state['user']
user_name = get_user_name(current_user)

# --- レイアウト ---

st.sidebar.markdown(f"### 🦉 Owl v3.5")
st.sidebar.markdown(f"<p style='color:#9CA3AF; font-size:0.8rem;'>User: {user_name}</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

menu = st.sidebar.radio("MENU", ["Dashboard", "Team Chat", "M4 Strategy", "M1 SNS", "M2 Editor", "M3 Sales"])

st.sidebar.markdown("---")
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    api_key = st.sidebar.text_input("API Key", type="password")
client = OpenAI(api_key=api_key) if api_key else None

if st.sidebar.button("Logout"):
    st.session_state['user'] = None
    st.rerun()

# --- プロンプト定義 (Fix: 定義位置を修正) ---
STYLE = "【基本スタイル】\n1.言語:日本語\n2.禁止:自分語り/ポエム/説教\n3.構成:受容→分析→処方\n4.態度:プロのカウンセラー"

# アダプティブ設定
adaptive_prompt = ""
if menu in ["M1 SNS", "M2 Editor", "M3 Sales"]:
    st.sidebar.markdown("### ⚙️ Settings")
    TARGET_MEDIA = {
        "X (Twitter)": {"len": "140字以内", "tone": "共感・発見"},
        "X (Long)": {"len": "1000字", "tone": "ストーリー"},
        "note (Article)": {"len": "3000字", "tone": "解説"},
        "note (LP)": {"len": "5000字", "tone": "解決"},
        "DM": {"len": "300字", "tone": "私信"}
    }
    DEPTH_LEVELS = {"Light": "拡散", "Standard": "信頼", "Deep": "解決"}
    
    sel_media = st.sidebar.selectbox("Media", list(TARGET_MEDIA.keys()))
    sel_depth = st.sidebar.selectbox("Depth", list(DEPTH_LEVELS.keys()))
    
    m_info = TARGET_MEDIA[sel_media]
    adaptive_prompt = (
        f"\n【出力設定】媒体:{sel_media}(目安{m_info['len']}), トーン:{m_info['tone']}, "
        f"深さ:{sel_depth}\n"
    )
    
    if menu == "M1 SNS":
        st.sidebar.markdown("---")
        st.sidebar.write("👁️ Image Analysis")
        up = st.file_uploader("Upload", type=["jpg","png"])
        if up and client:
            if st.sidebar.button("Analyze"):
                with st.spinner("Analyzing..."):
                    res = analyze_image(client, up)
                    st.session_state['img_context'] = res
                    st.sidebar.success("Done")

# メインチャットUI
def render_chat_interface(mode, base_system_prompt):
    if not client: st.warning("API Key Required"); return
    
    st.markdown(f"## {mode}")
    st.markdown(f"<p class='sub-text'>AI Assistant for {mode}</p>", unsafe_allow_html=True)
    
    full_prompt = base_system_prompt + adaptive_prompt
    if 'img_context' in st.session_state and menu == "M1 SNS":
        full_prompt += f"\n[画像分析]: {st.session_state['img_context']}"
    full_prompt += "\n【思考プロセス】1.感情エミュレーション 2.具体化 3.構成 4.執筆 (出力は結果のみ)"

    key = f"chat_{current_user}_{mode}"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": full_prompt}]
        st.session_state[key].append({"role": "assistant", "content": "準備完了。指示をください。"})
    
    st.session_state[key][0]["content"] = full_prompt

    for i, msg in enumerate(st.session_state[key]):
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user"><div style="font-weight:bold; margin-bottom:5px; color:#9CA3AF;">You</div>{msg["content"]}</div>', unsafe_allow_html=True)
        elif msg["role"] == "assistant":
            st.markdown(f'<div class="chat-owl"><div style="font-weight:bold; margin-bottom:5px; color:#10A37F;">Owl</div>{msg["content"]}</div>', unsafe_allow_html=True)
            c1, c2, _ = st.columns([1, 1, 10])
            with c1:
                if st.button("👍", key=f"g_{key}_{i}"): save_feedback("GEN", mode, msg["content"], "good")
            with c2:
                if st.button("👎", key=f"b_{key}_{i}"): save_feedback("GEN", mode, msg["content"], "bad")

    st.markdown("<br>", unsafe_allow_html=True)
    with st.form(key=f"form_{mode}", clear_on_submit=True):
        user_input = st.text_area("Message Owl...", height=100)
        if st.form_submit_button("Send") and user_input:
            st.session_state[key].append({"role": "user", "content": user_input})
            try:
                with st.spinner("Thinking..."):
                    res = client.chat.completions.create(model="gpt-3.5-turbo", messages=st.session_state[key], max_tokens=3000)
                st.session_state[key].append({"role": "assistant", "content": res.choices[0].message.content})
                st.rerun()
            except Exception as e: st.error(str(e))

# --- コンテンツ表示 ---

if menu == "Dashboard":
    st.markdown(f"## Welcome back, {user_name}")
    st.markdown("<p class='sub-text'>Athenalink Operation System</p>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔥 My Tasks")
        tasks = get_tasks(current_user).head(5)
        if not tasks.empty:
            for i, t in tasks.iterrows():
                st.markdown(f'<div class="card"><b>{t["title"]}</b> <span style="float:right; color:#EF4444;">{t["priority"]}</span></div>', unsafe_allow_html=True)
                if st.button("Done", key=f"d_d_{t['task_id']}"): complete_task(t['task_id']); st.rerun()
        else: st.info("No tasks.")
    with c2:
        st.markdown("### 💬 Team Chat (Latest)")
        chats = get_team_chat().head(3)
        for i, c in chats.iterrows():
            st.markdown(f'<div class="card"><small style="color:#9CA3AF">{c["user_id"]} • {c["created_at"]}</small><br>{c["message"]}</div>', unsafe_allow_html=True)

elif menu == "Team Chat":
    st.markdown("## Team Chat")
    with st.form("team_chat"):
        msg = st.text_area("Message...")
        if st.form_submit_button("Send") and msg: send_team_chat(current_user, msg); st.rerun()
    chats = get_team_chat()
    for i, c in chats.iterrows():
        is_me = c['user_id'] == current_user
        align = "text-align: right;" if is_me else ""
        bg = COLOR_BG_CARD if is_me else "transparent"
        border = f"1px solid {COLOR_BORDER}" if is_me else "none"
        st.markdown(f'<div style="{align}"><div style="display:inline-block; background-color:{bg}; border:{border}; padding:10px 15px; border-radius:12px; text-align:left; margin-bottom:10px; color:{COLOR_TEXT_MAIN};"><div style="font-size:0.8rem; color:#9CA3AF; margin-bottom:4px;">{c["user_id"]}</div>{c["message"]}</div></div>', unsafe_allow_html=True)

# ここで分岐 (Fix: STYLE変数はこの前で定義済みなのでエラーにならない)
elif menu == "M4 Strategy":
    render_chat_interface("M4 Strategy", f"戦略参謀です。{STYLE}")
elif menu == "M1 SNS":
    render_chat_interface("M1 SNS", f"SNS担当です。読者の心を代弁するポストを作成してください。{STYLE}")
elif menu == "M2 Editor":
    render_chat_interface("M2 Editor", f"編集者です。読者が納得する記事構成を作成してください。{STYLE}")
elif menu == "M3 Sales":
    render_chat_interface("M3 Sales", f"解決型セールスライターです。PASONAで長文レターを書いてください。{STYLE}")
