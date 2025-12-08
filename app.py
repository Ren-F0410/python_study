import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI

# --- 1. アプリ設定 & データベース初期化 ---
st.set_page_config(page_title="Owl v1.3", page_icon="🦉", layout="wide")

DB_PATH = "owl.db"

def init_db():
    """データベースとテーブルの初期化"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # プロジェクト管理用テーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            project_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            domain TEXT,
            goal TEXT,
            status TEXT DEFAULT 'active',
            created_at DATETIME
        )
    ''')
    
    # タスク管理用テーブル（Phase 2で本格使用）
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            title TEXT,
            status TEXT DEFAULT 'TODO',
            priority TEXT DEFAULT 'Middle',
            created_at DATETIME
        )
    ''')
    
    conn.commit()
    conn.close()

# アプリ起動時にDBをチェック
init_db()

# --- 2. 関数群 ---

def get_projects():
    """全プロジェクトを取得"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM projects", conn)
    conn.close()
    return df

def create_project(p_id, name, domain, goal):
    """新規プロジェクト作成"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO projects (project_id, name, domain, goal, created_at) VALUES (?, ?, ?, ?, ?)",
                  (p_id, name, domain, goal, datetime.now()))
        conn.commit()
        st.success(f"✅ プロジェクト『{name}』を作成しました！")
    except sqlite3.IntegrityError:
        st.error("⚠️ そのIDは既に使用されています。別のIDにしてください。")
    except Exception as e:
        st.error(f"エラー: {e}")
    finally:
        conn.close()

# --- 3. UI構築 ---

st.title("🦉 Athenalink OS v1.3")

# サイドバー：APIキー
st.sidebar.header("🔑 System Access")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")

# サイドバー：プロジェクト選択
st.sidebar.header("📂 Project Selector")

# プロジェクト一覧の取得
df_projects = get_projects()

if df_projects.empty:
    st.sidebar.warning("まだプロジェクトがありません。")
    current_project_id = None
else:
    # セレクトボックス用に辞書作成 {ID: 名前}
    project_options = {row['project_id']: f"{row['name']} ({row['project_id']})" for index, row in df_projects.iterrows()}
    current_project_id = st.sidebar.selectbox(
        "現在のプロジェクト",
        options=list(project_options.keys()),
        format_func=lambda x: project_options[x]
    )

# サイドバー：新規作成フォーム
with st.sidebar.expander("➕ 新規プロジェクト作成"):
    with st.form("create_project_form"):
        new_id = st.text_input("ID (例: love_note_01)", placeholder="英数字推奨")
        new_name = st.text_input("プロジェクト名", placeholder="恋愛note第1弾")
        new_domain = st.selectbox("事業ドメイン", ["love_content", "owl_dev", "marketing", "other"])
        new_goal = st.text_area("目標・メモ")
        submitted = st.form_submit_button("作成")
        if submitted and new_id and new_name:
            create_project(new_id, new_name, new_domain, new_goal)
            st.rerun() # 画面更新

# サイドバー：機能メニュー
st.sidebar.header("🚀 Modules")
menu = st.sidebar.radio("Menu", [
    "🏠 ダッシュボード",
    "✅ タスク管理 (ToDo)",
    "🧠 M4 参謀本部",
    "📱 M1 SNS集客",
    "📝 M2 記事制作",
    "💰 M3 セールス"
])

# --- 4. メイン画面の表示 ---

if not current_project_id:
    st.info("👈 左のサイドバーから「新規プロジェクト」を作成してください。")
    st.stop()

# 現在のプロジェクト情報を取得
conn = sqlite3.connect(DB_PATH)
current_project = pd.read_sql("SELECT * FROM projects WHERE project_id = ?", conn, params=(current_project_id,)).iloc[0]
conn.close()

# === 🏠 ダッシュボード ===
if menu == "🏠 ダッシュボード":
    st.header(f"Project: {current_project['name']}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📌 Basic Info")
        st.write(f"**ID:** `{current_project['project_id']}`")
        st.write(f"**Domain:** `{current_project['domain']}`")
        st.write(f"**Status:** {current_project['status']}")
    
    with col2:
        st.subheader("🎯 Goal / Memo")
        st.info(current_project['goal'])

    st.markdown("---")
    st.write("ここに「今日のタスク」や「直近の成果物」が表示されます（Phase 2で実装予定）。")

# === ✅ タスク管理 ===
elif menu == "✅ タスク管理 (ToDo)":
    st.header(f"Tasks for {current_project['name']}")
    st.info("🚧 工事中：Phase 2でここにタスク管理機能が入ります。")

# === 🧠 M4 参謀本部 ===
elif menu == "🧠 M4 参謀本部":
    st.header("参謀本部 (Strategy)")
    st.write(f"現在、プロジェクト **『{current_project['name']}』** の戦略を立案中です。")
    st.info("🚧 工事中：これまでのチャット機能は次のステップでここに統合されます。")

# === その他のモジュール ===
else:
    st.header(menu)
    st.write(f"Project: {current_project['name']}")
    st.info("🚧 システム移行中... まもなく機能が開放されます。")
