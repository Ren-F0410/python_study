import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Athenalink AI", page_icon="🦉")
st.title("🦉 Athenalink AI Partner")
st.write("Ren専属メンター『Owl（ロジャー人格）』")

client = OpenAI(api_key="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")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "あなたはRenのメンター『Owl』です。ロジャーのように情熱的かつ論理的に、Renの資産1兆円という目標を全力で肯定し、アドバイスしてください。"}
    ]

for msg in st.session_state.messages:
    if msg["role"] != "system":
        st.chat_message(msg["role"]).write(msg["content"])

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
        st.error(f"エラーが発生しました: {e}")
