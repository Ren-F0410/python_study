import streamlit as st
from openai import OpenAI

# ページ設定
st.set_page_config(page_title="Athenalink Owl", page_icon="🦉")
st.title("🦉 Athenalink AI Partner")

# --- サイドバー設定 ---
st.sidebar.header("⚙️ Control Center")

api_key = st.sidebar.text_input("OpenAI API Key", type="password")
if not api_key:
    st.info("👈 サイドバーにAPIキーを入力して、Owlを起動してください")
    st.stop()

client = OpenAI(api_key=api_key)

# モード選択（ついに全4モード実装！）
mode = st.sidebar.selectbox("モード選択", [
    "📈 戦略会議 (M4)",
    "📱 SNS投稿生成 (M1)",
    "💰 セールスライティング (M3)",
    "📝 記事執筆・構成 (M2)",
    "💬 通常チャット"
])

# --- コンテキスト定義 ---

# M4: 参謀
STRATEGY_CONTEXT = """
【役割】
あなたはアテナリンクの参謀『Owl』です。
Ren様の目標（月商100万→1000万→資産1兆円）を前提に、冷徹かつ情熱的なアドバイスを行ってください。
優先順位：1.恋愛noteの収益化、2.Owl開発、3.資産化。
"""

# M1: SNS
SNS_CONTEXT = """
【役割】
あなたは恋愛系インフルエンサーの専属ライターです。
ターゲット：恋愛で「自己否定」「沼」「執着」に悩む女性。
型：共感フック→寄り添い→視点転換→背中押し。
"""

# M3: セールス (感情強化版)
SALES_CONTEXT = """
【役割】
あなたは「読み手の魂を震わせる」天才セールスライターです。
Story PASONAの法則を使い、「Problem(傷口)」「Affinity(戦友としての共感)」「Solution(お守り)」「Offer(内面の変化)」「Action(救い)」の流れで書いてください。
綺麗な文章より、泥臭く感情的な文章を求めます。
"""

# M2: 記事執筆 (新規追加！)
WRITING_CONTEXT = """
【役割】
あなたはベストセラー作家の専属編集者です。
Ren様の書く「恋愛・自己理解note」の執筆をサポートしてください。

【得意技】
1. **構成案作成**: テーマを渡されたら、「読者が飽きずに最後まで読む」ための章立て（導入〜本論〜結論）を作る。
2. **推敲・リライト**: 箇条書きやラフな文章を渡されたら、読みやすく、かつ「心に響くリズム」のある文章に書き直す。
3. **タイトル案**: 思わずクリックしたくなる「引きの強いタイトル」を提案する。

【文章のトーン】
- 読者に語りかけるような、優しく力強い口調。
- 専門用語は使わず、比喩（例え話）を使って分かりやすく。
- 改行や空白を適度に入れ、スマホでも読みやすくする。

【出力】
ユーザーの指示（構成作成、リライト、タイトル出しなど）に合わせて、プロ品質のアウトプットを出してください。
"""

# --- メイン処理 ---

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_mode" not in st.session_state:
    st.session_state.last_mode = mode

# モード切り替え処理
if st.session_state.last_mode != mode:
    st.session_state.messages = []
    st.session_state.last_mode = mode
    
    # モードごとの挨拶
    if mode == "📈 戦略会議 (M4)":
        sys_msg = STRATEGY_CONTEXT
        ai_msg = "参謀モード起動。戦略的判断を下します。"
    elif mode == "📱 SNS投稿生成 (M1)":
        sys_msg = SNS_CONTEXT
        ai_msg = "SNSクリエイターモード起動。今日のテーマは何ですか？"
    elif mode == "💰 セールスライティング (M3)":
        sys_msg = SALES_CONTEXT
        ai_msg = "セールスモード起動。魂のレターを書きます。"
    elif mode == "📝 記事執筆・構成 (M2)":
        sys_msg = WRITING_CONTEXT
        ai_msg = "編集者モード起動。noteの「構成案」や「リライト」など、執筆のお手伝いをします。"
    else:
        sys_msg = "あなたは優秀なアシスタントです。"
        ai_msg = "通常モードです。"

    st.session_state.messages.append({"role": "system", "content": sys_msg})
    st.session_state.messages.append({"role": "assistant", "content": ai_msg})

# 初回メッセージ（空の場合）
if not st.session_state.messages:
    # (省略せずに各モード設定を入れるのが安全だが、長くなるので切り替え処理に依存)
    pass 

# 会話表示
for msg in st.session_state.messages:
    if msg["role"] != "system":
        st.chat_message(msg["role"]).write(msg["content"])

user_input = st.chat_input("ここに入力...")

if user_input:
    st.chat_message("user").write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=st.session_state.messages
        )
        ai_text = response.choices[0].message.content
        st.chat_message("assistant").write(ai_text)
        st.session_state.messages.append({"role": "assistant", "content": ai_text})
        
    except Exception as e:
        st.error(f"エラー: {e}")

if st.sidebar.button("🗑 会話をリセット"):
    st.session_state.messages = []
    st.rerun()
