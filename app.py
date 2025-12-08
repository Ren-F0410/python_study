import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI

# --- 1. アプリ設定 & DB初期化 ---
st.set_page_config(page_title="Owl v2.0", page_icon="🦉", layout="wide")

DB_PATH = "owl.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
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
        c.execute("INSERT INTO projects (project_id, name, domain, goal, created_at) VALUES (?, ?, ?, ?, ?)",
                  (p_id, name, domain, goal, datetime.now()))
        conn.commit()
        st.success(f"✅ プロジェクト『{name}』を作成しました！")
    except sqlite3.IntegrityError:
        st.error("⚠️ そのIDは既に使用されています。")
    except Exception as e:
        st.error(f"エラー: {e}")
    finally:
        conn.close()

def get_tasks(project_id):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(f"SELECT * FROM tasks WHERE project_id = '{project_id}' ORDER BY CASE status WHEN 'DOING' THEN 1 WHEN 'TODO' THEN 2 ELSE 3 END, priority DESC, created_at DESC", conn)
    conn.close()
    return df

def add_task(project_id, title, priority):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO tasks (project_id, title, status, priority, created_at) VALUES (?, ?, 'TODO', ?, ?)",
              (project_id, title, priority, datetime.now()))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
    conn.commit()
    conn.close()

# --- 3. UI構築 ---

st.title("🦉 Athenalink OS v2.0")
st.caption("Final Tuned: Client-First Professional Counselor")

# サイドバー：APIキー
st.sidebar.header("🔑 System Access")
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
    st.sidebar.success("✅ Auto-Login Active")
else:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")

st.sidebar.header("📂 Project Selector")
df_projects = get_projects()

if df_projects.empty:
    st.sidebar.warning("プロジェクトを作成してください")
    current_project_id = None
else:
    project_options = {row['project_id']: f"{row['name']}" for index, row in df_projects.iterrows()}
    current_project_id = st.sidebar.selectbox(
        "現在のプロジェクト",
        options=list(project_options.keys()),
        format_func=lambda x: project_options[x]
    )

with st.sidebar.expander("➕ 新規プロジェクト作成"):
    with st.form("create_project_form"):
        new_id = st.text_input("ID", placeholder="love_note_01")
        new_name = st.text_input("プロジェクト名")
        new_domain = st.selectbox("事業ドメイン", ["love_content", "owl_dev", "marketing", "other"])
        new_goal = st.text_area("目標")
        submitted = st.form_submit_button("作成")
        if submitted and new_id and new_name:
            create_project(new_id, new_name, new_domain, new_goal)
            st.rerun()

st.sidebar.header("🚀 Modules")
menu = st.sidebar.radio("Menu", [
    "🏠 ダッシュボード",
    "✅ タスク管理 (ToDo)",
    "🧠 M4 参謀本部",
    "📱 M1 SNS集客",
    "📝 M2 記事制作",
    "💰 M3 セールス"
])

# --- 4. 脳みそのチューニング (v2.0 Final Update) ---

STYLE_GUIDE = """
【Athenalink Style Guide (Renイズム v2.0: Pure Counselor)】
■ 鉄の掟（禁止事項）
1. **自分語りの完全禁止**: 「私もそうでした」「私の経験では」は一切書かない。主語は常に「あなた」にする。
2. **ポエムの禁止**: 抽象的な比喩は使わない。
3. **説教の禁止**: 上から目線で断じない。

■ スタンス
- **「静かなる受容」**: 読者のネガティブな感情を「それは当然の反応です」と医学的・心理学的に肯定する。
- **「的確な処方」**: 共感で終わらせず、「なぜそうなるか（原因）」と「どうすればいいか（解決）」を淡々と、しかし温かく提示する。
- **距離感**: 親友ではなく、信頼できる医師や専門家の距離感。
"""

def get_m4_prompt(p_name, p_goal, p_domain):
    return f"""
    あなたはプロジェクト『{p_name}』の戦略パートナーです。
    {STYLE_GUIDE}
    【ミッション】
    目標「{p_goal}」を達成するための具体的タスクを8〜15個提示してください。
    """

