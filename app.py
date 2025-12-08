import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI

# --- 1. 設定 ---
st.set_page_config(page_title="Owl v2.0", page_icon="🦉", layout="wide")
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

# --- 2. データ操作関数 ---
def get_projects():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM projects", conn)
    conn.close()
    return df

def create_project(p_id, name, domain, goal):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?)",
            (p_id, name, domain, goal, 'active', datetime.now())
        )
        conn.commit()
        st.success(f"プロジェクト『{name}』を作成しました")
    except:
        st.error("エラー: IDが重複しています")
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
    c.execute(
        "INSERT INTO tasks (project_id, title, status, priority, created_at) "
        "VALUES (?, ?, 'TODO', ?, ?)",
        (pid, title, prio, datetime.now())
    )
    conn.commit()
    conn.close()

def delete_task(tid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE task_id = ?", (tid,))
    conn.commit()
    conn.close()

# --- 3. UI設計 ---
st.title("🦉 Athenalink OS v2.0")
st.caption("Strategic Editor AI: Adaptive Engine & Multi-Modal Ready")

st.sidebar.header("🔑 システムアクセス")
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
    st.sidebar.success("✅ 自動ログイン中")
else:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")

st.sidebar.header("📂 プロジェクト選択")
df_projects = get_projects()

if df_projects.empty:
    st.sidebar.warning("プロジェクトを作成してください")
    current_project_id = None
else:
    opts = {row['project_id']: row['name'] for i, row in df_projects.iterrows()}
    current_project_id = st.sidebar.selectbox(
        "現在のプロジェクト", 
        options=list(opts.keys()), 
        format_func=lambda x: opts[x]
    )

with st.sidebar.expander("➕ 新規プロジェクト作成"):
    with st.form("new_proj"):
        new_id = st.text_input("ID (例: love01)")
        new_name = st.text_input("プロジェクト名")
        new_domain = st.selectbox("事業ドメイン", ["love_content", "owl_dev", "marketing"])
        new_goal = st.text_area("目標")
        if st.form_submit_button("作成") and new_id:
            create_project(new_id, new_name, new_domain, new_goal)
            st.rerun()

st.sidebar.header("🚀 機能メニュー")
menu = st.sidebar.radio(
    "モード選択", 
    ["🏠 ダッシュボード", "✅ タスク管理", "🧠 M4 参謀本部", "📱 M1 SNS集客", "📝 M2 記事制作", "💰 M3 セールス"]
)

# --- 4. アダプティブ文章エンジン (v2.0 Core) ---

# 設定値の定義
TARGET_MEDIA = {
    "X (Twitter)": {"len": "140文字以内", "tone": "共感・発見", "style": "短文・改行多め"},
    "X (長文ポスト)": {"len": "500〜1000文字", "tone": "ストーリーテリング", "style": "没入感のある物語"},
    "note (記事)": {"len": "2000〜4000文字", "tone": "専門家・解説", "style": "見出し付き構成"},
    "note (販売LP)": {"len": "5000文字以上", "tone": "情熱・解決策提示", "style": "PASONA完全版"},
    "DM/LINE": {"len": "200〜400文字", "tone": "親密・私信", "style": "語りかけ"}
}

DEPTH_LEVELS = {
    "Light (拡散狙い)": "広く浅く、誰にでも刺さる言葉で。",
    "Standard (教育・信頼)": "なぜそうなるのか？という理由を含める。",
    "Deep (成約・ファン化)": "深層心理まで掘り下げ、痛みを共有し、根本解決を示す。"
}

# サイドバーに生成設定を表示（チャット系モードの時のみ）
adaptive_prompt = ""
if menu in ["📱 M1 SNS集客", "📝 M2 記事制作", "💰 M3 セールス"]:
    st.sidebar.markdown("---")
    st.sidebar.header("🎛 生成設定 (Adaptive)")
    
    sel_media = st.sidebar.selectbox("📡 媒体・フォーマット", list(TARGET_MEDIA.keys()))
    sel_depth = st.sidebar.selectbox("🌊 深さ・目的", list(DEPTH_LEVELS.keys()))
    
    # 動的プロンプトの生成
    media_info = TARGET_MEDIA[sel_media]
    adaptive_prompt = (
        f"【出力設定】\n"
        f"・媒体: {sel_media} (目安: {media_info['len']})\n"
        f"・トーン: {media_info['tone']}\n"
        f"・スタイル: {media_info['style']}\n"
        f"・深さレベル: {sel_depth} ({DEPTH_LEVELS[sel_depth]})\n"
        "※ 上記の設定に厳密に従い、文字数や構成を最適化してください。\n"
    )

# 基本スタイル（Renイズム v2.0ベース）
BASE_STYLE = (
    "【基本スタイルガイド】\n"
    "1. 言語: 日本語 (English Forbidden)\n"
    "2. 禁止: 自分語り(私は〜)、ポエム、説教。\n"
    "3. スタンス: 受容(肯定) → 分析(脳科学/心理学) → 処方(解決策)。\n"
    "4. 態度: 冷静で温かいプロフェッショナル。\n"
)

if not current_project_id:
    st.stop()

conn = sqlite3.connect(DB_PATH)
p_data = pd.read_sql("SELECT * FROM projects WHERE project_id = ?", conn, params=(current_project_id,)).iloc[0]
conn.close()
p_info = f"プロジェクト: {p_data['name']}, 目標: {p_data['goal']}"

client = OpenAI(api_key=api_key) if api_key else None

def render_chat(role, base_instruction):
    if not client:
        st.warning("API Keyを入力してください")
        return
    
    # プロンプトを合体（基本指示 + プロジェクト情報 + アダプティブ設定）
    full_system_prompt = f"{base_instruction}\n{BASE_STYLE}\n{p_info}\n{adaptive_prompt}"
    
    key = f"chat_{current_project_id}_{role}"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": full_system_prompt}]
        st.session_state[key].append({"role": "assistant", "content": "起動しました。設定に合わせて生成します。"})
    
    # 設定が変わったらシステムプロンプトを更新するロジック（簡易版）
    # 常に最新の設定をsystemメッセージの末尾に追加する形で上書き効果を狙う
    st.session_state[key][0]["content"] = full_system_prompt

    for msg in st.session_state[key]:
        if msg["role"] != "system":
            st.chat_message(msg["role"]).write(msg["content"])
    
    st.markdown("---")
    with st.form(key=f"form_{role}", clear_on_submit=True):
        user_input = st.text_area("指示を入力...", height=150)
        send = st.form_submit_button("送信")
    
    if send and user_input:
        st.session_state[key].append({"role": "user", "content": user_input})
        try:
            with st.spinner("Owl v2.0 is optimizing..."):
                messages_to_send = st.session_state[key].copy()
                # 念押し指示
                messages_to_send[-1]["content"] += " (設定された媒体と深さに合わせて書いてください)"
                
                res = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages_to_send,
                    temperature=0.7,
                    max_tokens=3500 # 長文対応強化
                )
            st.session_state[key].append({"role": "assistant", "content": res.choices[0].message.content})
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- 5. 画面表示 ---
if menu == "🏠 ダッシュボード":
    st.header(f"Project: {p_data['name']}")
    st.info(p_data['goal'])
    st.subheader("🔥 今日のタスク")
    d = get_tasks(current_project_id)
    if not d.empty:
        st.dataframe(d)
    else:
        st.write("タスクなし")

elif menu == "✅ タスク管理":
    st.header("タスク管理")
    with st.form("add_t", clear_on_submit=True):
        t = st.text_input("タスク名")
        p = st.selectbox("優先度", ["High", "Middle"])
        if st.form_submit_button("追加"):
            add_task(current_project_id, t, p)
            st.rerun()
    d = get_tasks(current_project_id)
    if not d.empty:
        st.data_editor(d, key="deditor")
        with st.expander("削除"):
            did = st.number_input("ID", step=1)
            if st.button("削除"):
                delete_task(did)
                st.rerun()

elif menu == "🧠 M4 参謀本部":
    # 参謀はアダプティブ対象外（常に戦略モード）
    render_chat("M4", "あなたは戦略参謀です。目標達成のための具体的タスクを8〜15個提案してください。")

elif menu == "📱 M1 SNS集客":
    render_chat("M1", "あなたはSNS担当です。読者の心を代弁するポストを作成してください。")

elif menu == "📝 M2 記事制作":
    render_chat("M2", "あなたは編集者です。読者が納得する記事構成・本文を作成してください。")

elif menu == "💰 M3 セールス":
    render_chat("M3", "あなたは解決型セールスライターです。読者を救うための文章を書いてください。")
