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
mode = st.sidebar.selectbox("モード選択", ["💬 通常チャット", "📈 戦略会議 (M4)"])

# --- 戦略データ（Renさんのゴール） ---
STRATEGY_CONTEXT = """
【アテナリンク戦略データ】
■ 数値目標
- 6ヶ月後：月商100万円（恋愛事業）
- 1年後：月商1,000万円
- 30年後：個人資産1兆円

■ 直近のミッション
- 恋愛note第1弾の完成と販売開始
- Owl開発（v1.0実戦投入）
- X（Twitter）からの集客導線確立

あなたはアテナリンクの参謀『Owl』です。
この目標を前提に、具体的かつ論理的に、時には厳しくアドバイスしてください。
"""

# --- メイン処理 ---

# チャット履歴の初期化
if "messages" not in st.session_state:
    st.session_state.messages = []

# 「戦略会議」モードに切り替えた時、最初にコンテキストを注入する
if mode == "📈 戦略会議 (M4)" and not st.session_state.messages:
    st.session_state.messages.append({"role": "system", "content": STRATEGY_CONTEXT})
    initial_greeting = "アテナリンク参謀モードを起動しました。現状の戦略データを読み込んでいます。\n\n「今週の計画」や「次のアクション」について指示をください。"
    st.session_state.messages.append({"role": "assistant", "content": initial_greeting})

# 「通常チャット」モードの初期化
elif mode == "💬 通常チャット" and not st.session_state.messages:
    st.session_state.messages.append({"role": "system", "content": "あなたは優秀なアシスタントです。"})

# 会話の表示
for msg in st.session_state.messages:
    if msg["role"] != "system":
        st.chat_message(msg["role"]).write(msg["content"])

# 入力フォーム
user_input = st.chat_input("ここに入力...")

if user_input:
    # ユーザーの入力を表示・追加
    st.chat_message("user").write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # AIの応答生成
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=st.session_state.messages
        )
        ai_text = response.choices[0].message.content
        
        # AIの応答を表示・追加
        st.chat_message("assistant").write(ai_text)
        st.session_state.messages.append({"role": "assistant", "content": ai_text})
        
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

# 履歴リセットボタン
if st.sidebar.button("🗑 会話をリセット"):
    st.session_state.messages = []
    st.rerun()
