# 1. 設計図（クラス）を作る
class Robot:
    # ロボットが作られる時に最初に呼ばれる「初期設定」
    def __init__(self, name):
        self.name = name  # 「自分の名前」を記憶する
        self.battery = 100 # 「バッテリー」は満タン(100)でスタート

    # ロボットができること（メソッド）1：挨拶
    def say_hello(self):
        print("Hello! I am " + self.name + ".")

    # ロボットができること（メソッド）2：動く
    def move(self):
        self.battery = self.battery - 10
        print(self.name, "moved! Battery:", self.battery)

# --- ここから設計図を使って実体化（製造）します ---

# 設計図から「robor」と「jarvis」という2体のロボットを製造！
my_robot1 = Robot("Robo-kun")
my_robot2 = Robot("Jarvis")

# それぞれに命令してみる
my_robot1.say_hello()  # ロボくん、挨拶して！
my_robot2.say_hello()  # ジャービス、挨拶して！

my_robot1.move()       # ロボくん、動いて！
my_robot2.move()       # ジャービス、動いて！
my_robot2.move()       # ジャービス、もう一回！
