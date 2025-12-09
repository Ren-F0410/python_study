import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI
import base64

# --- 1. アプリ設定 & ミニマルデザイン定義 ---
st.set_page_config(page_title="Owl v3.2", page_icon="🦉", layout="wide")

# カラー定義
COLOR_BG = "#FFFFFF"
COLOR_ACCENT = "#F7D9E3"
COLOR_TEXT = "#222222"
COLOR_BORDER = "rgba(0,0,0,0.06)"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Noto Sans JP', sans-serif;
        color: {COLOR_TEXT};
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
        color: {COLOR_TEXT};
        letter-spacing: 0.05em;
    }}
    .user-info {{
        font-size: 0.9rem;
        color: #666;
    }}

    /* --- サイドバー（ナビゲーション） --- */
    [data-testid="stSidebar"] {{
        background-color: #FAFAFA; /* ほんの少しだけグレーにして区別 */
        border-right: 1px solid {COLOR_BORDER};
    }}
    [data-testid="stSidebar"] * {{
        color: {COLOR_TEXT} !important;
    }}

    /* --- 入力欄 (ミニマル統一) --- */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
        background-color: {COLOR_BG} !important;
        color: {COLOR_TEXT} !important;
        border: 1px solid {COLOR_BORDER} !important;
        border-radius: 8px !important; /* 少し丸める程度 */
        padding: 12px !important;
        box-shadow: none !important;
    }}
    .stTextInput input:focus, .stTextArea textarea:focus {{
        border-color: {COLOR_ACCENT} !important;
    }}

    /* --- ボタン (ACCENTカラー) --- */
    div.stButton > button {{
        background-color: {COLOR_ACCENT} !important;
        color: {COLOR_TEXT} !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        padding: 0.5rem 1.2rem !important;
        box-shadow: none !important;
    }}
    div.stButton > button:hover {{
        opacity: 0.8;
    }}

    /* --- カード (枠線のみ) --- */
    .minimal-card {{
        background-color: {COLOR_BG};
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }}
    .card-title {{
        font-weight: 700;
        margin-bottom: 0.5rem;
        font-size: 1rem;
        border-left: 4px solid {COLOR_ACCENT};
        padding-left: 10px;
    }}

    /* --- チャットバブルのカスタマイズ --- */
    /* ユーザーのメッセージ */
    [data-testid="stChatMessage"][data-testid="user"] {{
        background-color: {COLOR_ACCENT};
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        border: none;
    }}
    /* アシスタントのメッセージ */
    [data-testid="stChatMessage"][data-testid="assistant"] {{
        background-color: {COLOR_BG};
        border: 1px solid {COLOR_BORDER};
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }}
    
    /* アバターアイコンを消す（あるいは小さくする） */
    [data-testid="stChatMessageAvatarBackground"] {{
        display: none;
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
    st.toast("Thank you!")

# --- ログイン ---
if 'user' not in st.session_state: st.session_state['user'] = None
if not st.session_state['user']:
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown(f"<h1 style='text-align:center; color:{COLOR_TEXT};'>Owl v3.2</h1>", unsafe_allow_html=True)
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
    <div class="app-title">🦉 Owl v3.2</div>
    <div class="user-info">User: <b>{user_name}</b> | <a href="#" onclick="window.location.reload();">Logout</a></div>
</div>
""", unsafe_allow_html=True)

# サイドバー (ナビゲーションのみ)
st.sidebar.markdown("### MENU")
menu = st.sidebar.radio("", ["ダッシュボード", "チームチャット", "M4 戦略", "M1 SNS", "M2 記事", "M3 セールス"])
st.sidebar.markdown("---")
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    api_key = st.sidebar.text_input("API Key", type="password")
client = OpenAI(api_key=api_key) if api_key else None

if st.sidebar.button("ログアウト"):
    st.session_state['user'] = None
    st.rerun()

# --- 共通チャットコンポーネント ---
def render_chat_interface(mode, system_prompt, right_column_content=None):
    if not client: st.warning("API Key Required"); return
    
    # 2カラムレイアウト (左:チャット / 右:サイドパネル)
    col_chat, col_side = st.columns([1.8, 1])
    
    key = f"chat_{current_user}_{mode}"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": system_prompt}]
        st.session_state[key].append({"role": "assistant", "content": "準備完了。指示をください。"})

    with col_chat:
        st.markdown(f"#### {mode}")
        # チャット履歴表示
        for i, msg in enumerate(st.session_state[key]):
            if msg["role"] != "system":
                # カスタムCSSでバブル化
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    if msg["role"] == "assistant" and i > 0:
                        c1, c2, c3 = st.columns([1,1,8])
                        with c1: 
                            if st.button("👍", key=f"up_{key}_{i}"): save_feedback("GEN", mode, msg["content"], "good")
                        with c2: 
                            if st.button("👎", key=f"down_{key}_{i}"): save_feedback("GEN", mode, msg["content"], "bad")

        st.markdown("---")
        # 入力フォーム (下部)
        with st.form(key=f"form_{mode}", clear_on_submit=True):
            user_input = st.text_area("指示を入力...", height=100)
            c1, c2 = st.columns([4, 1])
            with c2:
                send = st.form_submit_button("送信")
        
        if send and user_input:
            st.session_state[key].append({"role": "user", "content": user_input})
            try:
                with st.spinner("Writing..."):
                    res = client.chat.completions.create(model="gpt-3.5-turbo", messages=st.session_state[key], max_tokens=2000)
                st.session_state[key].append({"role": "assistant", "content": res.choices[0].message.content})
                st.rerun()
            except Exception as e: st.error(str(e))

    with col_side:
        # 右サイドパネル（タスクや設定など）
        st.markdown('<div class="card-title">Information</div>', unsafe_allow_html=True)
        if right_column_content:
            right_column_content()
        
        # 共通のタスク表示
        st.markdown('<div class="card-title" style="margin-top:20px;">My Tasks</div>', unsafe_allow_html=True)
        tasks = get_tasks(current_user).head(5)
        if not tasks.empty:
            for i, t in tasks.iterrows():
                st.markdown(f"""
                <div class="minimal-card" style="padding:0.8rem;">
                    <small style="color:#888;">{t['priority']}</small><br>
                    <b>{t['title']}</b>
                </div>
                """, unsafe_allow_html=True)
                if st.button("完了", key=f"done_side_{t['task_id']}"): complete_task(t['task_id']); st.rerun()
        else:
            st.info("No tasks.")

# --- 各ページの内容 ---

if menu == "ダッシュボード":
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("### Dashboard")
        st.info("左のメニューからモードを選択してください。")
        
        # チームチャットプレビュー
        st.markdown('<div class="card-title">Team Chat (Latest)</div>', unsafe_allow_html=True)
        chats = get_team_chat().head(3)
        for i, c in chats.iterrows():
            st.markdown(f"""
            <div class="minimal-card">
                <small>{c['user_id']} • {c['created_at']}</small><br>
                {c['message']}
            </div>
            """, unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card-title">Quick Add Task</div>', unsafe_allow_html=True)
        with st.form("quick_task"):
            t = st.text_input("タスク名")
            p = st.selectbox("優先度", ["High", "Middle"])
            if st.form_submit_button("追加"):
                add_task("general", t, current_user, p)
                st.rerun()
        
        st.markdown('<div class="card-title" style="margin-top:20px;">My Tasks</div>', unsafe_allow_html=True)
        tasks = get_tasks(current_user)
        for i, t in tasks.iterrows():
            st.markdown(f'<div class="minimal-card">{t["title"]}</div>', unsafe_allow_html=True)

elif menu == "チームチャット":
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("### Team Chat")
        with st.form("team_chat_form", clear_on_submit=True):
            msg = st.text_area("メッセージ", height=80)
            if st.form_submit_button("送信"):
                send_team_chat(current_user, msg)
                st.rerun()
        
        chats = get_team_chat()
        for i, c in chats.iterrows():
            is_me = c['user_id'] == current_user
            # チャットバブル風表示（HTML）
            bg = "#F7D9E3" if is_me else "#FFFFFF"
            border = "none" if is_me else "1px solid rgba(0,0,0,0.06)"
            align = "right" if is_me else "left"
            st.markdown(f"""
            <div style="text-align:{align}; margin-bottom:10px;">
                <div style="display:inline-block; background:{bg}; border:{border}; padding:10px 15px; border-radius:12px; text-align:left; max-width:80%;">
                    <div style="font-size:0.75rem; color:#666; margin-bottom:4px;">{c['user_id']}</div>
                    {c['message']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    with c2:
        st.markdown('<div class="card-title">Members</div>', unsafe_allow_html=True)
        st.write("• Ren (Owner)")
        st.write("• Shu (Member)")

elif menu == "M1 SNS":
    def m1_sidebar():
        st.write("SNS用の画像分析")
        up = st.file_uploader("画像アップロード", type=["jpg","png"])
        if up and client:
            if st.button("分析実行"):
                res = analyze_image(client, up)
                st.session_state['img_context'] = res
                st.success("完了")
    
    prompt = "SNS担当です。読者の心を代弁するポストを作成してください。"
    if 'img_context' in st.session_state: prompt += f"\n[画像分析]: {st.session_state['img_context']}"
    render_chat_interface("M1 SNS", prompt, m1_sidebar)

elif menu == "M4 戦略": render_chat_interface("M4 Strategy", "戦略参謀です。")
elif menu == "M2 記事": render_chat_interface("M2 Editor", "編集者です。")
elif menu == "M3 セールス": render_chat_interface("M3 Sales", "セールスライターです。")
elif menu == "キャンペーン設計":
    st.markdown("### Campaign Planner")
    with st.form("camp"):
        target = st.text_input("目的")
        span = st.selectbox("期間", ["7days", "14days"])
        if st.form_submit_button("作成"):
            render_chat_interface("Planner", f"目的:{target}, 期間:{span} の計画を立てて。")
