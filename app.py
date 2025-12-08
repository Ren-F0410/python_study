import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI
import base64
import io

# --- 1. 設定 & デザイン注入 ---
st.set_page_config(page_title="Owl v3.0", page_icon="🦉", layout="wide")

# カスタムCSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }
    .main-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 1.5rem; border-radius: 10px; color: white; margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 { color: white !important; margin: 0; font-size: 2rem; }
    .main-header p { color: #e0e7ff; margin: 0; font-size: 0.9rem; }
    div.stButton > button {
        background: linear-gradient(to right, #f59e0b, #d97706);
        color: white; border: none; border-radius: 8px; font-weight: bold;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3); }
    .stTextArea textarea { background-color: #1e1e1e; color: #ffffff; border: 1px solid #4b5563; border-radius: 10px; }
    .stTextArea textarea:focus { border-color: #f59e0b; box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.2); }
    [data-testid="stSidebar"] { background-color: #111827; }
    /* フィードバックボタン用のスタイル */
    .feedback-btn { padding: 0.2rem 0.5rem; font-size: 0.8rem; margin-right: 0.5rem; background: transparent !important; color: #aaa !important; border: 1px solid #444 !important; }
    .feedback-btn:hover { color: white !important; border-color: white !important; }
</style>
""", unsafe_allow_html=True)

DB_PATH = "owl.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS projects (project_id TEXT PRIMARY KEY, name TEXT, domain TEXT, goal TEXT, status TEXT DEFAULT 'active', created_at DATETIME)")
    c.execute("CREATE TABLE IF NOT EXISTS tasks (task_id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, title TEXT, status TEXT DEFAULT 'TODO', priority TEXT DEFAULT 'Middle', created_at DATETIME)")
    # フィードバック用テーブル追加
    c.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, module TEXT, content TEXT, rating TEXT, created_at DATETIME)")
    conn.commit()
    conn.close()

init_db()

# --- 2. データ & マルチモーダル関数 ---
def get_projects():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM projects", conn)
    conn.close()
    return df

def create_project(p_id, name, domain, goal):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?)", (p_id, name, domain, goal, 'active', datetime.now()))
        conn.commit()
        st.success(f"作成完了: {name}")
    except: st.error("エラー: ID重複")
    finally: conn.close()

def get_tasks(pid):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(f"SELECT * FROM tasks WHERE project_id = '{pid}' ORDER BY status DESC, priority DESC", conn)
    conn.close()
    return df

def add_task(pid, title, prio):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO tasks (project_id, title, status, priority, created_at) VALUES (?, ?, 'TODO', ?, ?)", (pid, title, prio, datetime.now()))
    conn.commit()
    conn.close()

def delete_task(tid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE task_id = ?", (tid,))
    conn.commit()
    conn.close()

def save_feedback(pid, module, content, rating):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO feedback (project_id, module, content, rating, created_at) VALUES (?, ?, ?, ?, ?)", (pid, module, content, rating, datetime.now()))
    conn.commit()
    conn.close()
    st.toast(f"フィードバックを送信しました: {rating}")

# 画像分析（GPT-4o）
def analyze_image(client, image_file):
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    response = client.chat.completions.create(
        model="gpt-4o", # マルチモーダルモデル
        messages=[
            {"role": "system", "content": "あなたは優秀な分析官です。アップロードされた画像の内容を詳細に分析し、テキストで説明してください。"},
            {"role": "user", "content": [
                {"type": "text", "text": "この画像を分析してください。"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}
        ],
        max_tokens=500
    )
    return response.choices[0].message.content

# 画像生成（DALL-E 3）
def generate_image(client, text_prompt):
    # テキストから画像プロンプトを生成
    prompt_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "以下のテキストの内容に基づき、SNS投稿に添える魅力的なアイキャッチ画像を生成するための、DALL-E用プロンプト（英語）を作成してください。"},
                  {"role": "user", "content": text_prompt}]
    )
    dalle_prompt = prompt_response.choices[0].message.content
    
    # 画像生成実行
    image_response = client.images.generate(
        model="dall-e-3",
        prompt=dalle_prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    return image_response.data[0].url

# --- 3. UIロジック ---
st.sidebar.header("🔑 System")
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
    st.sidebar.success("✅ Auto-Login")
else:
    api_key = st.sidebar.text_input("API Key", type="password")

client = OpenAI(api_key=api_key) if api_key else None

st.sidebar.header("📂 プロジェクト")
df_projects = get_projects()
current_project_id = None
if not df_projects.empty:
    opts = {row['project_id']: row['name'] for i, row in df_projects.iterrows()}
    current_project_id = st.sidebar.selectbox("選択", options=list(opts.keys()), format_func=lambda x: opts[x])

with st.sidebar.expander("➕ 新規作成"):
    with st.form("new_proj"):
        new_id = st.text_input("ID"); new_name = st.text_input("名前")
        new_dom = st.selectbox("分野", ["love_content", "owl_dev", "marketing"]); new_goal = st.text_area("目標")
        if st.form_submit_button("作成") and new_id:
            create_project(new_id, new_name, new_dom, new_goal); st.rerun()

st.sidebar.header("🚀 メニュー")
menu = st.sidebar.radio("Go", ["🏠 HOME", "✅ TASKS", "🧠 M4 戦略", "📱 M1 SNS", "📝 M2 記事", "💰 M3 販売"])

# アダプティブ設定 & マルチモーダル入力
adaptive_prompt = ""
image_analysis_result = ""

if menu in ["📱 M1 SNS", "📝 M2 記事", "💰 M3 販売"]:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎛 生成設定")
    TARGET_MEDIA = {"X (Twitter)": {"len":"140字","tone":"共感"}, "X (長文)": {"len":"1000字","tone":"物語"}, "note (記事)": {"len":"3000字","tone":"解説"}, "note (販売LP)": {"len":"5000字","tone":"解決"}, "DM/LINE": {"len":"300字","tone":"私信"}}
    DEPTH_LEVELS = {"Light": "拡散狙い", "Standard": "信頼構築", "Deep": "根本解決"}
    sel_media = st.sidebar.selectbox("媒体", list(TARGET_MEDIA.keys()))
    sel_depth = st.sidebar.selectbox("深さ", list(DEPTH_LEVELS.keys()))
    m_info = TARGET_MEDIA[sel_media]
    adaptive_prompt = f"【出力設定】媒体:{sel_media}({m_info['len']}),トーン:{m_info['tone']},深さ:{sel_depth}({DEPTH_LEVELS[sel_depth]})"
    
    st.sidebar.markdown("### 👁️ 画像分析 (β)")
    uploaded_file = st.sidebar.file_uploader("参考画像をアップロード", type=["jpg", "png", "jpeg"])
    if uploaded_file and client:
        if st.sidebar.button("画像を分析する"):
            with st.sidebar.spinner("Analyzing image..."):
                analysis = analyze_image(client, uploaded_file)
                st.session_state['image_analysis'] = analysis
                st.sidebar.success("分析完了！")

if 'image_analysis' in st.session_state:
    image_analysis_result = f"\n【参考画像分析データ】\n{st.session_state['image_analysis']}\n※この画像データも踏まえて回答してください。"
    st.sidebar.info("画像データを保持中")
    if st.sidebar.button("画像データをクリア"):
        del st.session_state['image_analysis']
        st.rerun()

if not current_project_id:
    st.markdown('<div class="main-header"><h1>🦉 Athenalink OS v3.0</h1><p>Welcome. Select a project.</p></div>', unsafe_allow_html=True); st.stop()

conn = sqlite3.connect(DB_PATH); p_data = pd.read_sql("SELECT * FROM projects WHERE project_id = ?", conn, params=(current_project_id,)).iloc[0]; conn.close()
st.markdown(f"""<div class="main-header"><h1>🦉 Athenalink OS v3.0</h1><p>Project: <b>{p_data['name']}</b> | Goal: {p_data['goal']}</p></div>""", unsafe_allow_html=True)

STYLE = "【スタイルガイド】\n1. 言語: 日本語。\n2. 禁止: 自分語り、ポエム、説教。\n3. 構成: 受容(肯定)→分析(脳科学)→処方(解決策)。\n4. 態度: 冷静で温かいプロフェッショナル。"
prompts = {
    "M4": f"あなたは戦略参謀です。{STYLE} 目標達成のタスクを8-15個提案して。",
    "M1": f"あなたはSNS担当です。{STYLE} 読者の心を代弁するポストを3案作成して。",
    "M2": f"あなたは編集者です。{STYLE} 納得感のある記事構成(見出し5-10個)を作成して。",
    "M3": f"あなたは解決型セールスライターです。{STYLE} PASONA(Problem/Affinity/Solution/Action)で長文レターを書いて。"
}

def render_chat(role, base_prompt):
    if not client: st.warning("API Key Required"); return
    full_prompt = f"{base_prompt}\n{adaptive_prompt}\n{image_analysis_result}"
    key = f"chat_{current_project_id}_{role}"
    if key not in st.session_state: st.session_state[key] = [{"role": "system", "content": full_prompt}, {"role": "assistant", "content": "準備完了。"}]
    st.session_state[key][0]["content"] = full_prompt

    for i, msg in enumerate(st.session_state[key]):
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                # フィードバックボタン (アシスタントの回答のみ)
                if msg["role"] == "assistant" and i > 0:
                    c1, c2 = st.columns([1, 10])
                    with c1:
                        if st.button("👍", key=f"fb_up_{key}_{i}"): save_feedback(current_project_id, role, msg["content"], "good")
                    with c2:
                        if st.button("👎", key=f"fb_down_{key}_{i}"): save_feedback(current_project_id, role, msg["content"], "bad")

    st.markdown("---")
    with st.form(key=f"form_{role}", clear_on_submit=True):
        user_input = st.text_area("指示を入力...", height=150)
        send = st.form_submit_button("🚀 送信する")
    
    if send and user_input:
        st.session_state[key].append({"role": "user", "content": user_input})
        try:
            with st.spinner("Owl v3.0 is thinking..."):
                msgs = st.session_state[key].copy()
                msgs[-1]["content"] += " (設定と画像データを考慮し、日本語で)"
                res = client.chat.completions.create(model="gpt-3.5-turbo", messages=msgs, temperature=0.7, max_tokens=3000)
            st.session_state[key].append({"role": "assistant", "content": res.choices[0].message.content})
            st.rerun()
        except Exception as e: st.error(f"Error: {e}")

# --- コンテンツ表示 ---
if menu == "🏠 HOME":
    st.subheader("📊 ダッシュボード"); d = get_tasks(current_project_id)
    if not d.empty: st.dataframe(d, use_container_width=True)
    else: st.info("タスクなし")
elif menu == "✅ TASKS":
    st.subheader("✅ タスク管理")
    with st.form("add_t", clear_on_submit=True):
        c1, c2 = st.columns([3, 1]); t = c1.text_input("タスク名"); p = c2.selectbox("優先度", ["High", "Middle"])
        if st.form_submit_button("追加"): add_task(current_project_id, t, p); st.rerun()
    d = get_tasks(current_project_id);
    if not d.empty: st.data_editor(d, key="deditor", use_container_width=True)
        with st.expander("🗑 削除"):
            did = st.number_input("ID", step=1)
            if st.button("実行"): delete_task(did); st.rerun()
elif menu == "🧠 M4 戦略": render_chat("M4", prompts["M4"])
elif menu == "📱 M1 SNS":
    render_chat("M1", prompts["M1"])
    # 画像生成機能 (M1限定)
    st.markdown("### 🎨 クリエイティブ生成")
    if st.button("最新の投稿案から画像を生成する (DALL-E 3)"):
        key = f"chat_{current_project_id}_M1"
        if key in st.session_state and len(st.session_state[key]) > 2:
            last_assistant_msg = st.session_state[key][-1]["content"]
            with st.spinner("Generating image..."):
                try:
                    img_url = generate_image(client, last_assistant_msg)
                    st.image(img_url, caption="Generated by DALL-E 3")
                    st.success("画像生成完了！")
                except Exception as e:
                    st.error(f"画像生成エラー: {e}")
        else:
            st.warning("先にテキストを生成してください。")

elif menu == "📝 M2 記事": render_chat("M2", prompts["M2"])
elif menu == "💰 M3 販売": render_chat("M3", prompts["M3"])
