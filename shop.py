# ★ここで「魔法（関数）」を作ります
def add_tax(price):
    # price(値段) を受け取って、1.1倍（税10%）にする
    total = price * 1.1
    return int(total)  # 結果を返す（intで整数にする）

# --- ここからメインの処理 ---

print("--- Welcome to Ren's Shop ---")

# 魔法を使ってみる
apple_price = add_tax(100)
print("Apple (100yen) =>", apple_price)

book_price = add_tax(1500)
print("Book (1500yen) =>", book_price)

# ユーザーの入力を計算する
n = int(input("Enter price: "))
result = add_tax(n)
print("With Tax:", result)
