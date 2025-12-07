import os
import shutil  # 引越し業者（ファイルを移動させる魔法）

# ターゲットの部屋（さっき作ったフォルダ）
target_dir = "messy_room"

print("--- Cleaning Start! ---")

# 1. 部屋の中にあるファイルリストを取得
files = os.listdir(target_dir)
print("Files found:", files)

# 2. ファイルを1つずつチェックする（これが forループ！）
# filesの中身を1個ずつ取り出して、filename という箱に入れてループします
for filename in files:
    
    # ファイルの「拡張子（しっぽ）」を調べる
    if filename.endswith(".txt"):
        # テキストファイルなら "Text_Box" フォルダへ
        destination = "Text_Box"
    elif filename.endswith(".jpg") or filename.endswith(".png"):
        # 画像ファイルなら "Image_Box" フォルダへ
        destination = "Image_Box"
    else:
        # それ以外は何もしないで次へ（スキップ）
        continue
    
    # --- 移動処理 ---
    
    # 移動先のフォルダの「完全な住所」を作る
    # 例: messy_room/Text_Box
    dest_path = os.path.join(target_dir, destination)
    
    # もし移動先フォルダがなかったら、自動で作る（気が利く！）
    if not os.path.exists(dest_path):
        os.mkdir(dest_path)
        print("Created folder:", destination)
    
    # ファイルを移動させる
    # shutil.move(今の場所, 新しい場所)
    src = os.path.join(target_dir, filename)
    dst = os.path.join(dest_path, filename)
    shutil.move(src, dst)
    
    print("Moved:", filename, "->", destination)

print("--- Cleaning Complete! ---")