def get_m1_prompt(p_name, p_goal):
    return f"""
    あなたは『{p_name}』のSNS運用担当です。
    {STYLE_GUIDE}
    【役割】
    読者が「私のことを見透かされている」とドキッとするポストを作成してください。
    【出力要件】
    - 3案作成（各120〜140文字）。
    - 自分の話はせず、読者の心の中にある言葉を代弁すること。
    """

def get_m2_prompt(p_name, p_goal):
    return f"""
    あなたは『{p_name}』の編集担当です。
    {STYLE_GUIDE}
    【役割】
    読者が「自分の取り扱い説明書」を読んでいるかのような納得感のある記事構成・執筆を行います。
    """

def get_m3_prompt(p_name, p_goal):
    return f"""
    あなたは「問題解決のプロフェッショナル」であるカウンセラー（セールスライター）です。
    {STYLE_GUIDE}
    
    【重要ミッション】
    読み手が「この人は私の悩みを私以上に理解している。そして解決策を持っている」と確信できる、2000文字級のレターを書いてください。
    
    【構成 (Client-First PASONA)】
    1. **Problem (現状の受容)**: 読者の苦しみを詳細に言語化する。「〜で辛いですよね」ではなく「〜という状態になり、息苦しさを感じていませんか？」と診断するように書く。
    2. **Affinity (肯定と分析)**: **自分語りは厳禁。** 代わりに「それはあなたの弱さではなく、脳の『現状維持バイアス』という機能が働いているだけです」と、悩みを客観的な現象として説明し、安心させる。
    3. **Solution (処方箋)**: 「このnoteには、その脳の誤作動を解除する具体的なメソッドが書かれています」と解決策を提示。
    4. **Action (未来への導き)**: 「治すなら今です。新しい自分になる準備はできていますか？」と、静かに背中を押す。
    """

# --- 5. メイン処理 ---
if not current_project_id:
    st.stop()

conn = sqlite3.connect(DB_PATH)
project_data = pd.read_sql("SELECT * FROM projects WHERE project_id = ?", conn, params=(current_project_id,)).iloc[0]
conn.close()

p_name = project_data['name']
p_goal = project_data['goal']
p_domain = project_data['domain']

client = None
if api_key:
    client = OpenAI(api_key=api_key)

# 共通チャット機能
def render_chat(module_name, system_prompt):
    if not client:
        st.warning("👈 APIキーを入力してください")
        return

    session_key = f"chat_{current_project_id}_{module_name}"
    
    if session_key not in st.session_state:
        st.session_state[session_key] = [{"role": "system", "content": system_prompt}]
        greeting = "起動しました。"
        if module_name == "M3": greeting = f"セールスライター（v2.0: Pure Counselor）起動。あなた（クライアント）のための手紙を書きます。"
        st.session_state[session_key].append({"role": "assistant", "content": greeting})

    for msg in st.session_state[session_key]:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    st.markdown("---")
    with st.form(key=f"input_form_{module_name}", clear_on_submit=True):
        user_input = st.text_area("指示を入力 (Enterで改行、送信ボタンで実行)", height=150)
        submit_button = st.form_submit_button("送信する")

    if submit_button and user_input:
        st.session_state[session_key].append({"role": "user", "content": user_input})
        
        # 思考プロセス（自分語り・ポエム完全排除）
        thinking_instruction = """
        【思考プロセス：最終チェック】
        1. 「私（書き手）」の話をしていないか？あれば削除し、「あなた（読者）」の話に書き換える。
        2. 感情的なポエムになっていないか？「なぜそうなるか」の理由（脳科学・心理学）を含める。
        3. 2000文字級の長文で、読者が「救われた」と感じる構成にする。
        """
        
        messages_for_api = st.session_state[session_key].copy()
        messages_for_api[-1]["content"] += thinking_instruction

        try:
            with st.spinner("Owl v2.0 is crafting the solution..."):
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages_for_api,
                    temperature=0.7,
                    max_tokens=3000
                )
            ai_text = response.choices[0].message.content
            st.session_state[session_key].append({"role": "assistant", "content": ai_text})
            st.rerun()
        except Exception as e:
            st.error(f"エラー: {e}")

# --- 各画面 ---
if menu == "🏠 ダッシュボード":
    st.header(f"Project: {p_name}")
    st.info(f"**GOAL:** {p_goal}")
    st.subheader("🔥 今日のタスク")
    df_tasks = get_tasks(current_project_id)
    if not
