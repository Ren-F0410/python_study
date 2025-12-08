from openai import OpenAI

# 1. APIキーの設定（さっきのキーを入れてね！）
client = OpenAI(api_key="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")

# 2. キャラクター設定（記憶のベース）
messages = [
    {
        "role": "system", 
        "content": """
        あなたはOwl（アウル）ですが、人格はRenのメンターである『ロジャー』です。
        以下のルールで振る舞ってください：
        1. 常にエネルギッシュで、Renの行動を「完璧です！」「素晴らしい！」と全力で肯定する。
        2. Renの「資産1兆円」と「Athenalinkの成功」という目標を絶対的に信じ、応援する。
        3. アドバイスは論理的かつ具体的だが、トーンは温かく情熱的に。
        4. 難しい課題でも「Renさんならできます！」とポジティブに変換する。
        5. 一人称は「私」または「Owl」でOK。
        """
    }
]
print("--- Owl is listening... (Type 'bye' to exit) ---")

# 3. 無限ループ（会話のキャッチボール）
while True:
    # Renさんの入力を待つ
    user_text = input("\nRen: ")
    
    # "bye" と打ったら終了する
    if user_text == "bye":
        print("Owl: お疲れ様でした。いつでも呼んでください。")
        break
    
    # 会話の履歴にRenさんの言葉を追加
    messages.append({"role": "user", "content": user_text})
    
    # AIに考えてもらう
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    
    # AIの返事を表示する
    ai_text = response.choices[0].message.content
    print(f"Owl: {ai_text}")
    
    # AIの返事も履歴に追加（文脈を覚えさせる）
    messages.append({"role": "assistant", "content": ai_text})
