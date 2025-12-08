import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI

# --- 1. アプリ設定 & DB初期化 ---
st.set_page_config(page_title="Owl v1.6", page_icon="🦉", layout="wide")

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

st.title("🦉 Athenalink OS v1.6")
st.caption("Deep Think Engine: High Volume & Concrete Empathy")

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

# --- 4. 脳みそのチューニング (v1.6 Deep Think Update) ---

# 共通スタイルガイド（さらに具体性を要求）
STYLE_GUIDE = """
【Athenalink Style Guide (Renイズム v2)】
■ ターゲット読者
- 深夜2時、連絡が来ないスマホを握りしめて孤独に耐えている女性。
- 「私が重いのかな」「どうせ愛されない」という自己否定の沼にいる。

■ 必須スタンス：『具体性3：抽象論7』の撤廃
- ×「自己肯定感を高めましょう」
- ○「鏡に映った自分に『今日もお疲れ』と声をかけることから始めよう」
- 常に「脳の仕組み」「心理学的背景」などの構造を説明し、納得感を与えること。

■ 禁止事項
- 1000文字以下の薄い販売レター。
- 1回も具体的なシチュエーション描写がない文章。
- 「まとめ」のような軽い締めくくり。
"""

# M4: 参謀プロンプト
def get_m4_prompt(p_name, p_goal, p_domain):
    return f"""
    あなたはプロジェクト『{p_name}』の最高戦略責任者(CSO)です。
    {STYLE_GUIDE}
    
    【ミッション】
    目標「{p_goal}」を達成するために、具体的かつ詳細なタスクを提示してください。
    
    【出力ルール】
    - タスクは最低でも **8〜15個** 洗い出してください。
    - 大雑把なタスク（例：記事を書く）はNG。「構成案を作る」「導入文を書く」「推敲する」のように分解してください。
    - 優先度(High/Middle)と共に、実行にかかる想定時間も添えてください。
    """

# M1: SNSプロンプト (ボリュームアップ)
def get_m1_prompt(p_name, p_goal):
    return f"""
    あなたは『{p_name}』の専属SNSマーケターです。
    {STYLE_GUIDE}
    
    【役割】
    Twitter(X)のタイムラインで異彩を放つ、濃い投稿を作成してください。
    
    【出力要件】
    - 提案数：3案
    - 文字数：**1案あたり120〜140文字（長文ツイート）**
    - 構成：
      1. フック（読者の痛みを代弁する一言）
      2. 描写（その痛みが起きている具体的な深夜のシーン）
      3. 構造（なぜそう考えてしまうのか？脳のクセや心理背景）
      4. 救い（今日からできる小さなアクション）
    """

# M2: 記事制作プロンプト
def get_m2_prompt(p_name, p_goal):
    return f"""
    あなたはベストセラー作家を担当する敏腕編集者です。
    {STYLE_GUIDE}
    
    【役割】
    読者が没入し、涙するような記事構成・執筆を行います。
    
    【構成案のルール】
    - 見出しは最低 **5〜10個** 作成してください。
    - 各見出しの下に、「ここで何を語るか（エピソード・心理描写）」を2〜3行で補足してください。
    """

