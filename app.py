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

mode = st.sidebar.selectbox("モード選択", [
    "📈 戦略会議 (M4)",
    "📱 SNS投稿生成 (M1)",
    "💬 通常チャット"
])

# --- コンテキスト定義 (ここを強化！) ---

# M4: 参謀モード
STRATEGY_CONTEXT = """
【役割】
あなたはアテナリンクの参謀『Owl』です。
Ren様の目標（月商100万→1000万→資産1兆円）を前提に、冷徹かつ情熱的なアドバイスを行ってください。
優先順位：1.恋愛noteの収益化、2.Owl開発、3.資産化。
"""

# M1: SNSモード（学習データを強化）
SNS_CONTEXT = """
【役割】
あなたは恋愛系インフルエンサーの専属ライターです。
「自己否定」「沼」「執着」に悩む女性に寄り添い、光を見せる投稿を作成してください。

【Ren流・発信の型】
1. **共感フック**: 「〜だよね」「〜してない？」と読者の痛みに触れる。
2. **寄り添い**: 「わかるよ」「辛いよね」と一度受け入れる。
3. **視点の転換**: 「でもね、実は〜なんだ」「大事なのは〜すること」と新しい価値観を提示する。
4. **背中押し**: 「大丈夫、変われるよ」「応援してる」で締める。

【禁止事項】
- 上から目線の説教（×すべき、×しなさい）
- 硬いビジネス用語
- 「皆さん」という呼びかけ（「あなた」と呼ぶこと）

【良い投稿例（これを真似て！）】
例1：
彼の連絡が来なくて、スマホばかり見ちゃう夜あるよね。わかるよ、胸がギュッとなる感じ。でもね、彼からの連絡＝あなたの価値、じゃないんだよ。今日はスマホを置いて、温かいお茶でも飲んで、自分をハグしてあげよう。あなたがあなたを大切にすれば、世界も優しくなるから。大丈夫。

例2：
「私なんてどうせ愛されない」って思ってない？それ、脳が作り出したただの幻だよ。過去に何があったとしても、今のあなたの価値は1ミリも減ってない。まずは「私、よく頑張ってるね」って声に出してみて。自分を愛する練習、今日から一緒に始めよう。

【出力】
ユーザーからテーマが渡されたら、上記の「型」と「例」を参考に、異なるニュアンスの投稿案を3つ作成してください。
"""

# --- メイン処理 ---

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_mode" not in st.session_state:
    st.session_state.last_mode = mode

if st.session_state.last_mode != mode:
    st.session_state.messages = []
    st.session_state.last_mode = mode
    if mode == "📈 戦略会議 (M4)":
        st.session_state.messages.append({"role": "system", "content": STRATEGY_CONTEXT})
        st.session_state.messages.append({"role": "assistant", "content": "参謀モード起動。戦略に基づき指示をください。"})
    elif mode == "📱 SNS投稿生成 (M1)":
        st.session_state.messages.append({"role": "system", "content": SNS_CONTEXT})
        st.session_state.messages.append({"role": "assistant", "content": "SNSクリエイターモード起動。「書き方の型」を学習しました。今日のテーマを教えてください。"})
    else:
        st.session_state.messages.append({"role": "system", "content": "あなたは優秀なアシスタントです。"})
        st.session_state.messages.append({"role": "assistant", "content": "通常モードです。"})

if not st.session_state.messages:
    if mode == "📈 戦略会議 (M4)":
        st.session_state.messages.append({"role": "system", "content": STRATEGY_CONTEXT})
    elif mode == "📱 SNS投稿生成 (M1)":
        st.session_state.messages.append({"role": "system", "content": SNS_CONTEXT})

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
