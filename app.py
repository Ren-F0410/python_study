import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI
import base64
import requests
from bs4 import BeautifulSoup
import io
import re

# --- 1. アプリ設定 & デザイン (v3.5 Dark Theme) ---
st.set_page_config(page_title="Owl v3.6.8", page_icon="🦉", layout="wide")

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
    
    /* チャットバブル */
    .chat-user {{ background: {COLOR_BG_CARD}; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid {COLOR_BORDER}; }}
    .chat-owl {{ background: transparent; padding: 15px; margin-bottom: 10px; border-bottom: 1px solid {COLOR_BORDER}; }}
    .chat-system {{ background: #1F2937; padding: 10px; border-radius: 4px; border-left: 4px solid {COLOR_ACCENT}; margin-bottom: 10px; font-size: 0.9rem; color: #E5E7EB; }}
    
    /* ログインボックス */
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

def add_task(title, assignee, prio):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO tasks (project_id, title, assignee, status, priority, created_at) VALUES ('general', ?, ?, 'TODO', ?, ?)", (title, assignee, prio, datetime.now()))
    conn.commit()
    conn.close()

def get_tasks(uid=None):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM tasks WHERE status != 'DONE' ORDER BY priority DESC, created_at DESC", conn)
    conn.close()
    return df

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

# --- ナレッジベース関連 (Core Logic) ---

def save_knowledge(k_type, title, content, meta=""):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO knowledge_base (type, title, content, meta, created_at) VALUES (?, ?, ?, ?, ?)", (k_type, title, content, meta, datetime.now()))
    conn.commit()
    conn.close()

def get_recent_knowledge(limit=3):
    """直近の学習データを取得してコンテキスト用に整形する"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(f"SELECT type, title, content FROM knowledge_base ORDER BY created_at DESC LIMIT {limit}", conn)
    conn.close()
    
    if df.empty:
        return ""
    
    context_text = "\n【Owlが現在保持している学習データ (Context)】\n"
    for i, row in df.iterrows():
        context_text += f"- [{row['type'].upper()}] {row['title']}: {row['content'][:300]}...\n"
    context_text += "※ ユーザーの指示には、上記の学習データを踏まえて回答してください。\n"
    return context_text

def get_knowledge_summary():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT id, type, title, created_at FROM knowledge_base ORDER BY created_at DESC LIMIT 5", conn)
    conn.close()
    return df

# --- URL & 画像解析 ---

def extract_url(text):
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
    return urls[0] if urls else None

def fetch_and_summarize_url(client, url):
    """URLを取得し、LLMで要約してDBに保存する"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        # 1. Fetch
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # タイトル取得
        title = soup.title.string if soup.title else url
        
        # 本文抽出（スクリプト除去）
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()
        text_content = soup.get_text()
        text_content = ' '.join(text_content.split())[:10000] # 長すぎるとエラーになるのでカット
        
        # Xなどのブロック検知
        if "JavaScript" in text_content and "enable" in text_content:
            return False, "サイトのセキュリティにより読み込めませんでした（スクショ推奨）", ""

        # 2. Summarize (LLM)
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "以下のWEB記事のテキストを読み、タイトルと、重要なポイントを3〜5個の箇条書きで要約してください。"},
                {"role": "user", "content": text_content[:3000]}
            ]
        )
        summary = res.choices[0].message.content
        
        # 3. Save
        full_data = f"【要約】\n{summary}\n\n【本文抜粋】\n{text_content[:2000]}"
        save_knowledge("url", title, full_data, meta=url)
        
        return True, title, summary

    except Exception as e:
        return False, f"エラー: {str(e)}", ""

def process_uploaded_image(client, image_file):
    """画像をVisionモデルで解析し、DBに保存する"""
    image_file.seek(0)
    b64 = base64.b64encode(image_file.read()).decode('utf-8')
    
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "この画像の内容を詳細に分析してください。SNS投稿の参考にするため、文字情報、デザイン、雰囲気、訴求ポイントを言語化してください。"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ]}]
    )
    description = res.choices[0].message.content
    save_knowledge("image", image_file.name, description)
    return description

def generate_image(client, prompt):
    res = client.images.generate(model="dall-e-3", prompt=prompt, size="1024x1024", quality="standard", n=1)
    return res.data[0].url

# --- 3. ログイン ---
if 'user' not in st.session_state: st.session_state['user'] = None
if not st.session_state['user']:
    st.markdown(f"<div class='login-box'><h1>🦉 Owl v3.6.8</h1><p>Athenalink Operation System</p></div>", unsafe_allow_html=True)
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
st.sidebar.markdown(f"### 🦉 Owl v3.6.8")
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
        t = st.text_input("Task")
        p = st.selectbox("Priority", ["High", "Medium", "Low"])
        if st.form_submit_button("Add"):
            add_task(t, current_user, p)
            st.rerun()

if st.sidebar.button("Logout"):
    st.session_state['user'] = None
    st.rerun()

