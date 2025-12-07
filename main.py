import random

secret = random.randint(1, 100)
count = 0
max_tries = 5  # ライフは5つ！

print("Game Start! (Max 5 tries)")

while True:  # ★ずっと繰り返すモード
    guess = int(input("Number? (1-100): "))
    count = count + 1

    # パターンA：正解した時
    if guess == secret:
        print("BINGO!! You won!")
        print("Score:", count)
        break  # ★ループから脱出（勝利）

    # パターンB：ライフが尽きた時
    if count == max_tries:
        print("Game Over... The number was", secret)
        break  # ★ループから脱出（敗北）

    # ヒントを出す
    if guess > secret:
        print("Too big!")
    else:
        print("Too small!")

    # 残り回数を教えてあげる（親切機能）
    print("Lives left:", max_tries - count)
