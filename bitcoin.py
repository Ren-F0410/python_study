import requests
import time
import datetime

print("--- Bitcoin Monitor Started ---")
print("Press 'Control + C' to stop")

# CoinGeckoのAPIの住所（ビットコインを日本円で教えて！というリクエスト）
url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=jpy"

while True:
    try:
        # 1. APIに電話をかけてデータをもらう
        response = requests.get(url)
        
        # 2. もらったデータ（JSON）をPythonで読めるように変換
        # データはこういう形できます -> {'bitcoin': {'jpy': 14500000}}
        data = response.json()
        
        # 3. 価格を取り出す（箱の中の、箱の中を取り出すイメージ）
        price = data['bitcoin']['jpy']
        
        # 4. 今の時間と一緒に表示
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] 1 BTC = {price:,} JPY")
        
        # 10秒待機（連打すると怒られるので！）
        time.sleep(10)

    except Exception as e:
        print("Error:", e)
        time.sleep(10)
