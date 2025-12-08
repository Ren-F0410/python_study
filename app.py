import streamlit as st
from openai import OpenAI

# ページ設定
st.set_page_config(page_title="Athenalink AI", page_icon="🦉")
st.title("🦉 Athenalink AI Partner")
st.write("Ren専属メンター『Owl』 - Mobile Version")

# サイドバーでキーを入力させる（安全対策）
# これにより、GitHubに公開してもキーは漏れません
api_key = st.sidebar.text_input("OpenAI API Key", type="password")

if not api_key:
    st.info("👈 サイドバーにAPIキーを入力して、Owlを起動してください")
    st.stop()

client = OpenAI(api_key=api_key)

# チャット履歴の初期化
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "あなたはRenの参謀『Owl』です。資産1兆円とアテナリンクの成功を目指し、具体的かつ情熱的にアドバイスしてください。"}
    ]

# 会話の表示
for msg in st.session_state.messages:
    if msg["role"] != "system":
        st.chat_message(msg["role"]).write(msg["content"])

# 入力フォーム
user_input = st.chat_input("Owlに相談したいことは？")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)
    
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
