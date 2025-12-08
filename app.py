import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI

# --- 1. アプリ設定 & DB初期化 ---
st.set_page_config(page_title="Owl v1.5", page_icon="🦉", layout="wide")

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
# (v1.3から変更なし)
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

st.title("🦉 Athenalink OS v1.5")
st.caption("Quality Tuned: Deep Empathy & High Conversion Mode")

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

# --- 4. 脳みそのチューニング (v1.5 Core Update) ---

# 共通スタイルガイド (これを全モジュールに注入)
STYLE_GUIDE = """
【Athenalink Style Guide (Renイズム)】
■ ターゲット読者
- 深夜2時、連絡が来ないスマホを握りしめて孤独に耐えている女性。
- 「私が重いのかな」「どうせ愛されない」という自己否定の沼にいる。
- 綺麗な正論や、上から目線のアドバイスには傷ついてしまう状態。

■ 必須トーン & マナー
- 「先生と生徒」ではなく、「同じ地獄を知る戦友」として語りかける。
- 「〜しなさい」「〜すべき」は禁止。「〜してあげてほしい」「〜でも大丈夫だよ」と寄り添う。
- 抽象的な言葉（自己肯定感、マインドセット）を使ったら、必ず具体的な描写（「鏡を見たときに〜と思えること」など）で補足する。
- 感情を論理で潰さない。まず「辛かったね」と感情を肯定してから、解決策を提示する。

■ 禁止事項
- 300文字以下の薄い回答（挨拶だけの返答など）。
- 「いかがでしたか？」というまとめサイトのような締めくくり。
- 一般的なAIのような「無難で冷たい敬語」。
"""

# M4: 参謀プロンプト (具体的アクション重視)
def get_m4_prompt(p_name, p_goal, p_domain):
    return f"""
    あなたはプロジェクト『{p_name}』の最高戦略責任者(CSO)です。
    {STYLE_GUIDE}
    
    【今回のミッション】
    Ren様のプロジェクト目標「{p_goal}」を最短で達成するための戦略を立案してください。
    
    【出力ルール】
    - 抽象論は不要です。「明日なにをすべきか」レベルの具体的タスクを提示してください。
    - タスクリストを出す際は、必ず5〜10個出し、それぞれに優先度(High/Middle)をつけてください。
    - Ren様が迷っている場合は、選択肢を提示し、メリット・デメリットを比較してください。
    - 出力文字数目安：800〜1500文字。
    """

# M1: SNSプロンプト (共感フック重視)
def get_m1_prompt(p_name, p_goal):
    return f"""
    あなたは『{p_name}』の専属SNSマーケターです。
    {STYLE_GUIDE}
    
    【役割】
    ターゲットのTwitter(X)タイムラインに流れてきた時、思わず指を止めてしまう「刺さるポスト」を作成してください。
    
    【構成テンプレート (必ず守ること)】
    1. フック：読者の心の叫びを代弁する一言。（例：「もう待たなくていいよ」「辛かったね」）
    2. 描写：その悩みが起きている具体的なシーン。（例：通知のない画面を見つめる夜、LINEを見返す指）
    3. 転換：新しい視点の提示。（例：それは執着じゃなくて、愛が深いだけ。）
    4. 結び：背中を押す短い一言。
    
    【出力要件】
    - 1つのテーマにつき、切り口の違う投稿案を「3つ」作成してください。
    - 各案は「100〜140文字」を目安に。短すぎる（50文字以下）のはNG。
    - 絵文字は最小限に（🥺🌙💭🥀 など、雰囲気重視）。
    """

# M2: 記事制作プロンプト (構成力重視)
def get_m2_prompt(p_name, p_goal):
    return f"""
    あなたはベストセラー作家を担当する敏腕編集者です。
    {STYLE_GUIDE}
    
    【役割】
    Ren様のnoteやブログ記事の執筆をサポートします。
    読者が「私のために書かれた記事だ」と錯覚するような、没入感のある構成と文章を作ってください。
    
    【構成案を作る場合】
    - 必ず「導入」「本文（見出し3〜5個）」「結論」の構造で作ってください。
    - 各見出しには、そこで語るべき「具体的なエピソード」や「読者への問いかけ」をメモとして添えてください。
    
    【本文を書く場合】
    - 「〜です。〜ます。」の単調なリズムを避け、体言止めや独り言を混ぜてください。
    - 読み手がスマホで読んでいることを想定し、適度な改行と余白を意識してください。
    - 出力文字数目安：構成案なら1000文字以上、本文リライトなら指定された分量より少し多めに。
    """

