import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI

# --- 1. アプリ設定 & DB初期化 ---
st.set_page_config(page_title="Owl v1.8", page_icon="🦉", layout="wide")

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

st.title("🦉 Athenalink OS v1.8")
st.caption("Counselor Mode: Analytical & Solution-Oriented")

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

# --- 4. 脳みそのチューニング (v1.8 Counselor Update) ---

STYLE_GUIDE = """
【Athenalink Style Guide (Renイズム v4: Counselor)】
■ ペルソナ（書き手の人格）
- **「冷静かつ温かい、解決志向の女性カウンセラー」**。
- 詩的な表現や過剰な比喩（「魂の叫び」「千切れるような痛み」など）は控える。
- 感情に寄り添いつつも、すぐに「なぜその感情が起きるのか（メカニズム）」と「どうすれば治るか（ソリューション）」へ話を展開する。
- 読者を「患者」扱いせず、「変わろうとしているクライアント」としてリスペクトする。

■ 文章のトーン
- 地に足のついた、具体的で実用的な言葉を選ぶ。
- 「辛いよね」で終わらせず、「辛いのは脳の誤作動だよ。修正できるよ」と希望を論理で示す。
- 読んだ後に「感動した」ではなく「やるべきことが分かった」と思わせる。
"""

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

def get_m1_prompt(p_name, p_goal):
    return f"""
    あなたは『{p_name}』のSNS運用担当です。
    {STYLE_GUIDE}
    【役割】
    TLに流れてきた時、読者が「私の悩みの答えがここにある」と感じる有益なポストを作成してください。
    【出力要件】
    - 3案作成（各120〜140文字）。
    - ただの共感ポエムにならないように注意。「共感」は入り口にし、「気付き（解決のヒント）」を必ず入れること。
    """

def get_m2_prompt(p_name, p_goal):
    return f"""
    あなたは『{p_name}』の編集担当です。
    {STYLE_GUIDE}
    【役割】
    読者が「なるほど、そうだったのか」と納得し、行動したくなる記事構成・執筆を行います。
    【構成案のルール】
    - 見出し5〜10個。
    - 感情的なストーリーだけでなく、論理的な解説（なぜ依存してしまうのか等）をしっかり組み込む。
    """

def get_m3_prompt(p_name, p_goal):
    return f"""
    あなたは「解決策を提示する」セールスライターです。
    {STYLE_GUIDE}
    
    【重要ミッション】
    読み手が「このnoteなら、今の苦しい状況を本当に変えられるかもしれない」と確信できる、2000文字級のレターを書いてください。
    
    【禁止事項】
    - 雰囲気だけの詩的な文章。
    - 「魔法のように変わる」といった根拠のない約束。
    
    【構成 (Counselor's PASONA)】
    1. **Problem**: 現状の辛さを描写するが、悲劇のヒロインにはさせない。「それはあなたのせいではなく、思考のクセです」と定義する。
    2. **Affinity**: 「私も同じ道を通り、メソッドを使って抜け出しました」と実証性を提示。
    3. **Solution**: このnoteが提供する具体的な解決メソッド（ワークや考え方）の一部をチラ見せする。
    4. **Action**: 感情的な煽りではなく、「今ここで決断すれば、明日の朝はこう変わる」と論理的なベネフィットで背中を押す。
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

# 共通チャット機能（送信後クリア & カウンセラーモード）
def render_chat(module_name, system_prompt):
    if not client:
        st.warning("👈 APIキーを入力してください")
        return

    session_key = f"chat_{current_project_id}_{module_name}"
    
    if session_key not in st.session_state:
        st.session_state[session_key] = [{"role": "system", "content": system_prompt}]
        greeting = "起動しました。"
        if module_name == "M3": greeting = f"セールスライター（v1.8: Counselor Mode）起動。解決策を提示するレターを書きます。"
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
        
        # 思考プロセス（カウンセラー視点での推敲）
        thinking_instruction = """
        【思考プロセス：カウンセラー視点チェック】
        1. 詩的になりすぎていないか？ポエムを排除し、具体的な言葉に置き換える。
        2. 「共感」だけで終わらず、必ず「分析（なぜ起きるか）」と「解決策（どうするか）」をセットにする。
        3. 読者を子供扱いせず、自立しようとする女性として尊重するトーンにする。
        """
        
        messages_for_api = st.session_state[session_key].copy()
        messages_for_api[-1]["content"] += thinking_instruction

        try:
            with st.spinner("Owl v1.8 is analyzing & writing..."):
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
    if not df_tasks.empty:
        st.dataframe(df_tasks)
    else:
        st.write("タスクなし")

elif menu == "✅ タスク管理 (ToDo)":
    st.header("Task Management")
    with st.form("add_task_form", clear_on_submit=True):
        t_title = st.text_input("タスク追加")
        t_prio = st.selectbox("優先度", ["High", "Middle", "Low"])
        if st.form_submit_button("追加"):
            add_task(current_project_id, t_title, t_prio)
            st.rerun()
    df_tasks = get_tasks(current_project_id)
    if not df_tasks.empty:
        st.data_editor(df_tasks, key="editor_v1_8")
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
