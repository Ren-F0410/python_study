import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI
import base64

# --- 1. アプリ設定 & デザイン ---
st.set_page_config(page_title="Owl v3.4.1", page_icon="🦉", layout="wide")

# カラー定義
COLOR_BG = "#FFFFFF"
COLOR_PRIMARY = "#FADDE1" # アクセントピンク
COLOR_INK = "#111827"     # 文字・濃いUI
COLOR_BORDER = "#E5E7EB"
COLOR_CARD_BG = "#F9FAFB" 

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Noto Sans JP', sans-serif;
        color: {COLOR_INK};
        background-color: {COLOR_BG};
    }}

    .stApp {{ background-color: {COLOR_BG}; background-image: none; }}

    /* ヘッダー */
    .header-container {{
        display: flex; justify-content: space-between; align-items: center;
        padding-bottom: 1rem; margin-bottom: 2rem; border-bottom: 1px solid {COLOR_BORDER};
    }}
    .app-title {{ font-size: 1.5rem; font-weight: 700; color: {COLOR_INK}; display: flex; align-items: center; gap: 10px; }}
    .user-info {{ font-size: 0.9rem; color: #6B7280; }}

    /* サイドバー */
    [data-testid="stSidebar"] {{ background-color: #FAFAFA; border-right: 1px solid {COLOR_BORDER}; }}
    [data-testid="stSidebar"] * {{ color: {COLOR_INK} !important; }}

    /* 入力欄 (白背景・グレー枠) */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
        background-color: {COLOR_BG} !important;
        color: {COLOR_INK} !important;
        border: 1px solid {COLOR_BORDER} !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        box-shadow: none !important;
    }}
    .stTextInput input:focus, .stTextArea textarea:focus {{
        border-color: {COLOR_PRIMARY} !important;
        box-shadow: 0 0 0 1px {COLOR_PRIMARY} !important;
    }}

    /* ボタン */
    div.stButton > button {{
        background-color: {COLOR_INK} !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        padding: 0.5rem 1.2rem !important;
    }}
    div.stButton > button:hover {{ background-color: #374151 !important; }}

    /* チャットバブル */
    .chat-bubble-user {{
        background-color: {COLOR_PRIMARY}; color: {COLOR_INK};
        padding: 12px 16px; border-radius: 12px 12px 0 12px;
        margin-bottom: 8px; max-width: 85%; margin-left: auto; font-size: 0.95rem;
    }}
    .chat-bubble-owl {{
        background-color: {COLOR_CARD_BG}; color: {COLOR_INK};
        border: 1px solid {COLOR_BORDER};
        padding: 12px 16px; border-radius: 12px 12px 12px 0;
        margin-bottom: 8px; max-width: 85%; margin-right: auto; font-size: 0.95rem;
    }}
    
    /* ログインボックス */
    .login-box {{
        max-width: 400px; margin: 100px auto; padding: 40px;
        background: {COLOR_CARD_BG}; border-radius: 12px;
        text-align: center; border: 1px solid {COLOR_BORDER};
    }}
    
    /* カード */
    .minimal-card {{
        background-color: {COLOR_CARD_BG}; border: 1px solid {COLOR_BORDER};
        border-radius: 8px; padding: 1rem; margin-bottom: 0.8rem;
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

# --- 2. データ関数 ---
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
        messages=[{"role": "user", "content": [{"type": "text", "text": "画像を詳細に分析してください。"}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]
    )
    return res.choices[0].message.content

def save_feedback(pid, module, content, rating):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO feedback (project_id, module, content, rating, created_at) VALUES (?, ?, ?, ?, ?)", (pid, module, content, rating, datetime.now()))
    conn.commit()
    conn.close()
    st.toast("Feedback Saved")

# --- 3. ログイン処理 ---
if 'user' not in st.session_state: st.session_state['user'] = None
if not st.session_state['user']:
    st.markdown(f"<div class='login-box'><h1>🦉 Owl v3.4</h1><p>Athenalink Director AI</p></div>", unsafe_allow_html=True)
    _, c2, _ = st.columns([1,1,1])
    with c2:
        with st.form("login"):
            uid = st.selectbox("USER", ["ren", "shu"])
            if st.form_submit_button("LOGIN"):
                st.session_state['user'] = uid
                st.rerun()
    st.stop()

current_user = st.session_state['user']
user_name = get_user_name(current_user)

# --- 4. レイアウト & ロジック ---

# ヘッダー
st.markdown(f"""
<div class="header-container">
    <div class="app-title">🦉 Owl v3.4 <span style="font-size:0.8rem; font-weight:400; margin-left:10px; color:#999;">Stable</span></div>
    <div class="user-info">User: <b>{user_name}</b> | <a href="#" onclick="window.location.reload();" style="color:#333;">Logout</a></div>
</div>
""", unsafe_allow_html=True)

# サイドバー
st.sidebar.markdown("### MENU")
menu = st.sidebar.radio("", ["ダッシュボード", "チームチャット", "M4 戦略", "M1 SNS", "M2 記事", "M3 セールス"])
st.sidebar.markdown("---")

# API Key
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    api_key = st.sidebar.text_input("API Key", type="password")
client = OpenAI(api_key=api_key) if api_key else None

# アダプティブ設定
adaptive_prompt = ""
if menu in ["M1 SNS", "M2 記事", "M3 セールス"]:
    st.sidebar.markdown("### 🎛 生成設定")
    TARGET_MEDIA = {
        "X (Twitter)": {"len": "140字以内", "tone": "共感・発見"},
        "X (長文)": {"len": "1000字", "tone": "ストーリー"},
        "note (記事)": {"len": "3000字", "tone": "解説"},
        "note (LP)": {"len": "5000字", "tone": "解決"},
        "DM": {"len": "300字", "tone": "私信"}
    }
    DEPTH_LEVELS = {"Light": "拡散", "Standard": "信頼", "Deep": "解決"}
    
    sel_media = st.sidebar.selectbox("媒体", list(TARGET_MEDIA.keys()))
    sel_depth = st.sidebar.selectbox("深さ", list(DEPTH_LEVELS.keys()))
    
    m_info = TARGET_MEDIA[sel_media]
    adaptive_prompt = (
        f"\n【出力設定】媒体:{sel_media}(目安{m_info['len']}), トーン:{m_info['tone']}, "
        f"深さ:{sel_depth}({DEPTH_LEVELS[sel_depth]})\n"
    )
    
    if menu == "M1 SNS":
        st.sidebar.markdown("---")
        st.sidebar.write("👁️ 画像分析")
        up = st.file_uploader("Upload", type=["jpg","png"])
        if up and client:
            if st.sidebar.button("分析"):
                with st.spinner("Analyzing..."):
                    res = analyze_image(client, up)
                    st.session_state['img_context'] = res
                    st.sidebar.success("完了")

# 共通チャット
def render_chat_interface(mode, base_system_prompt):
    if not client: st.warning("API Key Required"); return
    
    full_prompt = base_system_prompt + adaptive_prompt
    if 'img_context' in st.session_state and menu == "M1 SNS":
        full_prompt += f"\n[画像分析]: {st.session_state['img_context']}"
    
    # 思考プロセス (v2.5)
    full_prompt += "\n【思考プロセス】1.感情エミュレーション 2.具体化 3.構成 4.執筆 (出力は結果のみ)"

    col_main, col_sub = st.columns([2, 1])
    key = f"chat_{current_user}_{mode}"
    
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": full_prompt}]
        st.session_state[key].append({"role": "assistant", "content": "準備完了。"})
    
    st.session_state[key][0]["content"] = full_prompt

    with col_main:
        st.markdown(f"#### {mode}")
        for i, msg in enumerate(st.session_state[key]):
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-bubble-user">{msg["content"]}</div>', unsafe_allow_html=True)
            elif msg["role"] == "assistant":
                st.markdown(f'<div class="chat-bubble-owl">{msg["content"]}</div>', unsafe_allow_html=True)
                if i > 0:
                    c1, c2 = st.columns([1, 8])
                    with c1:
                        if st.button("👍", key=f"g_{key}_{i}"): save_feedback("GEN", mode, msg["content"], "good")
                    with c2:
                        if st.button("👎", key=f"b_{key}_{i}"): save_feedback("GEN", mode, msg["content"], "bad")
        
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form(key=f"form_{mode}", clear_on_submit=True):
            user_input = st.text_area("指示を入力...", height=120)
            if st.form_submit_button("送信"):
                st.session_state[key].append({"role": "user", "content": user_input})
                try:
                    with st.spinner("Thinking..."):
                        res = client.chat.completions.create(model="gpt-3.5-turbo", messages=st.session_state[key], max_tokens=3000)
                    st.session_state[key].append({"role": "assistant", "content": res.choices[0].message.content})
                    st.rerun()
                except Exception as e: st.error(str(e))

    with col_sub:
        st.markdown("#### Info")
        st.info(f"設定: {sel_media} / {sel_depth}" if adaptive_prompt else "標準モード")
        st.markdown("#### Tasks")
        tasks = get_tasks(current_user).head(5)
        for i, t in tasks.iterrows():
            st.markdown(f'<div class="minimal-card">{t["title"]}</div>', unsafe_allow_html=True)
            if st.button("完了", key=f"d_s_{t['task_id']}"): complete_task(t['task_id']); st.rerun()

# --- 各ページ ---

if menu == "ダッシュボード":
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Team Chat (Latest)")
        chats = get_team_chat().head(3)
        for i, c in chats.iterrows():
            st.markdown(f'<div class="minimal-card"><small>{c["user_id"]}</small><br>{c["message"]}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown("### Quick Task")
        with st.form("quick_task"):
            t = st.text_input("タスク名")
            p = st.selectbox("優先度", ["High", "Middle"])
            if st.form_submit_button("追加"): add_task("gen", t, current_user, p); st.rerun()

elif menu == "チームチャット":
    st.markdown("### Team Chat")
    with st.form("team_chat"):
        msg = st.text_area("メッセージ")
        if st.form_submit_button("送信") and msg: send_team_chat(current_user, msg); st.rerun()
    chats = get_team_chat()
    for i, c in chats.iterrows():
        is_me = c['user_id'] == current_user
        cls = "chat-bubble-user" if is_me else "chat-bubble-owl"
        align = "right" if is_me else "left"
        st.markdown(f'<div style="text-align:{align}"><div class="{cls}">{c["message"]}</div><small>{c["user_id"]}</small></div>', unsafe_allow_html=True)

# プロンプト (v2.5ベース)
STYLE = "【スタイル】\n1.言語:日本語\n2.禁止:自分語り/ポエム/説教\n3.構成:受容→分析→処方\n4.態度:プロのカウンセラー"

if menu == "M4 戦略":
    render_chat_interface("M4 Strategy", f"戦略参謀です。{STYLE}")
elif menu == "M1 SNS":
    render_chat_interface("M1 SNS", f"SNS担当です。読者の心を代弁するポストを作成してください。{STYLE}")
elif menu == "M2 記事":
    render_chat_interface("M2 Editor", f"編集者です。読者が納得する記事構成を作成してください。{STYLE}")
elif menu == "M3 セールス":
    render_chat_interface("M3 Sales", f"解決型セールスライターです。PASONAで長文レターを書いてください。{STYLE}")
