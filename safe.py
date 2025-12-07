print("--- Super Safe Calculator ---")

while True:
    # try: 「ここから下は、エラーが起きるかもしれない危険地帯です！」という合図
    try:
        user_input = input("Enter a number (or 'q'): ")
        
        if user_input == "q":
            print("Bye!")
            break

        # 数字に変換（ここで文字を入れるとエラーになる！）
        number = int(user_input)

        # 割り算（ここで0を入れるとエラーになる！）
        result = 100 / number

        print("100 divided by", number, "is", result)

    # except: 「もしエラーが起きたら、クラッシュせずにここを実行して！」という命綱
    except ValueError:
        print("⚠️  Error: Please enter a NUMBER, not text!")

    except ZeroDivisionError:
        print("⚠️  Error: You cannot divide by ZERO!")
