english_dict = {
    "apple": "りんご",
    "book": "本",
    "cat": "猫",
    "dog": "犬",
    "python": "ニシキヘビ"
}

print("--- My Dictionary ---")

while True:
    # ユーザーに入力を求める
    word = input("English word? (or 'q' to quit): ")

    if word == "q":
        break

    # ★ここからが新機能！
    if word in english_dict:
        # 知っている単語のとき
        print("=>", word, "is", english_dict[word])
    else:
        # 知らない単語のとき -> 登録しちゃう？
        print("I don't know that word.")
        choice = input("Do you want to add it? (y/n): ")
        
        if choice == "y":
            meaning = input("Japanese meaning: ")
            # ★【最強の魔法】辞書に新しいデータを追加する
            english_dict[word] = meaning
            print("Saved!", word, "=", meaning)
        else:
            print("Okay, skip.")
