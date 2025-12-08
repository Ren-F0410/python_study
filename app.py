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

# モード選択（M3を追加！）
mode = st.sidebar.selectbox("モード選択", [
    "📈 戦略会議 (M4)",
    "📱 SNS投稿生成 (M1)",
    "💰 セールスライティング (M3)",
    "💬 通常チャット"
])

# --- コンテキスト定義 ---

# M4: 参謀モード
STRATEGY_CONTEXT = """
【役割】
あなたはアテナリンクの参謀『Owl』です。
Ren様の目標（月商100万→1000万→資産1兆円）を前提に、冷徹かつ情熱的なアドバイスを行ってください。
優先順位：1.恋愛noteの収益化、2.Owl開発、3.資産化。
"""

# M1: SNSモード
SNS_CONTEXT = """
【役割】
あなたは恋愛系インフルエンサーの専属ライターです。
ターゲット：恋愛で「自己否定」「沼」「執着」に悩む女性。

【Ren流・発信の型】
1. 共感フック（〜だよね）
2. 寄り添い（わかるよ）
3. 視点の転換（でも実は〜なんだ）
4. 背中押し（大丈夫、変われるよ）
"""

# M3: セールスモード（新規追加！）
SALES_CONTEXT = """
【役割】
あなたは「人の心を動かし、行動させる」プロのセールスライターです。
Ren様の「恋愛note」を、悩める女性に届けるための魅力的な「販売ページの文章」や「強力な告知文」を作成してください。

【セールスの型 (PASONAの法則)】
1. **Problem (問題)**: 読者の痛み・悩みを明確に言い当てる。「〜で辛い思いをしてませんか？」
2. **Affinity (親近感)**: 「私もかつてはそうでした」と寄り添い、敵ではないことを示す。
3. **Solution (解決策)**: その悩みの唯一の解決策が「このnote」であることを示す。
4. **Offer (提案)**: 具体的に何が得られるか？（ベネフィット）を提示する。
5. **Action (行動)**: 「今すぐ読んで、新しい自分に出会ってください」と背中を押す。

【出力】
ユーザーから「商品のテーマ」や「訴求ポイント」が渡されたら、
この法則に基づいた、読み手の感情を揺さぶる文章を作成してください。
"""

# --- メイン処理 ---

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_mode" not in st.session_state:
    st.session_state.last_mode = mode

# モード切り替え時の処理
if st.session_state.last_mode != mode:
    st.session_state.messages = []
    st.session_state.last_mode = mode
    
    if mode == "📈 戦略会議 (M4)":
        st.session_state.messages.append({"role": "system", "content": STRATEGY_CONTEXT})
        st.session_state.messages.append({"role": "assistant", "content": "参謀モード起動。戦略的判断を下します。"})
    elif mode == "📱 SNS投稿生成 (M1)":
        st.session_state.messages.append({"role": "system", "content": SNS_CONTEXT})
        st.session_state.messages.append({"role": "assistant", "content": "SNSクリエイターモード起動。今日のテーマは何ですか？"})
    elif mode == "💰 セールスライティング (M3)":
        st.session_state.messages.append({"role": "system", "content": SALES_CONTEXT})
        st.session_state.messages.append({"role": "assistant", "content": "セールスライターモード起動。noteの「タイトル」や「売りたいポイント」を教えてください。最強のセールスレターを書きます。"})
    else:
        st.session_state.messages.append({"role": "system", "content": "あなたは優秀なアシスタントです。"})
        st.session_state.messages.append({"role": "assistant", "content": "通常モードです。"})

if not st.session_state.messages:
    # 初回メッセージ設定（万が一空の場合）
    if mode == "📈 戦略会議 (M4)":
        st.session_state.messages.append({"role": "system", "content": STRATEGY_CONTEXT})
    elif mode == "📱 SNS投稿生成 (M1)":
        st.session_state.messages.append({"role": "system", "content": SNS_CONTEXT})
    elif mode == "💰 セールスライティング (M3)":
        st.session_state.messages.append({"role": "system", "content": SALES_CONTEXT})

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
