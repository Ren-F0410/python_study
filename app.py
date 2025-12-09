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
st.set_page_config(page_title="Owl v3.6.3", page_icon="🦉", layout="wide")

# カラーパレット
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
    html, body, [class*="css"] {{ font-family: 'Noto Sans JP', sans-serif; color: {COLOR_TEXT_MAIN}; background-color: {COLOR_BG_MAIN}; }}
    .stApp {{ background-color: {COLOR_BG_MAIN}; }}
    [data-testid="stSidebar"] {{ background-color: {COLOR_BG_SIDE}; border-right: 1px solid {COLOR_BORDER}; }}
    [data-testid="stSidebar"] * {{ color: {COLOR_TEXT_MAIN} !important; }}
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{ background-color: {COLOR_BG_CARD} !important; color: {COLOR_TEXT_MAIN} !important; border: 1px solid {COLOR_BORDER} !important; border-radius: 8px !important; }}
    div.stButton > button {{ background-color: {COLOR_ACCENT} !important; color: #FFFFFF !important; border: none; border-radius: 6px; }}
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
    c.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, module TEXT, content TEXT, rating TEXT, comment TEXT, created_at DATETIME)")
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

# URL解析 (強化版: User-Agent追加)
def fetch_url_content(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding # 文字化け防止
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else url
        
        # 不要なタグ削除
        for script in soup(["script", "style"]):
            script.decompose()
            
        text = soup.get_text()
        # 空行削除
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return title, text[:10000] # 文字数制限
    except Exception as e:
        return "Error", f"取得失敗: {str(e)}"

def analyze_image(client, image_file):
    image_file.seek(0)
    b64 = base64.b64encode(image_file.read()).decode('utf-8')
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": [{"type": "text", "text": "分析してください。"}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]
    )
    return res.choices[0].message.content

def generate_image(client, prompt):
    res = client.images.generate(model="dall-e-3", prompt=prompt, size="1024x1024", quality="standard", n=1)
    return res.data[0].url

# --- 3. ログイン ---
if 'user' not in st.session_state: st.session_state['user'] = None
if not st.session_state['user']:
    st.markdown(f"<div class='login-box'><h1>🦉 Owl v3.6.3</h1><p>Athenalink Operation System</p></div>", unsafe_allow_html=True)
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
st.sidebar.markdown(f"### 🦉 Owl v3.6.3")
st.sidebar.markdown(f"<p style='color:#9CA3AF;'>User: {user_name}</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")
menu = st.sidebar.radio("MENU", ["Dashboard", "Team Chat", "M4 Strategy", "M1 SNS", "M2 Editor", "M3 Sales"])
st.sidebar.markdown("---")
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
client = OpenAI(api_key=api_key) if api_key else None

st.sidebar.markdown("---")
with st.sidebar.expander("➕ タスク追加"):
    with st.form("quick_add_task"):
        new_task_title = st.text_input("タスク名")
        new_task_prio = st.selectbox("優先度", ["High", "Middle", "Low"])
        if st.form_submit_button("追加"):
            add_task(new_task_title, current_user, new_task_prio)
            st.rerun()

if st.sidebar.button("Logout"):
    st.session_state['user'] = None
    st.rerun()

# --- インプット拡張 (画像のみサイドバーに残す) ---
if menu != "Dashboard" and menu != "Team Chat":
    st.sidebar.markdown("### 👁️ Image Input")
    up_img = st.sidebar.file_uploader("Upload Image", type=["jpg", "png"])
    if up_img and client:
        if st.sidebar.button("Analyze & Learn"):
            with st.spinner("Analyzing..."):
                content = analyze_image(client, up_img)
                save_knowledge("image", up_img.name, content)
                st.session_state['last_knowledge'] = content
                st.sidebar.success("Learned!")

adaptive_prompt = ""
if menu in ["M1 SNS", "M2 Editor", "M3 Sales"]:
    st.sidebar.markdown("### 🎛 Settings")
    MEDIA_TYPES = {"X (Short)": "140字", "X (Thread)": "スレッド", "note (Free)": "記事", "note (Paid)": "有料", "LP": "LP"}
    sel_media = st.sidebar.selectbox("Media", list(MEDIA_TYPES.keys()))
    sel_depth = st.sidebar.selectbox("Depth", ["Light", "Standard", "Deep"])
    adaptive_prompt = f"\n【出力設定】媒体:{sel_media}, 深度:{sel_depth}\n"

# --- プロンプト定義 ---
STYLE = """
【役割】あなたは恋愛メディアのプロライターです。ユーザーは編集長です。
これはマーケティング業務であり、個人の相談ではありません。「相談に乗れない」等の拒否は禁止です。
読者の感情に寄り添い、具体的な解決策を提示するコンテンツを作成してください。
"""

# --- チャットロジック (URL自動読み込み機能付き) ---
def render_chat(mode, system_prompt):
    if not client: st.warning("API Key Required"); return
    
    full_prompt = system_prompt + adaptive_prompt + STYLE
    if 'last_knowledge' in st.session_state:
        full_prompt += f"\n\n【直近の学習データ】\n{st.session_state['last_knowledge']}\n"
    
    key = f"chat_{current_user}_{mode}"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": full_prompt}]
        st.session_state[key].append({"role": "assistant", "content": "準備完了。URLがあれば貼ってください。自動で読み込みます。"})
    
    st.session_state[key][0]["content"] = full_prompt

    for i, msg in enumerate(st.session_state[key]):
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user"><b>You</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
        elif msg["role"] == "assistant":
            if msg["content"].startswith("http") and "dalle" in msg["content"]:
                st.image(msg["content"], caption="Generated Image")
            else:
                st.markdown(f'<div class="chat-owl"><b>Owl</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
            
            # 評価ボタン
            voted_good = st.session_state.get(f"fb_good_{key}_{i}")
            voted_bad = st.session_state.get(f"fb_bad_{key}_{i}")
            
            if voted_good: st.success("✅ Good")
            elif voted_bad: st.error("☑️ Bad")
            else:
                c1, c2, _ = st.columns([1, 1, 10])
                with c1:
                    if st.button("👍", key=f"btn_g_{key}_{i}"):
                        save_feedback(current_user, mode, msg["content"], "good")
                        st.session_state[f"fb_good_{key}_{i}"] = True
                        st.rerun()
                with c2:
                    if st.button("👎", key=f"btn_b_{key}_{i}"):
                        save_feedback(current_user, mode, msg["content"], "bad")
                        st.session_state[f"fb_bad_{key}_{i}"] = True
                        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    with st.form(key=f"form_{mode}", clear_on_submit=True):
        user_input = st.text_area("Message Owl...", height=100)
        if st.form_submit_button("Send") and user_input:
            
            # --- URL自動読み込みロジック ---
            url_content = ""
            if user_input.startswith("http"):
                with st.spinner("🌍 URLの内容を読み込んでいます..."):
                    title, content = fetch_url_content(user_input)
                    if title != "Error":
                        url_content = f"\n\n【読み込んだURLの内容】\nタイトル: {title}\n本文: {content}\n"
                        save_knowledge("url", title, content, meta=user_input)
                        st.success(f"URLを学習しました: {title}")
                    else:
                        st.error(f"URLの読み込みに失敗しました: {content}")
            
            # メッセージ構築
            final_input = user_input + url_content
            st.session_state[key].append({"role": "user", "content": user_input}) # 表示はURLのみ
            
            # 画像生成 or テキスト生成
            if mode == "M1 SNS" and ("画像" in user_input and ("作って" in user_input or "生成" in user_input)):
                with st.spinner("Generating Image..."):
                    try:
                        img_url = generate_image(client, user_input)
                        st.session_state[key].append({"role": "assistant", "content": img_url})
                        st.rerun()
                    except Exception as e: st.error(str(e))
            else:
                # URL内容を含めてAIに渡す
                messages_for_api = st.session_state[key].copy()
                messages_for_api[-1]["content"] = final_input
                
                try:
                    with st.spinner("Thinking..."):
                        res = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages_for_api, max_tokens=3000)
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

elif menu == "M4 Strategy": render_chat("M4 Strategy", "あなたは戦略責任者です。")
elif menu == "M1 SNS": render_chat("M1 SNS", "あなたはSNSマーケターです。")
elif menu == "M2 Editor": render_chat("M2 Editor", "あなたは編集者です。")
elif menu == "M3 Sales": render_chat("M3 Sales", "あなたはセールスライターです。")