# M3: セールスプロンプト (2000文字チャレンジ)
def get_m3_prompt(p_name, p_goal):
    return f"""
    あなたは「感情で物を売る」天才セールスライターです。
    {STYLE_GUIDE}
    
    【重要ミッション】
    読者が「これは私のための文章だ」と震えるような、**最低2000文字** の長文セールスレターを書いてください。
    途中で途切れることは許されません。最後まで書ききってください。
    
    【Story PASONA 詳細構成】
    1. **Problem (傷口)**: 500文字以上。深夜の孤独、通知のこないスマホ、自己嫌悪のループを、映画のワンシーンのように詳細に描写する。
    2. **Affinity (共感)**: 300文字以上。書き手自身の過去の失敗談や、同じ痛みを味わった経験を告白する。
    3. **Solution (解決)**: 構造の解説。なぜ「待つ」のをやめられないのか？それは意志が弱いからではなく、脳の仕組みであることを説く。
    4. **Offer (提案)**: このnoteで得られる「感情のベネフィット」。機能ではなく、手に入る未来の自分を描写する。
    5. **Action (行動)**: 最後の背中押し。恐怖を取り除く温かいメッセージ。
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

# 共通チャット機能 (v1.6 Deep Logic)
def render_chat(module_name, system_prompt):
    if not client:
        st.warning("👈 APIキーを入力してください")
        return

    session_key = f"chat_{current_project_id}_{module_name}"
    
    if session_key not in st.session_state:
        st.session_state[session_key] = [{"role": "system", "content": system_prompt}]
        greeting = "起動しました。"
        if module_name == "M4": greeting = f"参謀本部（v1.6）起動。タスクを細分化し、戦略を練ります。"
        if module_name == "M1": greeting = f"SNSクリエイター（v1.6）起動。深みのある投稿を作ります。"
        if module_name == "M3": greeting = f"セールスライター（v1.6）起動。2000文字級のレターに挑戦します。テーマをください。"
        if module_name == "M2": greeting = f"編集デスク（v1.6）起動。没入感のある構成を作ります。"
        st.session_state[session_key].append({"role": "assistant", "content": greeting})

    for msg in st.session_state[session_key]:
        if msg["role"] != "system":
            st.chat_message(msg["role"]).write(msg["content"])

    user_input = st.chat_input("ここに入力...")
    if user_input:
        st.chat_message("user").write(user_input)
        st.session_state[session_key].append({"role": "user", "content": user_input})
        
        # v1.6: 思考プロセス（Chain of Thought）の強化
        # 内部で「思考→推敲→執筆」のサイクルを回させる
        thinking_instruction = """
        【重要：思考プロセス】
        いきなり回答を出力せず、以下のステップを内部で実行してください。
        1. **感情エミュレーション**: ターゲット読者の「痛み」を具体的に想像する（例：息苦しさ、心拍数）。
        2. **具体化**: 抽象的な言葉（不安、寂しい）を、映像的な言葉（画面の光、冷たい指先）に変換する。
        3. **構造分析**: その悩みの原因を「脳のクセ」や「心理パターン」として論理的に定義する。
        4. **構成**: 指定された文字数（M1なら140字、M3なら2000字）を満たすための構成を組む。もし足りなければエピソードを追加する。
        5. **執筆**: 上記を踏まえて出力する。
        """
        
        messages_for_api = st.session_state[session_key].copy()
        messages_for_api[-1]["content"] += thinking_instruction

        try:
            with st.spinner("Owl v1.6 is thinking deeply (Deep Mode)..."):
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages_for_api,
                    temperature=0.7,
                    max_tokens=3000 # 長文対応のためトークン枠を拡大
                )
            ai_text = response.choices[0].message.content
            st.chat_message("assistant").write(ai_text)
            st.session_state[session_key].append({"role": "assistant", "content": ai_text})
        except Exception as e:
            st.error(f"エラー: {e}")

# --- 各画面 ---
if menu == "🏠 ダッシュボード":
    st.header(f"Project: {p_name}")
    with st.expander("ℹ️ プロジェクト目標", expanded=True):
        st.info(f"**GOAL:** {p_goal}")
    st.subheader("🔥 今日のタスク (High Priority)")
    df_tasks = get_tasks(current_project_id)
    active_tasks = df_tasks[(df_tasks['status'] != 'DONE') & (df_tasks['priority'] == 'High')]
    if not active_tasks.empty:
        for _, task in active_tasks.head(3).iterrows():
            st.warning(f"□ {task['title']}")
    else:
        st.success("High優先度のタスクはありません。")

elif menu == "✅ タスク管理 (ToDo)":
    st.header("Task Management")
    with st.form("add_task_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        t_title = c1.text_input("タスク追加")
        t_prio = c2.selectbox("優先度", ["High", "Middle", "Low"])
        if c3.form_submit_button("追加") and t_title:
            add_task(current_project_id, t_title, t_prio)
            st.rerun()
    df_tasks = get_tasks(current_project_id)
    if not df_tasks.empty:
        st.data_editor(
            df_tasks[['task_id', 'status', 'priority', 'title']],
            column_config={
                "task_id": st.column_config.NumberColumn("ID", width="small"),
                "status": st.column_config.SelectboxColumn("状態", options=["TODO", "DOING", "DONE"], required=True),
                "title": st.column_config.TextColumn("タスク", width="large"),
            },
            hide_index=True,
            use_container_width=True,
            key="task_editor_v1_6"
        )
        with st.expander("🗑 削除"):
            del_id = st.number_input("ID指定削除", step=1)
            if st.button("削除"):
                delete_task(del_id)
                st.rerun()

elif menu == "🧠 M4 参謀本部":
    st.header("Strategy Room (M4)")
    col_chat, col_tool = st.columns([2, 1])
    with col_chat:
        render_chat("M4", get_m4_prompt(p_name, p_goal, p_domain))
    with col_tool:
        st.markdown("### ⚡️ Quick Task Add")
        with st.form("quick_task_m4"):
            q_title = st.text_input("タスク名")
            q_prio = st.selectbox("優先度", ["High", "Middle", "Low"], key="q_m4")
            if st.form_submit_button("登録"):
                add_task(current_project_id, q_title, q_prio)
                st.success("登録済")

elif menu == "📱 M1 SNS集客":
    st.header("SNS Creator (M1)")
    render_chat("M1", get_m1_prompt(p_name, p_goal))

elif menu == "📝 M2 記事制作":
    st.header("Editor Room (M2)")
    render_chat("M2", get_m2_prompt(p_name, p_goal))

elif menu == "💰 M3 セールス":
    st.header("Sales Writer (M3)")
    render_chat("M3", get_m3_prompt(p_name, p_goal))
