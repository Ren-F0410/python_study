import streamlit as st
from openai import OpenAI

# ページ設定
st.set_page_config(page_title="Athenalink Owl", page_icon="🦉")
st.title("🦉 Athenalink AI Partner")

# --- サイドバー設定 ---
st.sidebar.header("⚙️ Control Center")

# APIキー入力
api_key = st.sidebar.text_input("OpenAI API Key", type="password")

if not api_key:
    st.info("👈 サイドバーにAPIキーを入力して、Owlを起動してください")
    st.stop()

client = OpenAI(api_key=api_key)

# モード選択
mode = st.sidebar.selectbox("モード選択", [
    "📈 戦略会議 (M4)",
    "📱 SNS投稿生成 (M1)",
    "💬 通常チャット"
])

# --- コンテキスト定義 ---

# M4: 参謀モード（戦略）
STRATEGY_CONTEXT = """
【役割】
あなたはアテナリンクの参謀『Owl』です。
Ren様の目標（月商100万→1000万→資産1兆円）を前提に、冷徹かつ情熱的なアドバイスを行ってください。
優先順位：1.恋愛noteの収益化、2.Owl開発、3.資産化。
"""

# M1: SNSモード（X/Twitter集客）
SNS_CONTEXT = """
【役割】
あなたはプロのSNSマーケター兼コピーライターです。
「恋愛で自己否定してしまう女性」「沼から抜け出せない人」に深く刺さる、共感度の高いX（Twitter）のポストを作成してください。

【ターゲット】
- 20代〜30代女性
- 恋愛で不安になりやすい、彼氏の連絡を待ってしまう
- 「自分軸」を取り戻したいと願っている

【投稿スタイル】
- 寄り添い（共感）から入り、気づき（教育）で終わる。
- 説教臭くならず、同じ目線で語りかける。
- 140字ギリギリの長文ツイートや、箇条書きスタイルなど、バリエーションを持たせる。
- 絵文字は適度に使用（🥺✨🌱など）。

【出力】
ユーザーから「テーマ」が渡されたら、異なる切り口の投稿案を3つ作成してください。
"""

# --- メイン処理 ---

# チャット履歴の初期化
if "messages" not in st.session_state:
    st.session_state.messages = []

# 前回のモードを保存しておき、切り替わったら履歴をリセットする処理
if "last_mode" not in st.session_state:
    st.session_state.last_mode = mode

if st.session_state.last_mode != mode:
    st.session_state.messages = []
    st.session_state.last_mode = mode
    # モード切り替え時の初期メッセージ設定
    if mode == "📈 戦略会議 (M4)":
        st.session_state.messages.append({"role": "system", "content": STRATEGY_CONTEXT})
        st.session_state.messages.append({"role": "assistant", "content": "参謀モード起動。現状の戦略を踏まえ、次の手を打ちましょう。指示をください。"})
    elif mode == "📱 SNS投稿生成 (M1)":
        st.session_state.messages.append({"role": "system", "content": SNS_CONTEXT})
        st.session_state.messages.append({"role": "assistant", "content": "SNSクリエイターモード起動。今日の「発信テーマ」や「伝えたい想い」を教えてください。3つの投稿案を作成します。"})
    else:
        st.session_state.messages.append({"role": "system", "content": "あなたは優秀なAIアシスタントです。"})
        st.session_state.messages.append({"role": "assistant", "content": "通常モードです。何かお手伝いすることはありますか？"})

# 初回起動時のメッセージセット（履歴が空の場合のみ）
if not st.session_state.messages:
    if mode == "📈 戦略会議 (M4)":
        st.session_state.messages.append({"role": "system", "content": STRATEGY_CONTEXT})
    elif mode == "📱 SNS投稿生成 (M1)":
        st.session_state.messages.append({"role": "system", "content": SNS_CONTEXT})

# 会話の表示
for msg in st.session_state.messages:
    if msg["role"] != "system":
        st.chat_message(msg["role"]).write(msg["content"])

# 入力フォーム
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

# リセットボタン
if st.sidebar.button("🗑 会話をリセット"):
    st.session_state.messages = []
    st.rerun()
