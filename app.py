import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI
import base64
import requests
from bs4 import BeautifulSoup # 必要なら pip install beautifulsoup4
import io

# --- 1. アプリ設定 & デザイン (v3.5ベース) ---
st.set_page_config(page_title="Owl v3.6", page_icon="🦉", layout="wide")

# カラーパレット定義 (ChatGPT Dark Theme)
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
    c.execute("CREATE TABLE IF NOT EXISTS projects (project_id TEXT PRIMARY KEY, name TEXT, goal TEXT, owner_id TEXT, created_at DATETIME)")
    c.execute("CREATE TABLE IF NOT EXISTS tasks (task_id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, title TEXT, assignee TEXT, status TEXT DEFAULT 'TODO', priority TEXT, created_at DATETIME)")
    c.execute("CREATE TABLE IF NOT EXISTS team_chat (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, message TEXT, created_at DATETIME)")
    c.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, module TEXT, content TEXT, rating TEXT, comment TEXT, created_at DATETIME)")
    # 新: ナレッジベース
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

# タスク管理
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

# チームチャット
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

# フィードバック
def save_feedback(pid, module, content, rating):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO feedback (project_id, module, content, rating, created_at) VALUES (?, ?, ?, ?, ?)", (pid, module, content, rating, datetime.now()))
    conn.commit()
    conn.close()
    st.toast(f"Feedback: {rating}")

# ナレッジベース
def save_knowledge(k_type, title, content, meta=""):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO knowledge_base (type, title, content, meta, created_at) VALUES (?, ?, ?, ?, ?)", (k_type, title, content, meta, datetime.now()))
    conn.commit()
    conn.close()
    st.toast("Knowledge Saved to DB")

def get_knowledge_summary():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT id, type, title, created_at FROM knowledge_base ORDER BY created_at DESC LIMIT 5", conn)
    conn.close()
    return df

# URL解析 (簡易版)
def fetch_url_content(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # タイトルと本文抽出（簡易ロジック）
        title = soup.title.string if soup.title else url
        paragraphs = soup.find_all('p')
        text_content = "\n".join([p.get_text() for p in paragraphs])
        
        # 長すぎる場合はカット
        return title, text_content[:5000]
    except Exception as e:
        return "Error", str(e)

# 画像解析 (GPT-4o-mini)
def analyze_image(client, image_file):
    image_file.seek(0)
    b64 = base64.b64encode(image_file.read()).decode('utf-8')
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": [{"type": "text", "text": "この画像の内容（構成、文字、雰囲気）を詳細にテキスト化してください。これは後でコンテンツ制作の参考にします。"}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]
    )
    return res.choices[0].message.content

# 画像生成 (DALL-E 3)
def generate_image(client, prompt):
    res = client.images.generate(model="dall-e-3", prompt=prompt, size="1024x1024", quality="standard", n=1)
    return res.data[0].url

# --- 3. ログイン ---
if 'user' not in st.session_state: st.session_state['user'] = None
if not st.session_state['user']:
    st.markdown(f"<div class='login-box'><h1>🦉 Owl v3.6</h1><p>Athenalink Operation System</p></div>", unsafe_allow_html=True)
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

