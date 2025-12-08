import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI

# --- 1. アプリ設定 & DB初期化 ---
st.set_page_config(page_title="Owl v1.9", page_icon="🦉", layout="wide")

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

st.title("🦉 Athenalink OS v1.9")
st.caption("Professional Counselor Mode: No Anecdotes, Pure Solution")

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

# --- 4. 脳みそのチューニング (v1.9 Professional Counselor Update) ---

STYLE_GUIDE = """
【Athenalink Style Guide (Renイズム v5: Professional Counselor)】
■ ペルソナ（書き手の人格）
- **「クライアントの痛みを深く理解する、プロの女性心理カウンセラー」**。
- 自分語り（「私もそうでした」）は禁止。主役はあくまで「あなた（読者）」であること。
- 感情的になりすぎず、しかし冷たくならず、包み込むような落ち着いたトーンで話す。

■ ターゲットへの態度
- 全肯定。「あなたが悪いわけではない」と心理学的根拠をもって伝える。
- 読者の混乱を整理し、「今何が起きているか」を言語化してあげる役割。

■ 表現のルール
- 「辛いよね」という共感の後に、必ず「それは〇〇という心の防衛反応なんだよ」と理屈を添える。
- 具体的な解決策（ソリューション）を提示する際は、自信を持って言い切る。
"""

def get_m4_prompt(p_name, p_goal, p_domain):
    return f"""
    あなたはプロジェクト『{p_name}』の戦略パートナーです。
    {STYLE_GUIDE}
    【ミッション】
    目標「{p_goal}」を達成するための具体的タスクを提示してください。
    【出力ルール】
    - タスクは8〜15個。
    - ビジネスとして冷静な判断をしつつ、Ren様に寄り添った口調で提案してください。
    """

def get_m1_prompt(p_name, p_goal):
    return f"""
    あなたは『{p_name}』のSNS運用担当です。
    {STYLE_GUIDE}
    【役割】
    TLに流れてきた時、読者が「私の心を代弁してくれている」と感じ、救いを求めるポストを作成してください。
    【出力要件】
    - 3案作成（各120〜140文字）。
    - 自分の体験談ではなく、「あなたの心の中」を透視したような言葉を選ぶこと。
    """

def get_m2_prompt(p_name, p_goal):
    return f"""
    あなたは『{p_name}』の編集担当です。
    {STYLE_GUIDE}
    【役割】
    読者が「自分の取り扱い説明書」を読んでいるかのような納得感のある記事構成・執筆を行います。
    【構成案のルール】
    - 見出し5〜10個。
    - 感情のアップダウンだけでなく、「理解→納得→行動」のロジックを通す。
    """

def get_m3_prompt(p_name, p_goal):
    return f"""
    あなたは「解決策を提示する」プロのカウンセラー（セールスライター）です。
    {STYLE_GUIDE}
    
    【重要ミッション】
    読み手が「この人は私の悩みの正体を知っている。そして治し方も知っている」と確信できる、2000文字級のレターを書いてください。
    
    【禁止事項】
    - 「私も昔は...」という自分語り（Anecdote）。
    - 詩的なだけの表現。
    
    【構成 (Professional PASONA)】
    1. **Problem (現状の受容)**: 読者の苦しみを詳細に描写する。「今、胸が苦しいですよね。それは当然のことです」と全肯定する。
    2. **Affinity (専門的共感)**: 自分語りではなく、「多くの女性が同じ沼に陥ります。なぜなら脳には〇〇という性質があるからです」と、悩みを客観化・一般化して安心させる。
    3. **Solution (解決の提示)**: 感情論ではなく、メソッドとしての解決策を提示する。「このnoteには、その脳のクセを解除する具体的な手順が書かれています」。
    4. **Action (未来への導き)**: 「一緒に治していきましょう」と、医師が患者に手を差し伸べるような信頼感のあるクロージング。
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

# 共通チャット機能（送信後クリア & プロカウンセラーモード）
def render_chat(module_name, system_prompt):
    if not client:
        st.warning("👈 APIキーを入力してください")
        return

    session_key = f"chat_{current_project_id}_{module_name}"
    
    if session_key not in st.session_state:
        st.session_state[session_key] = [{"role": "system", "content": system_prompt}]
        greeting = "起動しました。"
        if module_name == "M3": greeting = f"セールスライター（v1.9: Professional Counselor）起動。自分語りをせず、解決策へ導くレターを書きます。"
        st.session_state[session_key].append({"role": "assistant", "content": greeting})

    for msg in st.session_state[session_key]:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    st.markdown("---")
    with st.form(key=f"input_form_{module_name}", clear_on_submit=True):
        user_input = st.text_area("指示を入力 (Enterで