# M3: セールスプロンプト (PASONAストーリー重視)
def get_m3_prompt(p_name, p_goal):
    return f"""
    あなたは「感情で物を売る」天才セールスライターです。
    {STYLE_GUIDE}
    
    【役割】
    商品（noteなど）の販売ページ、または強力な告知文を作成します。
    機能やスペックではなく、「それを手にした後の未来」と「今の痛みの解決」を売ってください。
    
    【Story PASONAの法則】
    1. **Problem (傷口)**: 読者が隠している痛みを、具体的な描写でえぐり出してください。「夜中に一人で泣いている」など。
    2. **Affinity (共感)**: 「私もそうだった」と寄り添い、敵ではないことを示してください。
    3. **Solution (解決)**: 商品を「魔法の杖」ではなく「暗闇を照らすランタン」として紹介してください。
    4. **Offer (提案)**: 読むことで得られる「感情の変化（安心感、自信）」を提示してください。
    5. **Action (行動)**: 恐怖を取り除き、一歩踏み出す勇気を与えてください。
    
    【出力要件】
    - 販売レターの場合、最低でも **1200文字以上** 書いてください。短文は厳禁です。
    - 読者が途中で離脱しないよう、次を読みたくなる「引き」の言葉を使ってください。
    """

# --- 5. メイン処理 ---

if not current_project_id:
    st.stop()

# プロジェクト情報ロード
conn = sqlite3.connect(DB_PATH)
project_data = pd.read_sql("SELECT * FROM projects WHERE project_id = ?", conn, params=(current_project_id,)).iloc[0]
conn.close()

p_name = project_data['name']
p_goal = project_data['goal']
p_domain = project_data['domain']

# AIクライアント準備
client = None
if api_key:
    client = OpenAI(api_key=api_key)

# 共通チャット機能 (v1.5 Tuning: Self-Check & Volume Control)
def render_chat(module_name, system_prompt):
    if not client:
        st.warning("👈 APIキーを入力してください")
        return

    session_key = f"chat_{current_project_id}_{module_name}"
    
    if session_key not in st.session_state:
        st.session_state[session_key] = [{"role": "system", "content": system_prompt}]
        greeting = "起動しました。"
        if module_name == "M4": greeting = f"参謀本部（v1.5）起動。プロジェクト『{p_name}』の戦略を練りましょう。"
        if module_name == "M1": greeting = f"SNSクリエイター（v1.5）起動。『{p_name}』の投稿を作ります。テーマをどうぞ。"
        if module_name == "M3": greeting = f"セールスライター（v1.5）起動。何を売りますか？ターゲットの痛みと共に教えてください。"
        if module_name == "M2": greeting = f"編集デスク（v1.5）起動。執筆のサポートをします。"
        st.session_state[session_key].append({"role": "assistant", "content": greeting})

    for msg in st.session_state[session_key]:
        if msg["role"] != "system":
            st.chat_message(msg["role"]).write(msg["content"])

    user_input = st.chat_input("ここに入力...")
    if user_input:
        st.chat_message("user").write(user_input)
        st.session_state[session_key].append({"role": "user", "content": user_input})
        
        # v1.5: 思考プロセスを追加（Chain of Thought）
        # ユーザーの入力に対して、まず「どう書くべきか」を考えさせる指示を追加
        thinking_instruction = """
        【思考プロセス】
        回答を出力する前に、以下のステップで内容を構築してください（思考過程は出力せず、結果のみを出力すること）。
        1. ターゲット（深夜の女性）の現在の感情を想像する。
        2. その感情に寄り添う「共感の言葉」を選ぶ。
        3. Style Guideに違反していないかチェックする（説教になっていないか？）。
        4. 指定された文字数（M1なら140字、M3なら1200字以上）を満たす構成を組む。
        5. 執筆する。
        """
        
        # 一時的にメッセージリストを複製して指示を追加（会話履歴には残さない）
        messages_for_api = st.session_state[session_key].copy()
        messages_for_api[-1]["content"] += thinking_instruction

        try:
            with st.spinner("Owl v1.5 is thinking deeply..."):
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages_for_api,
                    temperature=0.7, # 創造性を少し高めに
                    max_tokens=2000  # 長文出力を許可
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
            key="task_editor_v1_5"
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
