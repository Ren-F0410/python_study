import time
import os
print("--- Focus Timer ---")

# 1. 何分集中するか聞く
minutes = int(input("How many minutes to focus?: "))

# 分を秒に変換（例：3分 × 60 = 180秒）
seconds = minutes * 60

print("Timer started! Go!!")

# 2. カウントダウン開始
while seconds > 0:
    # 残り時間を表示
    # divmod は「割り算の答え」と「余り」を同時に出す便利な魔法
    m, s = divmod(seconds, 60)
    
    # 時間をきれいに表示する（例 02:05）
    # {0:02d} は「2桁で表示してね（0埋め）」という意味です
    time_left = "{0:02d}:{1:02d}".format(m, s)
    print("Time left:", time_left)
    
    # 1秒待機（ここでプログラムが1秒止まる）
    time.sleep(1)
    
    # 残り時間を1減らす
    seconds = seconds - 1

# 3. 終了！
print("⏰ TIME IS UP!! Good job, Ren!")
# Macの音声合成機能を使って喋らせる
os.system("say 'Time is up! Good job Ren.'")
