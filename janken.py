import random

# ★これが「リスト」です！3つの文字をまとめて管理します
hands = ["Gu", "Choki", "Pa"]

print("--- Janken Game ---")
print("0: Gu, 1: Choki, 2: Pa")

# 1. ユーザーが選ぶ（数字で入力）
i = int(input("You (0-2): "))

# 2. リストから「選んだ文字」を取り出す
user_hand = hands[i]

# 3. コンピュータがランダムに選ぶ
pc_hand = random.choice(hands)

# 4. お互いの手を表示
print("You:", user_hand)
print("PC :", pc_hand)

# 5. 勝敗判定（ちょっと長いけど頑張って！）
if user_hand == pc_hand:
    print("Draw! (Aiko)")
elif (user_hand == "Gu" and pc_hand == "Choki") or \
     (user_hand == "Choki" and pc_hand == "Pa") or \
     (user_hand == "Pa" and pc_hand == "Gu"):
    print("You WIN!!")
else:
    print("You Lose...")