st.sidebar.markdown(f"### 🦉 Owl v3.6")
st.sidebar.markdown(f"<p style='color:#9CA3AF;'>User: {user_name}</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

menu = st.sidebar.radio("MENU", ["Dashboard", "Team Chat", "M4 Strategy", "M1 SNS", "M2 Editor", "M3 Sales"])

st.sidebar.markdown("---")
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
client = OpenAI(api_key=api_key) if api_key else None

if st.sidebar.button("Logout"):
    st.session_state['user'] = None
    st.rerun()

# --- インプット拡張 (サイドバー) ---
st.sidebar.markdown("### 📥 Input & Learn")
input_type = st.sidebar.selectbox("Type", ["URL", "Image", "Text Memo"])

if input_type == "URL":
    url_input = st.sidebar.text_input("URL")
    if st.sidebar.button("Fetch & Learn"):
        if url_input:
            with st.spinner("Fetching..."):
                title, content = fetch_url_content(url_input)
                save_knowledge("url", title, content, meta=url_input)
                st.session_state['last_knowledge'] = content # 直近のコンテキストとして保持
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
        "X (Short)": "140字以内、共感重視、拡散狙い",
        "X (Thread)": "5〜10ツイート構成、ストーリーテリング",
        "note (Free)": "2000〜3000字、導入→共感→解決策",
        "note (Paid)": "5000字以上、PASONA法、熱量高め",
        "LP": "10000字規模、QUESTフォーマット、成約重視"
    }
    
    sel_media = st.sidebar.selectbox("Media", list(MEDIA_TYPES.keys()))
    sel_depth = st.sidebar.selectbox("Depth", ["Light", "Standard", "Deep"])
    
    adaptive_prompt = (
        f"\n【出力モード設定】\n"
        f"・媒体: {sel_media} ({MEDIA_TYPES[sel_media]})\n"
        f"・深度: {sel_depth}\n"
        "※ 上記設定に基づき、最適な構成・文字数・トーンで出力してください。\n"
    )

# --- チャットロジック ---
def render_chat(mode, system_prompt):
    if not client: st.warning("API Key Required"); return
    
    # プロンプト組立
    full_prompt = system_prompt + adaptive_prompt
    if 'last_knowledge' in st.session_state:
        full_prompt += f"\n\n【直近の学習データ（これを参考にしてください）】\n{st.session_state['last_knowledge']}\n"
    
    full_prompt += "\n【思考プロセス】1.感情エミュレーション 2.構成案作成 3.執筆 (出力は結果のみ)"

    key = f"chat_{current_user}_{mode}"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": full_prompt}]
        st.session_state[key].append({"role": "assistant", "content": "準備完了。指示をください。"})
    
    # 常に最新設定を反映
    st.session_state[key][0]["content"] = full_prompt

    # ログ表示
    for i, msg in enumerate(st.session_state[key]):
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user"><b>You</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
        elif msg["role"] == "assistant":
            st.markdown(f'<div class="chat-owl"><b>Owl</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
            # 評価
            c1, c2, _ = st.columns([1, 1, 10])
            with c1:
                if st.button("👍", key=f"g_{key}_{i}"): save_feedback(current_user, mode, msg["content"], "good")
            with c2:
                if st.button("👎", key=f"b_{key}_{i}"): save_feedback(current_user, mode, msg["content"], "bad")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 入力
    with st.form(key=f"form_{mode}", clear_on_submit=True):
        user_input = st.text_area("Message Owl...", height=100)
        c1, c2 = st.columns([6, 1])
        with c2:
            st.write("")
            submit = st.form_submit_button("Send")
    
    if submit and user_input:
        # 画像生成トリガー
        if "画像" in user_input and ("作って" in user_input or "生成" in user_input) and mode == "M1 SNS":
            st.session_state[key].append({"role": "user", "content": user_input})
            with st.spinner("Generating Image..."):
                try:
                    img_url = generate_image(client, user_input)
                    st.session_state[key].append({"role": "assistant", "content": f"![Generated Image]({img_url})"})
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

# プロンプト定義
STYLE = "【スタイル】\n1.言語:日本語\n2.禁止:自分語り/ポエム/説教\n3.構成:受容→分析→処方\n4.態度:プロのカウンセラー"

elif menu == "M4 Strategy":
    render_chat("M4 Strategy", f"あなたはアテナリンクの最高戦略責任者です。{STYLE}")
elif menu == "M1 SNS":
    render_chat("M1 SNS", f"あなたはSNSマーケターです。読者の心を代弁し、バズる投稿を作成してください。{STYLE}")
elif menu == "M2 Editor":
    render_chat("M2 Editor", f"あなたは編集者です。読者が納得し、行動したくなる記事構成を作成してください。{STYLE}")
elif menu == "M3 Sales":
    render_chat("M3 Sales", f"あなたは解決型セールスライターです。PASONA等のフレームワークを用いて、成約率の高いレターを書いてください。{STYLE}")
