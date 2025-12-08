import sys
import os
import json
import datetime

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.settings import OPENAI_API_KEY
from openai import OpenAI

def create_plan(project_id="mission_001"):
    """
    data/goal.txt を読み込み、プロジェクト計画(JSON)とサマリー(MD)を生成する
    """
    # 1. goal.txt を読み込む
    goal_path = os.path.join(os.path.dirname(__file__), '../data/goal.txt')
    
    if not os.path.exists(goal_path):
        print("⚠️ data/goal.txt が見つかりません。先に目標を書いてください！")
        return

    with open(goal_path, 'r', encoding='utf-8') as f:
        user_goal = f.read()

    print(f"🦉 Owlが目標を分析中... (Project: {project_id})")
    print("   (数十秒かかる場合があります...)")

    # 2. AIに作戦を立てさせる
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    # プロンプト（AIへの指示書）
    system_prompt = """
    あなたは優秀な戦略参謀『Owl』です。
    ユーザーの目標(goal.txt)をもとに、具体的で実現可能なプロジェクト計画を立ててください。
    
    【出力形式】
    必ず以下のJSONフォーマットのみを出力してください。余計な挨拶は不要です。
    
    {
      "project_name": "プロジェクト名",
      "goal_summary": "目標の要約",
      "phases": [
        {"phase": "Phase 1", "name": "フェーズ名", "period": "期間(例: 1-2週目)", "goal": "この期間のゴール", "tasks": ["タスク1", "タスク2", "タスク3"]}
      ],
      "advice": "成功のための重要なアドバイス"
    }
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"以下の目標に対する計画を立ててください：\n\n{user_goal}"}
            ]
        )
        ai_response = response.choices[0].message.content

        # 3. 結果を保存する
        # 保存先フォルダを作る: projects/mission_001/
        save_dir = os.path.join(os.path.dirname(__file__), f'../projects/{project_id}')
        os.makedirs(save_dir, exist_ok=True)

        # JSONとして保存
        json_path = os.path.join(save_dir, 'plan.json')
        # AIの返答がJSONか確認して保存（そのまま書き込む）
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(ai_response)

        # 読みやすいMarkdownも作る (summary.md)
        # JSONをパースしてみる
        try:
            plan_data = json.loads(ai_response)
            md_content = f"# 🦉 Project: {plan_data.get('project_name')}\n\n"
            md_content += f"## 🎯 目標\n{plan_data.get('goal_summary')}\n\n"
            md_content += "## 📅 ロードマップ\n"
            for p in plan_data.get('phases', []):
                md_content += f"### {p['phase']}: {p['name']} ({p['period']})\n"
                md_content += f"- **ゴール**: {p['goal']}\n"
                for t in p.get('tasks', []):
                    md_content += f"- [ ] {t}\n"
                md_content += "\n"
            md_content += f"## 💡 参謀からのアドバイス\n{plan_data.get('advice')}\n"
            
            md_path = os.path.join(save_dir, 'summary.md')
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
                
            print(f"\n✅ 作戦立案完了！以下のファイルを確認してください。")
            print(f"   📂 {save_dir}/")
            print(f"     ├─ 📄 plan.json (システム用)")
            print(f"     └─ 📝 summary.md (人間用 -> これを読んで！)")
            print(f"\n★中身を見るコマンド: cat projects/{project_id}/summary.md")

        except json.JSONDecodeError:
            print("⚠️ AIがJSON形式以外で返答しました。生の返答を保存します。")
            with open(os.path.join(save_dir, 'raw_response.txt'), 'w', encoding='utf-8') as f:
                f.write(ai_response)

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    create_plan("mission_launch_01")
