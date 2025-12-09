import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI
import base64
import requests
from bs4 import BeautifulSoup
import io

# --- 1. アプリ設定 & デザイン ---
st.set_page_config(page_title="Owl v3.6.2", page_icon="🦉", layout="wide")

# カラーパレット (ChatGPT Dark Theme)
COLOR_BG_MAIN = "#0B1020"
COLOR_BG_SIDE = "#050816"
COLOR_BG_CARD = "#111827"
COLOR_TEXT_MAIN = "#F9FAFB"
COLOR_TEXT_SUB = "#9CA3AF"
COLOR_ACCENT = "#10A37F"
COLOR_BORDER = "#1F2937"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Noto Sans JP', sans-serif;
        color: {COLOR_TEXT_MAIN};
        background-color: {COLOR_BG_MAIN};
    }}
    .stApp {{ background-color: {COLOR_BG_MAIN}; }}
    
    [data-testid="stSidebar"] {{ background-color: {COLOR_BG_SIDE}; border-right: 1px solid {COLOR_BORDER}; }}
    [data-testid="stSidebar"] * {{ color: {COLOR_TEXT_MAIN} !important; }}
    
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
        background-color: {COLOR_BG_CARD} !important;
        color: {COLOR_TEXT_MAIN} !important;
        border: 1px solid {COLOR_BORDER} !important;
        border-radius: 8px !important;
    }}
    
    div.stButton > button {{
        background-color: {COLOR_ACCENT} !important;
        color: #FFFFFF !important;
        border: none; border-radius: 6px;
    }}
    
    .chat-user {{ background: {COLOR_BG_CARD}; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid {COLOR_BORDER}; }}
    .chat-owl {{ background: transparent; padding: 15px; margin-bottom: 10px; border-bottom: 1px solid {COLOR_BORDER}; }}
    
    .login-box {{ max-width: 400px; margin: 100px auto; padding: 40px; background: {COLOR_BG_CARD}; border-radius: 12px; text-align: center; }}
