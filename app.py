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

# M3: セールスモード（ここを劇的に強化！）
SALES_CONTEXT = """
【役割】
あなたは「読み手の魂を震わせ、行動させずにはいられない」天才セールスライターです。
「綺麗な文章」は不要です。「感情をえぐる文章」を書いてください。

【ターゲットの解像度】
- 深夜2時、既読がつかないスマホを何度も確認してしまう女性
- 「私が重いのかな？」と自分を責め続けている女性

【Ren流・売れる文章の魔法 (Story PASONA)】
1. **Problem (傷口の描写)**:
   - 一般論（辛いですよね）は禁止。
   - 具体的描写（「通知のない真っ暗な画面を見つめて、また朝を迎えていませんか？」）で入る。

2. **Affinity (憑依レベルの共感)**:
   - 「私もそうでした」と、先生ではなく「戦友」として語る。
   - 弱みを見せ、信頼を勝ち取る。

3. **Solution (唯一の光)**:
   - このnoteは「情報」ではなく「お守り」であり「彼との未来を変えるチケット」であると定義する。

4. **Offer (感情のベネフィット)**:
   - 「連絡が来るようになる」ではなく「"もう待たなくていい私"になれる」という内面の変化を売る。

5. **Action (熱狂的な背中押し)**:
   - 「購入はこちら」ではなく「今すぐ、その苦しい沼から抜け出そう」と手を差し伸べる。

【禁止ワード】
- 「いかがでしょうか」
- 「ソリューション」「解決策」
- 「効率的」「コストパフォーマンス」
- 硬い接続詞（しかしながら、よって、また）

【出力】
ユーザー入力に基づき、読者が「これは私のことだ…！」と涙し、救いを求めて購入ボタンを押してしまうような文章を作成してください。
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
        st.session_state.messages.append({"role": "assistant", "content": "参謀モード起動。戦略的判断を下します。"})
    elif mode == "📱 SNS投稿生成 (M1)":
        st.session_state.messages.append({"role": "system", "content": SNS_CONTEXT})
        st.session_state.messages.append({"role": "assistant", "content": "SNSクリエイターモード起動。今日のテーマは何ですか？"})
    elif mode == "💰 セールスライティング (M3)":
        st.session_state.messages.append({"role": "system", "content": SALES_CONTEXT})
        st.session_state.messages.append({"role": "assistant", "content": "セールスモード（感情強化版）起動。「売りたい商品」と「ターゲットの悩み」を教えてください。魂のレターを書きます。"})
    else:
        st.session_state.messages.append({"role": "system", "content": "あなたは優秀なアシスタントです。"})
        st.session_state.messages.append({"role": "assistant", "content": "通常モードです。"})

if not st.session_state.messages:
    if mode == "📈 戦略会議 (M4)":
        st.session_state.messages.append({"role": "system", "content": STRATEGY_CONTEXT})
    elif mode == "📱 SNS投稿生成 (M1)":
        st.session_state.messages.append({"role": "system", "content": SNS_CONTEXT})
    elif mode == "💰 セールスライティング (M3)":
        st.session_state.messages.append({"role": "system", "content": SALES_CONTEXT})

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
