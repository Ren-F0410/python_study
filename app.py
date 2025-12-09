import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI
import base64

# --- 1. アプリ設定 & デザイン定義 ---
st.set_page_config(page_title="Owl v3.3", page_icon="🦉", layout="wide")

# カラーパレット定義
COLOR_BG = "#FFFFFF"
COLOR_PRIMARY = "#FADDE1" # アクセントピンク
COLOR_INK = "#111827"     # 文字・濃いUI
COLOR_BORDER = "#E5E7EB"
COLOR_CARD_BG = "#F9FAFB" # 薄いグレー背景

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Noto Sans JP', sans-serif;
        color: {COLOR_INK};
        background-color: {COLOR_BG};
    }}

    /* 全体の背景リセット */
    .stApp {{
        background-color: {COLOR_BG};
        background-image: none;
    }}

    /* --- ヘッダー --- */
    .header-container {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 1rem;
        margin-bottom: 2rem;
        border-bottom: 1px solid {COLOR_BORDER};
    }}
    .app-title {{
        font-size: 1.5rem;
        font-weight: 700;
        color: {COLOR_INK};
        letter-spacing: 0.05em;
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .user-info {{
        font-size: 0.9rem;
        color: #6B7280;
    }}
    .user-info a {{
        color: {COLOR_INK};
        text-decoration: none;
        font-weight: 500;
        margin-left: 10px;
    }}

    /* --- サイドバー --- */
    [data-testid="stSidebar"] {{
        background-color: #FAFAFA;
        border-right: 1px solid {COLOR_BORDER};
    }}
    [data-testid="stSidebar"] * {{
        color: {COLOR_INK} !important;
    }}
    /* サイドバーのラジオボタン選択時 */
    div[role="radiogroup"] > label > div:first-child {{
        background-color: {COLOR_PRIMARY} !important;
        border-color: {COLOR_PRIMARY} !important;
    }}

    /* --- 入力欄 (統一スタイル) --- */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
        background-color: {COLOR_BG} !important;
        color: {COLOR_INK} !important;
        border: 1px solid {COLOR_BORDER} !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        box-shadow: none !important;
    }}
    /* フォーカス時 */
    .stTextInput input:focus, .stTextArea textarea:focus {{
        border-color: {COLOR_PRIMARY} !important;
        box-shadow: 0 0 0 1px {COLOR_PRIMARY} !important;
    }}

    /* --- ボタン (Inkカラー統一) --- */
    div.stButton > button {{
        background-color: {COLOR_INK} !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        padding: 0.5rem 1.2rem !important;
        height: 40px !important;
        box-shadow: none !important;
    }}
    div.stButton > button:hover {{
        background-color: #374151 !important; /* 少し明るいグレー */
    }}

    /* --- 評価ボタン (Primary Pink) --- */
    .feedback-btn {{
        background-color: {COLOR_PRIMARY};
        color: {COLOR_INK};
        border: none;
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.8rem;
        cursor: pointer;
        margin-right: 8px;
    }}
    .feedback-btn:hover {{
        background-color: #F9C8D0;
    }}

    /* --- チャットバブル --- */
    /* 自分 (右 / Primary Pink) */
    .chat-bubble-user {{
        background-color: {COLOR_PRIMARY};
        color: {COLOR_INK};
        padding: 12px 16px;
        border-radius: 12px 12px 0 12px;
        margin-bottom: 8px;
        max-width: 80%;
        margin-left: auto;
        font-size: 0.95rem;
    }}
    /* 相手/Owl (左 / Gray) */
    .chat-bubble-owl {{
        background-color: {COLOR_CARD_BG};
        color: {COLOR_INK};
        border: 1px solid {COLOR_BORDER};
        padding: 12px 16px;
        border-radius: 12px 12px 12px 0;
        margin-bottom: 8px;
        max-width: 80%;
        margin-right: auto;
        font-size: 0.95rem;
    }}
    
    /* Streamlit標準のチャットメッセージのスタイル上書き */
    [data-testid="stChatMessage"] {{
        background-color: transparent !important;
    }}
    [data-testid="stChatMessageAvatarBackground"] {{
        background-color: {COLOR_INK} !important;
        color: white !important;
    }}

    /* --- カード --- */
    .minimal-card {{
        background-color: {COLOR_CARD_BG};
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }}
    
    /* ユーティリティ */
    .text-sm {{ font-size: 0.85rem; color: #6B7280; }}
    .text-bold {{ font-weight: 700; }}
    
    /* ログインボックス */
    .login-box {{
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        background: {COLOR_CARD_BG};
        border-radius: 12px;
        text-align: center;
        border: 1px solid {COLOR_BORDER};
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
        messages=[{"role": "user", "content": [{"type": "text", "text": "画像分析をお願いします。"}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]
    )
    return res.choices[0].message.content

def save_feedback(pid, module, content, rating):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO feedback (project_id, module, content, rating, created_at) VALUES (?, ?, ?, ?, ?)", (pid, module, content, rating, datetime.now()))
    conn.commit()
    conn.close()
    st.toast("Feedback saved")

# --- ログイン ---
if 'user' not in st.session_state: st.session_state['user'] = None
if not st.session_state['user']:
    st.markdown(f"""
    <div class="login-box">
        <h1>🦉 Owl v3.3</h1>
        <p style="color:#666;">Athenalink Director AI</p>
        <br>
    </div>
    """, unsafe_allow_html=True)
    
    # ログインフォームを中央寄せするためにカラムで調整
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

# --- レイアウト構築 ---

# ヘッダー (全ページ共通)
st.markdown(f"""
<div class="header-container">
    <div class="app-title">🦉 Owl v3.3</div>
    <div class="user-info">
        User: <b>{user_name}</b> | <a href="#" onclick="window.location.reload();">Logout</a>
    </div>
</div>
""", unsafe_allow_html=True)

# サイドバー
st.sidebar.markdown("### MENU")
menu_options = ["ダッシュボード", "チームチャット", "M4 戦略", "M1 SNS", "M2 記事", "M3 セールス"]
menu = st.sidebar.radio("", menu_options)

st.sidebar.markdown("---")
# API Key設定
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
client = OpenAI(api_key=api_key) if api_key else None

if st.sidebar.button("Logout"):
    st.session_state['user'] = None
    st.rerun()

# --- コンテンツロジック ---

# 共通チャットコンポーネント
def render_chat_interface(mode, system_prompt, sidebar_content=None):
    if not client: st.warning("Please set API Key"); return
    
    # メインコンテンツエリア
    st.markdown(f"### {mode}")
    st.markdown(f'<p class="text-sm">Owl Assistant for {mode}</p>', unsafe_allow_html=True)
    
    # レイアウト分割 (チャットメイン + 右サイド情報)
    col_main, col_sub = st.columns([2, 1])
    
    key = f"chat_{current_user}_{mode}"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": system_prompt}]
        st.session_state[key].append({"role": "assistant", "content": "準備完了。指示をください。"})

    with col_main:
        # チャットログ
        for i, msg in enumerate(st.session_state[key]):
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-bubble-user">{msg["content"]}</div>', unsafe_allow_html=True)
            elif msg["role"] == "assistant":
                st.markdown(f'<div class="chat-bubble-owl">{msg["content"]}</div>', unsafe_allow_html=True)
                
                # 評価ボタン
                c1, c2 = st.columns([1, 8])
                with c1:
                    if st.button("👍", key=f"good_{key}_{i}"): save_feedback("GEN", mode, msg["content"], "good")
                with c2:
                    if st.button("👎", key=f"bad_{key}_{i}"): save_feedback("GEN", mode, msg["content"], "bad")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # 入力フォーム
        with st.form(key=f"form_{mode}", clear_on_submit=True):
            user_input = st.text_area("指示を入力...", height=120)
            c1, c2 = st.columns([5, 1])
            with c2:
                send = st.form_submit_button("送信")
        
        if send and user_input:
            st.session_state[key].append({"role": "user", "content": user_input})
            try:
                with st.spinner("Owl is thinking..."):
                    res = client.chat.completions.create(model="gpt-3.5-turbo", messages=st.session_state[key], max_tokens=2000)
                st.session_state[key].append({"role": "assistant", "content": res.choices[0].message.content})
                st.rerun()
            except Exception as e: st.error(str(e))

    with col_sub:
        # 右サイド情報パネル
        st.markdown("#### Information")
        if sidebar_content:
            sidebar_content()
        
        st.markdown("---")
        st.markdown("#### My Tasks")
        tasks = get_tasks(current_user).head(5)
        if not tasks.empty:
            for i, t in tasks.iterrows():
                st.markdown(f"""
                <div class="minimal-card" style="padding:1rem;">
                    <div class="text-sm">{t['priority']}</div>
                    <div class="text-bold">{t['title']}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("完了", key=f"done_sub_{t['task_id']}"): complete_task(t['task_id']); st.rerun()
        else:
            st.info("No tasks.")

# --- 各ページ ---

if menu == "ダッシュボード":
    st.info("左のメニューからモードを選択してください。")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Team Chat (Latest)")
        chats = get_team_chat().head(3)
        for i, c in chats.iterrows():
            st.markdown(f"""
            <div class="minimal-card">
                <div class="text-sm">{c['user_id']} • {c['created_at']}</div>
                <div>{c['message']}</div>
            </div>
            """, unsafe_allow_html=True)
            
    with c2:
        st.markdown("### Quick Task")
        with st.form("quick_task"):
            t = st.text_input("タスク名")
            p = st.selectbox("優先度", ["High", "Middle"])
            if st.form_submit_button("追加"):
                add_task("general", t, current_user, p)
                st.rerun()

elif menu == "チームチャット":
    st.markdown("### Team Chat")
    st.markdown('<p class="text-sm">RenとShuの共有チャット。会話内容はOwlの学習に利用されます。</p>', unsafe_allow_html=True)
    
    # チャットログ表示
    chats = get_team_chat()
    for i, c in chats.iterrows():
        is_me = c['user_id'] == current_user
        cls = "chat-bubble-user" if is_me else "chat-bubble-owl" # 相手はOwlスタイル（白背景）で代用
        align = "right" if is_me else "left"
        
        st.markdown(f"""
        <div style="text-align:{align};">
            <div style="display:inline-block; text-align:left;" class="{cls}">
                <div style="font-size:0.75rem; color:#666; margin-bottom:4px;">{c['user_id']}</div>
                {c['message']}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    with st.form("team_chat_form", clear_on_submit=True):
        c1, c2 = st.columns([5, 1])
        msg = c1.text_area("メッセージ", height=60)
        with c2:
            st.write("")
            if st.form_submit_button("送信") and msg:
                send_team_chat(current_user, msg)
                st.rerun()

elif menu == "M1 SNS":
    def m1_side():
        st.write("画像分析")
        up = st.file_uploader("Upload", type=["jpg","png"])
        if up and client:
            if st.button("分析"):
                res = analyze_image(client, up)
                st.session_state['img_context'] = res
                st.success("完了")
    
    prompt = "SNS担当です。読者の心を代弁するポストを作成してください。"
    if 'img_context' in st.session_state: prompt += f"\n[画像分析結果]: {st.session_state['img_context']}"
    render_chat_interface("M1 SNS", prompt, m1_side)

elif menu == "M4 戦略": render_chat_interface("M4 Strategy", "戦略参謀です。")
elif menu == "M2 記事": render_chat_interface("M2 Editor", "編集者です。")
elif menu == "M3 セールス": render_chat_interface("M3 Sales", "セールスライターです。")
