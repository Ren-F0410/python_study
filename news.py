import requests
from bs4 import BeautifulSoup
import datetime  # ★日時を扱う魔法

# 1. 今の日時を取得
now = datetime.datetime.now()
date_str = now.strftime("%Y-%m-%d %H:%M:%S")

# 2. レポートファイルを開く（今回は "w" で上書き保存します）
# ファイル名: news_report.txt
f = open("news_report.txt", "w")

# --- ファイルにヘッダーを書く ---
f.write("Yahoo! News Report\n")
f.write("Time: " + date_str + "\n")
f.write("-" * 30 + "\n")

# 3. Yahoo!にアクセス
url = "https://news.yahoo.co.jp/"
print("Accessing to:", url)

try:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # ページ内のリンクを全取得
    all_links = soup.find_all("a")
    
    count = 0
    for link in all_links:
        text = link.text.strip()
        
        # 15文字以上ならニュースとみなす
        if len(text) > 15:
            # ★画面に表示するだけでなく、ファイルにも書き込む！
            print("Found:", text)  # 画面用
            f.write(text + "\n")   # ファイル用
            count = count + 1
            
        if count >= 10:  # 10個集めたら終了
            break

    print("Success! Saved to news_report.txt")

except Exception as e:
    print("Error happened:", e)

# 4. 最後にファイルを閉じる（超重要！）
f.close()