</style>
""", unsafe_allow_html=True)

DB_PATH = "owl_v3_core.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, name TEXT, role TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS tasks (task_id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, title TEXT, assignee TEXT, status TEXT DEFAULT 'TODO', priority TEXT, created_at DATETIME)")
    c.execute("CREATE TABLE IF NOT EXISTS team_chat (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, message TEXT, created_at DATETIME)")
    c.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, module TEXT, content TEXT, rating TEXT, created_at DATETIME)")
    c.execute("CREATE TABLE IF NOT EXISTS knowledge_base (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, title TEXT, content TEXT, meta TEXT, created_at DATETIME)")
    c.execute("INSERT OR IGNORE INTO users VALUES ('ren', 'Ren', 'Owner')")
    c.execute("INSERT OR IGNORE INTO users VALUES ('shu', 'Shu', 'Member')")
    conn.commit()
    conn.close()

init_db()

# --- 2. バックエンドロジック ---

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

def add_task(title, assignee, prio):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO tasks (project_id, title, assignee, status, priority, created_at) VALUES ('general', ?, ?, 'TODO', ?, ?)", (title, assignee, prio, datetime.now()))
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
    conn.execute("INSERT INTO feedback (project_id, module, content, rating, created_at) VALUES (?, ?, ?, ?, ?)", (pid, module, content, rating, datetime.now()))
    conn.commit()
    conn.close()

def save_knowledge(k_type, title, content, meta=""):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO knowledge_base (type, title, content, meta, created_at) VALUES (?, ?, ?, ?, ?)", (k_type, title, content, meta, datetime.now()))
    conn.commit()
    conn.close()

def get_knowledge_summary():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT id, type, title, created_at FROM knowledge_base ORDER BY created_at DESC LIMIT 5", conn)
    conn.close()
    return df

def fetch_url_content(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else url
        paragraphs = soup.find_all('p')
        text_content = "\n".join([p.get_text() for p in paragraphs])
        return title, text_content[:5000]
    except Exception as e:
        return "Error", str(e)

def analyze_image(client, image_file):
    image_file.seek(0)
    b64 = base64.b64encode(image_file.read()).decode('utf-8')
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": [{"type": "text", "text": "この画像を詳細に分析してください。"}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]
    )
    return res.choices[0].message.content

def generate_image(client, prompt):
    res = client.images.generate(model="dall-e-3", prompt=prompt, size="1024x1024", quality="standard", n=1)
    return res.data[0].url

# --- 3. ログイン ---
if 'user' not in st.session_state: st.session_state['user'] = None
if not st.session_state['user']:
    st.markdown(f"<div class='login-box'><h1>🦉 Owl v3.6.2</h1><p>Athenalink Operation System</p></div>", unsafe_allow_html=True)
    _, c2, _ = st.columns([1,1,1])
    with c2:
        with st.form("login"):
            uid = st.selectbox("Select User", ["ren", "shu"])
            if st.form_submit_button("LOGIN"):
                st.session_state['user'] = uid
                st.rerun()
    st.stop()

current_user = st.session_state['user']
user_name = get_user_name(current_user)

# --- 4. レイアウト & モジュール ---

st.sidebar.markdown(f"### 🦉 Owl v3.6.2")
st.sidebar.markdown(f"<p style='color:#9CA3AF;'>User: {user_name}</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

menu = st.sidebar.radio("MENU", ["Dashboard", "Team Chat", "M4 Strategy", "M1 SNS", "M2 Editor", "M3 Sales"])

st.sidebar.markdown("---")
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
client = OpenAI(api_key=api_key) if api_key else None

# === 新機能：タスク追加フォーム（常時表示） ===
st.sidebar.markdown("---")
with st.sidebar.expander("➕ タスク追加", expanded=False):
    with st.form("quick_add_task"):
        new_task_title = st.text_input("タスク名")
        new_task_prio = st.selectbox("優先度", ["High", "Middle", "Low"])
        if st.form_submit_button("追加"):
            add_task(new_task_title, current_user, new_task_prio)
            st.rerun()

if st.sidebar.button("Logout"):
    st.session_state['user'] = None
    st.rerun()

# --- インプット拡張 (サイドバー) ---
if menu != "Dashboard" and menu != "Team Chat":
    st.sidebar.markdown("### 📥 Input & Learn")
    input_type = st.sidebar.selectbox("Type", ["URL", "Image"])

    if input_type == "URL":
        url_input = st.sidebar.text_input("URL")
        if st.sidebar.button("Fetch & Learn"):
            if url_input:
                with st.spinner("Fetching..."):
                    title, content = fetch_url_content(url_input)
                    save_knowledge("url", title, content, meta=url_input)
                    st.session_state['last_knowledge'] = content
                    st.sidebar.success("Learned!")

    elif input_type == "Image":
        up_img = st.sidebar.file_uploader("Upload Image", type=["jpg", "png"])
        if up_img and client:
            if st.sidebar.button("Analyze & Learn"):
                with st.spinner("Analyzing..."):
                    content = analyze_image(client, up_img)
                    save_knowledge("image", up_img.name, content)
                    st.session_state['last_knowledge'] = content
                    st.sidebar.success("Learned!")

# --- アダプティブ設定 ---
adaptive_prompt = ""
if menu in ["M1 SNS", "M2 Editor", "M3 Sales"]:
    st.sidebar.markdown("### 🎛 Output Settings")
    MEDIA_TYPES = {
        "X (Short)": "140字以内、共感重視",
        "X (Thread)": "5〜10ツイート構成",
        "note (Free)": "2000字、共感→解決",
        "note (Paid)": "5000字以上、PASONA",
        "LP": "10000字規模、成約重視"
    }
    sel_media = st.sidebar.selectbox("Media", list(MEDIA_TYPES.keys()))
    sel_depth = st.sidebar.selectbox("Depth", ["Light", "Standard", "Deep"])
    adaptive_prompt = f"\n【出力設定】媒体:{sel_media} ({MEDIA_TYPES[sel_media]}), 深度:{sel_depth}\n"

# --- プロンプト定義 (恋愛コンテンツ特化) ---
# ここで「個人の相談ではなく、マーケティングコンテンツ作成である」と明確に定義して拒否を防ぐ
STYLE = """
【重要：役割定義】
あなたは「恋愛系メディアのプロコンテンツライター」です。
ユーザー（私）は編集長であり、あなたに「一般読者に向けた記事やポストの作成」を依頼しています。
これは特定の個人のプライベートな相談ではなく、多くの読者に価値を提供するための「創作活動」および「マーケティング業務」です。
したがって、「個人的な相談には乗れない」といった拒否は一切不要です。
読者（ペルソナ）の感情に深く寄り添い、恋愛の悩みを解決する魅力的なコンテンツを作成してください。

