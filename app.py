import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI

# --- 1. アプリ設定 & DB初期化 ---
st.set_page_config(page_title="Owl v1.7", page_icon="🦉", layout="wide")

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

st.title("🦉 Athenalink OS v1.7")
st.caption("Deep Empathy (Sisterhood) & Form Input Mode")

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

# --- 4. 脳みそのチューニング (v1.7 Sisterhood Update) ---

# 共通スタイルガイド（女性性・共感性の強化）
STYLE_GUIDE = """
【Athenalink Style Guide (Renイズム v3: Sisterhood)】
■ ペルソナ（書き手の人格）
- **「かつて同じ沼で苦しみ、自力で這い上がった女性の先輩」**。
- 男性的・騎士的な「守ってあげる」トーンは厳禁。
- ロマンチックな言葉（「君」「僕」「輝く未来」など）は使わない。
- 女子会で深夜に本音で語り合うような、リアルで少し痛いけれど温かい言葉を選ぶ。

■ ターゲットへの態度
- 上から目線のアドバイスではなく、「横に座って背中をさする」距離感。
- 「わかるよ、辛いよね」という共感だけでなく、「でもね、それじゃあ貴方が壊れちゃうよ」という愛のある警告も含める。

■ 表現のルール
- 比喩は「生活感」のあるものを使う（例：ハンマーではなく「鉛を飲み込んだような重さ」「冷え切った指先」）。
- 文末は「〜だよね」「〜なんだよ」「〜してみようか」など、柔らかく語りかける口調。
"""

# M4: 参謀プロンプト
def get_m4_prompt(p_name, p_goal, p_domain):
    return f"""
    あなたはプロジェクト『{p_name}』の戦略パートナーです。
    {STYLE_GUIDE}
    【ミッション】
    目標「{p_goal}」を達成するための具体的タスクを提示してください。
    【出力ルール】
    - タスクは8〜15個。
    - 感情論ではなく、ビジネスとして冷静な判断をしつつ、Ren様に寄り添った口調で提案してください。
    """

# M1: SNSプロンプト
def get_m1_prompt(p_name, p_goal):
    return f"""
    あなたは『{p_name}』のSNS運用担当（中の人）です。
    {STYLE_GUIDE}
    【役割】
    TLに流れてきたら思わず「これ私のことだ」と手が止まるポストを作成してください。
    【出力要件】
    - 3案作成（各120〜140文字）。
    - ターゲットの女性が「この人は私の痛みをわかってくれる」と感じる独り言のようなトーンで。
    - キラキラした言葉は不要。深夜のリアルな感情を言語化して。
    """

# M2: 記事制作プロンプト
def get_m2_prompt(p_name, p_goal):
    return f"""
    あなたは『{p_name}』の編集担当です。
    {STYLE_GUIDE}
    【役割】
    女性読者が没入できる記事構成・執筆を行います。
    【構成案のルール】
    - 見出し5〜10個。
    - 読み手が「そうそう、そうなの！」と頷きながら読み進められるストーリー構成。
    """

# M3: セールスプロンプト
def get_m3_prompt(p_name, p_goal):
    return f"""
    あなたは「女性の心に寄り添う」セールスライターです。
    {STYLE_GUIDE}
    
    【重要ミッション】
    読み手が涙を流しながら「やっとわかってくれる人に出会えた」と感じる、2000文字級のレターを書いてください。
    
    【禁止事項】
    - 男性が女性を口説くようなロマンチックな表現。
    - 「君」「僕」という一人称・二人称（「あなた」「私」を使うこと）。
    - 偉そうな説教。
    
    【構成】
    ProblemからActionまで、同じ傷を持つ女性同士の対話として書ききってください。
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

# 共通チャット機能（改行対応UIに変更）
def render_chat(module_name, system_prompt):
    if not client:
        st.warning("👈 APIキーを入力してください")
        return

    session_key = f"chat_{current_project_id}_{module_name}"
    
    if session_key not in st.session_state:
        st.session_state[session_key] = [{"role": "system", "content": system_prompt}]
        greeting = "起動しました。"
        if module_name == "M3": greeting = f"セールスライター（v1.7: Sisterhood Mode）起動。女性同士の共感レターを書きます。"
        st.session_state[session_key].append({"role": "assistant", "content": greeting})

    # チャット履歴の表示
    for msg in st.session_state[session_key]:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # --- 新しい入力フォーム (Enterで改行、ボタンで送信) ---
    st.markdown("---")
    with st.form(key=f"input_form_{module_name}"):
        user_input = st.text_area("指示を入力 (Enterで改行、Command+Enter または下のボタンで送信)", height=150)
        submit_button = st.form_submit_button("送信する")

    if submit_button and user_input:
        # ユーザーの入力を表示に追加
        st.session_state[session_key].append({"role": "user", "content": user_input})
        
        # 思考プロセス（女性目線での推敲）
        thinking_instruction = """
        【思考プロセス：女性視点チェック】
        1. ロマンチックすぎないか？男性目線になっていないか？を確認。
        2. 「同じ痛みを知る女性の先輩」として、リアルな生活感のある言葉を選ぶ。
        3. 指定文字数（長文）を満たす構成を組む。
        """
        
        messages_for_api = st.session_state[session_key].copy()
        messages_for_api[-1]["content"] += thinking_instruction

        try:
            with st.spinner("Owl v1.7 is writing (Sisterhood Mode)..."):
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages_for_api,
                    temperature=0.7,
                    max_tokens=3000
                )
            ai_text = response.choices[0].message.content
            # AIの返答を履歴に追加
            st.session_state[session_key].append({"role": "assistant", "content": ai_text})
            st.rerun() # 画面更新してチャットを表示
        except Exception as e:
            st.error(f"エラー: {e}")

# --- 各画面 ---
if menu == "🏠 ダッシュボード":
    st.header(f"Project: {p_name}")
    st.info(f"**GOAL:** {p_goal}")
    st.subheader("🔥 今日のタスク")
    df_tasks = get_tasks(current_project_id)
    if not df_tasks.empty:
        st.dataframe(df_tasks)
    else:
        st.write("タスクなし")

elif menu == "✅ タスク管理 (ToDo)":
    st.header("Task Management")
    with st.form("add_task_form"):
        t_title = st.text_input("タスク追加")
        t_prio = st.selectbox("優先度", ["High", "Middle", "Low"])
        if st.form_submit_button("追加"):
            add_task(current_project_id, t_title, t_prio)
            st.rerun()
    df_tasks = get_tasks(current_project_id)
    if not df_tasks.empty:
        st.data_editor(df_tasks, key="editor_v1_7")
        with st.expander("削除"):
            del_id = st.number_input("ID", step=1)
            if st.button("削除"):
                delete_task(del_id)
                st.rerun()

elif menu == "🧠 M4 参謀本部":
    st.header("Strategy Room (M4)")
    render_chat("M4", get_m4_prompt(p_name, p_goal, p_domain))

elif menu == "📱 M1 SNS集客":
    st.header("SNS Creator (M1)")
    render_chat("M1", get_m1_prompt(p_name, p_goal))

elif menu == "📝 M2 記事制作":
    st.header("Editor Room (M2)")
    render_chat("M2", get_m2_prompt(p_name, p_goal))

elif menu == "💰 M3 セールス":
    st.header("Sales Writer (M3)")
    render_chat("M3", get_m3_prompt(p_name, p_goal))