# --- アダプティブ設定 ---
adaptive_prompt = ""
if menu in ["M1 SNS", "M2 Editor", "M3 Sales"]:
    st.sidebar.markdown("### 🎛 Settings")
    MEDIA_TYPES = {"X (Short)": "140字", "X (Thread)": "スレッド", "note (Article)": "記事", "LP": "LP"}
    sel_media = st.sidebar.selectbox("Media", list(MEDIA_TYPES.keys()))
    sel_depth = st.sidebar.selectbox("Depth", ["Light", "Standard", "Deep"])
    adaptive_prompt = f"\n【出力設定】媒体:{sel_media}, 深度:{sel_depth}\n"

# --- プロンプト定義 ---
STYLE = """
【役割】あなたは恋愛メディアのプロライターです。
マーケティング業務として、読者の感情に寄り添い、具体的な解決策を提示するコンテンツを作成してください。
"""

# --- チャットロジック (URL & 画像の統合処理) ---
def render_chat(mode, system_prompt):
    if not client: st.warning("API Key Required"); return
    
    # 1. コンテキストの構築 (DBから最新知識を取得)
    recent_knowledge = get_recent_knowledge()
    
    # 2. プロンプト組立
    full_prompt = system_prompt + adaptive_prompt + STYLE + recent_knowledge
    full_prompt += "\n【思考プロセス】1.感情エミュレーション 2.構成案作成 3.執筆 (出力は結果のみ)"

    key = f"chat_{current_user}_{mode}"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": full_prompt}]
        st.session_state[key].append({"role": "assistant", "content": "準備完了。指示をください。"})
    
    # 常に最新の知識状態にアップデート
    st.session_state[key][0]["content"] = full_prompt

    # 3. チャットログ表示
    for i, msg in enumerate(st.session_state[key]):
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user"><b>You</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
        elif msg["role"] == "assistant":
            # システム通知（URL読み込み完了など）は別のスタイルで表示
            if "✅" in msg["content"] and ("読み込みました" in msg["content"] or "完了" in msg["content"]):
                st.markdown(f'<div class="chat-system">{msg["content"]}</div>', unsafe_allow_html=True)
            elif msg["content"].startswith("http") and "dalle" in msg["content"]:
                st.image(msg["content"], caption="Generated Image")
            else:
                st.markdown(f'<div class="chat-owl"><b>Owl</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
                
                # 評価ボタン
                c1, c2, _ = st.columns([1, 1, 10])
                with c1:
                    if st.button("👍", key=f"g_{key}_{i}"): save_feedback(current_user, mode, msg["content"], "good")
                with c2:
                    if st.button("👎", key=f"b_{key}_{i}"): save_feedback(current_user, mode, msg["content"], "bad")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 4. 画像アップローダー (メイン画面)
    with st.expander("📎 画像を添付する (ここをクリック)", expanded=False):
        uploaded_img = st.file_uploader("画像を選択", type=["jpg", "png"], key=f"up_{mode}")
        if uploaded_img:
            if st.button("画像を読み込む"):
                with st.spinner("画像を分析中..."):
                    desc = process_uploaded_image(client, uploaded_img)
                    # 履歴にシステムメッセージとして追加
                    st.session_state[key].append({"role": "assistant", "content": f"✅ 画像『{uploaded_img.name}』を読み込みました。\n【分析結果】\n{desc[:200]}..."})
                    st.rerun()

    # 5. テキスト入力処理
    with st.form(key=f"form_{mode}", clear_on_submit=True):
        user_input = st.text_area("Message Owl...", height=100)
        if st.form_submit_button("Send") and user_input:
            
            # A. URLが含まれているかチェック
            extracted_url = extract_url(user_input)
            if extracted_url:
                with st.spinner("🌍 URLを読み込んでいます..."):
                    success, title, summary = fetch_and_summarize_url(client, extracted_url)
                    
                    if success:
                        # 成功時：履歴にシステムメッセージとして追加
                        system_msg = f"✅ URLを読み込みました: **{title}**\n\n【要約】\n{summary}"
                        st.session_state[key].append({"role": "user", "content": user_input})
                        st.session_state[key].append({"role": "assistant", "content": system_msg})
                        st.rerun()
                    else:
                        # 失敗時
                        st.error(f"URL読み込み失敗: {title}")
                        # 失敗しても、ユーザーの発言として残して、AIに「読めなかった」前提で答えさせる
            
            # B. 通常の会話処理 (URL処理後、またはURLなしの場合)
            if not extracted_url:
                st.session_state[key].append({"role": "user", "content": user_input})
                
                # 画像生成トリガー
                if mode == "M1 SNS" and ("画像" in user_input and ("作って" in user_input or "生成" in user_input)):
                    with st.spinner("Generating Image..."):
                        try:
                            img_url = generate_image(client, user_input)
                            st.session_state[key].append({"role": "assistant", "content": img_url})
                            st.rerun()
                        except Exception as e: st.error(str(e))
                else:
                    # テキスト生成
                    try:
                        with st.spinner("Thinking..."):
                            # 最新のknowledgeを含んだプロンプトでリクエスト
                            # ※ st.session_state[key] は直前で update されている
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

elif menu == "M4 Strategy": render_chat("M4 Strategy", "あなたは戦略責任者です。")
elif menu == "M1 SNS": render_chat("M1 SNS", "あなたはSNSマーケターです。")
elif menu == "M2 Editor": render_chat("M2 Editor", "あなたは編集者です。")
elif menu == "M3 Sales": render_chat("M3 Sales", "あなたはセールスライターです。")
