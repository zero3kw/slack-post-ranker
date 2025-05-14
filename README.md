# 📊 Slack Post Ranker

Slackチャンネルの投稿数をユーザーごとに集計し、ランキング形式で表示・投稿するBotです。  
GitHub ActionsとSlack APIを用いて、自動実行され、チャンネルに結果を通知します。

---

## 🔧 機能概要

- 指定チャンネルの投稿を取得（デフォルトは直近7日間）
- Botの投稿や通知などを除外（通常のユーザー投稿のみ）
- 投稿数をユーザーごとにカウントし、ランキングを生成
- 結果をそのままSlackに自動投稿（アイコン絵文字・Bot名も指定可能）
- GitHub Actionsでスケジューリング＆自動実行

---

## 🛠 セットアップ手順

### 1. 必要な環境変数を GitHub Secrets に設定

| Key               | 説明                   |
|------------------|------------------------|
| `SLACK_TOKEN`     | SlackのBot Token（xoxb-） |
| `SLACK_CHANNEL_ID`| 投稿対象のチャンネルID |

### 2. 実行方法

#### ✅ 手動実行
```bash
python main.py --token <SLACK_TOKEN> --channel <CHANNEL_ID> --days 7
```

#### GitHub Actionsで定期実行
`.github/workflows/slack_counter.yml` により、自動実行されます。