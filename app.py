import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI

# --- 1. 設定 & デザイン注入 ---
st.set_page_config(page_title="Owl v2.5", page_icon="🦉", layout="wide")

# カスタムCSS（見た目をカッコよくする魔法）
st.markdown("""
<style>
    /* 全体のフォントをモダンに */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Noto Sans JP', sans-serif;
    }
    
    /* ヘッダーの装飾 */
    .main-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        color: white !important;
        margin: 0;
        font-size: 2rem;
    }
    .main-header p {
        color: #e0e7ff;
        margin: 0;
        font-size: 0.9rem;
    }

    /* ボタンのデザイン */
    div.stButton > button {
        background: linear-gradient(to right, #f59e0b, #d97706);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
    }

    /* チャット入力欄の強調 */
    .stTextArea textarea {
        background-color: #1e1e1e;
        color: #ffffff;
        border: 1px solid #4b5563;
        border-radius: 10px;
    }
    .stTextArea textarea:focus {
        border-color: #f59e0b;
        box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.2);
    }
    
    /* サイドバーを少しシックに */
    [data-testid="stSidebar"] {
        background-color: #111827;
    }
</style>
""", unsafe_allow_html=True)

DB_PATH = "owl.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS projects ("
        "project_id TEXT PRIMARY KEY, name TEXT, domain TEXT, goal TEXT, "
        "status TEXT DEFAULT 'active', created_at DATETIME)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS tasks ("
        "task_id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, title TEXT, "
        "status TEXT DEFAULT 'TODO', priority TEXT DEFAULT 'Middle', created_at DATETIME)"
    )
    conn.commit()
    conn.close()

init_db()

# --- 2. データ関数 ---
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
    except:
        st.error("エラー: ID重複")
    finally:
        conn.close()

def get_tasks(pid):
    conn = sqlite3.connect(DB_PATH)
    q = f"SELECT * FROM tasks WHERE project_id = '{pid}' ORDER BY status DESC, priority DESC"
    df = pd.read_sql(q, conn)
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

# --- 3. UIロジック ---

# サイドバー設定
st.sidebar.header("🔑 System")
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
    st.sidebar.success("✅ Auto-Login")
else:
    api_key = st.sidebar.text_input("API Key", type="password")

st.sidebar.header("📂 プロジェクト")
df_projects = get_projects()
current_project_id = None
if not df_projects.empty:
    opts = {row['project_id']: row['name'] for i, row in df_projects.iterrows()}
    current_project_id = st.sidebar.selectbox("選択", options=list(opts.keys()), format_func=lambda x: opts[x])

with st.sidebar.expander("➕ 新規作成"):
    with st.form("new_proj"):
        new_id = st.text_input("ID")
        new_name = st.text_input("名前")
        new_dom = st.selectbox("分野", ["love_content", "owl_dev", "marketing"])
        new_goal = st.text_area("目標")
        if st.form_submit_button("作成"):
            if new_id:
                create_project(new_id, new_name, new_dom, new_goal)
                st.rerun()

st.sidebar.header("🚀 メニュー")
menu = st.sidebar.radio("Go", ["🏠 HOME", "✅ TASKS", "🧠 M4 戦略", "📱 M1 SNS", "📝 M2 記事", "💰 M3 販売"])

# アダプティブ設定
TARGET_MEDIA = {
    "X (Twitter)": {"len": "140字以内", "tone": "共感・発見", "style": "短文"},
    "X (長文)": {"len": "500-1000字", "tone": "ストーリー", "style": "没入感"},
    "note (記事)": {"len": "2000-4000字", "tone": "解説", "style": "見出し構成"},
    "note (販売LP)": {"len": "5000字以上", "tone": "解決・情熱", "style": "PASONA完全版"},
    "DM/LINE": {"len": "300字", "tone": "私信", "style": "語りかけ"}
}
DEPTH_LEVELS = {
    "Light": "広く浅く、拡散狙い",
    "Standard": "理由を含めた信頼構築",
    "Deep": "深層心理と根本解決(ファン化)"
}

adaptive_prompt = ""
if menu in ["📱 M1 SNS", "📝 M2 記事", "💰 M3 販売"]:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎛 生成設定")
    sel_media = st.sidebar.selectbox("媒体", list(TARGET_MEDIA.keys()))
    sel_depth = st.sidebar.selectbox("深さ", list(DEPTH_LEVELS.keys()))
    m_info = TARGET_MEDIA[sel_media]
    adaptive_prompt = (
        f"【出力設定】媒体:{sel_media}(目安{m_info['len']}), トーン:{m_info['tone']}, "
        f"スタイル:{m_info['style']}, 深さ:{sel_depth}({DEPTH_LEVELS[sel_depth]})"
    )

