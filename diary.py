# 1. 今日の日記を入力してもらう
text = input("Write today's diary: ")

# 2. ファイルを開く
# "a" は "append"（追記）の意味。上書きせずに続きに書くモードです。
f = open("ren_diary.txt", "a")

# 3. ファイルに書き込む
# "\n" は「改行」という意味。これがないと文字が全部くっついちゃいます。
f.write(text + "\n")

# 4. ファイルを閉じる（重要！）
f.close()

print("Saved to ren_diary.txt!")