【基本スタイル】
1. 言語: 日本語
2. 禁止: 自分語り、ポエム、説教、AI特有の拒否文言
3. 構成: 受容(Empathy) → 分析(Analysis) → 解決(Solution)
4. トーン: 頼れる姉御肌、もしくは冷静なカウンセラー
"""

# --- チャットロジック ---
def render_chat(mode, system_prompt):
    if not client: st.warning("API Key Required"); return
    
    full_prompt = system_prompt + adaptive_prompt + STYLE
    if 'last_knowledge' in st.session_state:
        full_prompt += f"\n\n【学習データ参照】\n{st.session_state['last_knowledge']}\n"
    
    full_prompt += "\n【思考プロセス】1.ターゲット読者の感情を想像 2.構成案作成 3.執筆 (出力は結果のみ)"

    key = f"chat_{current_user}_{mode}"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": full_prompt}]
        st.session_state[key].append({"role": "assistant", "content": "準備完了。コンテンツの指示をください。"})
    
    st.session_state[key][0]["content"] = full_prompt

    for i, msg in enumerate(st.session_state[key]):
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user"><b>You</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
        elif msg["role"] == "assistant":
            if msg["content"].startswith("http") and "dalle" in msg["content"]:
                st.image(msg["content"], caption="Generated Image")
            else:
                st.markdown(f'<div class="chat-owl"><b>Owl</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
            
            # --- 評価ボタン (押下状態を保存・表示) ---
            fb_key_good = f"fb_good_{key}_{i}"
            fb_key_bad = f"fb_bad_{key}_{i}"
            
            # 既に評価済みかチェック
            voted = False
            if st.session_state.get(fb_key_good):
                st.success("✅ Good評価済み")
                voted = True
            elif st.session_state.get(fb_key_bad):
                st.error("☑️ Bad評価済み")
                voted = True
            
            if not voted:
                c1, c2, _ = st.columns([1, 1, 10])
                with c1:
                    if st.button("👍", key=f"btn_good_{key}_{i}"):
                        save_feedback(current_user, mode, msg["content"], "good")
                        st.session_state[fb_key_good] = True # 状態保存
                        st.rerun()
                with c2:
                    if st.button("👎", key=f"btn_bad_{key}_{i}"):
                        save_feedback(current_user, mode, msg["content"], "bad")
                        st.session_state[fb_key_bad] = True # 状態保存
                        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    with st.form(key=f"form_{mode}", clear_on_submit=True):
        user_input = st.text_area("Message Owl...", height=100)
        if st.form_submit_button("Send") and user_input:
            if mode == "M1 SNS" and ("画像" in user_input and ("作って" in user_input or "生成" in user_input)):
                st.session_state[key].append({"role": "user", "content": user_input})
                with st.spinner("Generating Image..."):
                    try:
                        img_url = generate_image(client, user_input)
                        st.session_state[key].append({"role": "assistant", "content": img_url})
                        st.rerun()
                    except Exception as e: st.error(str(e))
            else:
                st.session_state[key].append({"role": "user", "content": user_input})
                try:
                    with st.spinner("Thinking..."):
                        res = client.chat.completions.create(model="gpt-3.5-turbo", messages=st.session_state[key], max_tokens=3000)
                    st.session_state[key].append({"role": "assistant", "content": res.choices[0].message.content})
                    st.rerun()
                except Exception as e: st.error(str(e))

# --- コンテンツ ---

if menu == "Dashboard":
    st.markdown(f"## Welcome back, {user_name}")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔥 My Tasks")
        tasks = get_tasks(current_user).head(5)
        if not tasks.empty:
            for i, t in tasks.iterrows():
                st.markdown(f'<div class="chat-user"><b>{t["title"]}</b> <span style="float:right; color:#EF4444;">{t["priority"]}</span></div>', unsafe_allow_html=True)
                if st.button("Done", key=f"d_{t['task_id']}"): complete_task(t['task_id']); st.rerun()
        else: st.info("No tasks.")
        
        st.markdown("### 📚 Recent Knowledge")
        knowledge = get_knowledge_summary()
        st.dataframe(knowledge, hide_index=True)

    with c2:
        st.markdown("### 💬 Team Chat")
        chats = get_team_chat().head(3)
        for i, c in chats.iterrows():
            st.markdown(f'<div class="chat-owl"><small>{c["user_id"]} • {c["created_at"]}</small><br>{c["message"]}</div>', unsafe_allow_html=True)

elif menu == "Team Chat":
    st.markdown("## Team Chat")
    with st.form("team_chat"):
        msg = st.text_area("Message...")
        if st.form_submit_button("Send") and msg: send_team_chat(current_user, msg); st.rerun()
    chats = get_team_chat()
    for i, c in chats.iterrows():
        align = "right" if c['user_id'] == current_user else "left"
        bg = "#1F2937" if c['user_id'] == current_user else "transparent"
        st.markdown(f'<div style="text-align:{align}"><div style="background:{bg}; padding:10px; border-radius:10px; display:inline-block; border:1px solid #333;">{c["message"]}</div><br><small style="color:#666;">{c["user_id"]}</small></div>', unsafe_allow_html=True)

elif menu == "M4 Strategy":
    render_chat("M4 Strategy", "あなたはアテナリンクの最高戦略責任者です。")
elif menu == "M1 SNS":
    render_chat("M1 SNS", "あなたはSNSマーケターです。読者の心を代弁し、バズる投稿を作成してください。")
elif menu == "M2 Editor":
    render_chat("M2 Editor", "あなたは編集者です。読者が納得し、行動したくなる記事構成を作成してください。")
elif menu == "M3 Sales":
    render_chat("M3 Sales", "あなたは解決型セールスライターです。PASONA等のフレームワークを用いて、成約率の高いレターを書いてください。")
