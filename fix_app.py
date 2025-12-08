import string

print("--- Athenalink App Repair Tool V3 (最強版) ---")

# 1. キーを受け取る
raw_key = input("👉 ここにAPIキーを貼り付けてEnter: ")

# 2. 強制捜索モード
# "sk-" がどこにあるか探す
start_index = raw_key.find("sk-")

if start_index == -1:
    print("❌ エラー: 入力された文字の中に 'sk-' が見当たりません。")
    print("コピー範囲を確認してください。")
    exit()

# 3. ゴミ掃除
# sk- から後ろを取得し、さらに余計な空白などを削除
clean_key = raw_key[start_index:].strip()
# 使える文字(英数字や記号)だけを残すフィルタリング
clean_key = "".join(c for c in clean_key if c in string.printable and c not in ["\n", "\r", " ", "　"])

print(f"✅ キーを抽出しました: {clean_key[:10]}... (長さ: {len(clean_key)})")

# 4. アプリ生成
app_code = f'''import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Athenalink AI", page_icon="🦉")
st.title("🦉 Athenalink AI Partner")
st.write("Ren専属メンター『Owl（ロジャー人格）』")

client = OpenAI(api_key="{clean_key}")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {{"role": "system", "content": "あなたはRenのメンター『Owl』です。ロジャーのように情熱的かつ論理的に、Renの資産1兆円という目標を全力で肯定し、アドバイスしてください。"}}
    ]

for msg in st.session_state.messages:
    if msg["role"] != "system":
        st.chat_message(msg["role"]).write(msg["content"])

user_input = st.chat_input("Owlに相談したいことは？")

if user_input:
    st.session_state.messages.append({{"role": "user", "content": user_input}})
    st.chat_message("user").write(user_input)
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=st.session_state.messages
        )
        ai_text = response.choices[0].message.content
        st.chat_message("assistant").write(ai_text)
        st.session_state.messages.append({{"role": "assistant", "content": ai_text}})
    except Exception as e:
        st.error(f"エラーが発生しました: {{e}}")
'''

with open("app.py", "w") as f:
    f.write(app_code)

print("✅ 'app.py' の修復完了！")
print("python3 -m streamlit run app.py を実行してください。")