if not current_project_id:
    st.markdown('<div class="main-header"><h1>🦉 Athenalink OS</h1><p>Welcome, Ren. Select a project to start.</p></div>', unsafe_allow_html=True)
    st.stop()

# プロジェクト情報取得
conn = sqlite3.connect(DB_PATH)
p_data = pd.read_sql("SELECT * FROM projects WHERE project_id = ?", conn, params=(current_project_id,)).iloc[0]
conn.close()

# メインヘッダー表示
st.markdown(f"""
<div class="main-header">
    <h1>🦉 Athenalink OS v2.5</h1>
    <p>Project: <b>{p_data['name']}</b> | Goal: {p_data['goal']}</p>
</div>
""", unsafe_allow_html=True)

# AIロジック
STYLE = (
    "【スタイルガイド】\n1. 言語: 日本語。\n2. 禁止: 自分語り、ポエム、説教。\n"
    "3. 構成: 受容(肯定)→分析(脳科学)→処方(解決策)。\n4. 態度: 冷静で温かいプロフェッショナル。"
)
prompts = {
    "M4": f"あなたは戦略参謀です。{STYLE} 目標達成のタスクを8-15個提案して。",
    "M1": f"あなたはSNS担当です。{STYLE} 読者の心を代弁するポストを3案作成して。",
    "M2": f"あなたは編集者です。{STYLE} 納得感のある記事構成(見出し5-10個)を作成して。",
    "M3": f"あなたは解決型セールスライターです。{STYLE} PASONA(Problem/Affinity/Solution/Action)で長文レターを書いて。"
}

client = OpenAI(api_key=api_key) if api_key else None

def render_chat(role, base_prompt):
    if not client:
        st.warning("Please enter API Key")
        return
    full_prompt = f"{base_prompt}\n{adaptive_prompt}"
    key = f"chat_{current_project_id}_{role}"
    
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": full_prompt}]
        st.session_state[key].append({"role": "assistant", "content": "準備完了。指示をください。"})
    
    # 設定更新
    st.session_state[key][0]["content"] = full_prompt

    for msg in st.session_state[key]:
        if msg["role"] != "system":
            st.chat_message(msg["role"]).write(msg["content"])
    
    st.markdown("---")
    with st.form(key=f"form_{role}", clear_on_submit=True):
        user_input = st.text_area("指示を入力...", height=150)
        send = st.form_submit_button("🚀 送信する")
    
    if send and user_input:
        st.session_state[key].append({"role": "user", "content": user_input})
        try:
            with st.spinner("Owl is thinking..."):
                msgs = st.session_state[key].copy()
                msgs[-1]["content"] += " (設定された媒体・深さ・スタイルを厳守し日本語で)"
                res = client.chat.completions.create(
                    model="gpt-3.5-turbo", messages=msgs, temperature=0.7, max_tokens=3000
                )
            st.session_state[key].append({"role": "assistant", "content": res.choices[0].message.content})
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- コンテンツ表示 ---
if menu == "🏠 HOME":
    st.subheader("📊 ダッシュボード")
    d = get_tasks(current_project_id)
    if not d.empty:
        st.dataframe(d, use_container_width=True)
    else:
        st.info("タスクがまだありません")

elif menu == "✅ TASKS":
    st.subheader("✅ タスク管理")
    with st.form("add_t", clear_on_submit=True):
        c1, c2 = st.columns([3, 1])
        t = c1.text_input("タスク名")
        p = c2.selectbox("優先度", ["High", "Middle"])
        if st.form_submit_button("追加"):
            add_task(current_project_id, t, p)
            st.rerun()
    d = get_tasks(current_project_id)
    if not d.empty:
        st.data_editor(d, key="deditor", use_container_width=True)
        with st.expander("🗑 削除ツール"):
            did = st.number_input("ID", step=1)
            if st.button("削除実行"):
                delete_task(did)
                st.rerun()

elif menu == "🧠 M4 戦略":
    render_chat("M4", prompts["M4"])
elif menu == "📱 M1 SNS":
    render_chat("M1", prompts["M1"])
elif menu == "📝 M2 記事":
    render_chat("M2", prompts["M2"])
elif menu == "💰 M3 販売":
    render_chat("M3", prompts["M3"])
