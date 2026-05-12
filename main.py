import requests
from collections import Counter
import time
from datetime import datetime, timedelta
import argparse
from typing import Dict, List, Any, Optional, Tuple


class SlackApiClient:
    """Slack API通信を担当するクラス"""

    def __init__(self, token: str) -> None:
        self.token = token
        self.headers = {'Authorization': f'Bearer {token}'}
        self.base_url = 'https://slack.com/api'

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict:
        """APIリクエストを実行し、レスポンスを返す"""
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)

        # 接続エラーのケースをハンドリング
        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ 接続エラー: {e}")
            return {"ok": False, "error": str(e)}

        data = response.json()

        if not data.get("ok"):
            print(f"⚠️ API エラー ({endpoint}): {data.get('error')}")

        return data

    def fetch_messages(self, channel_id: str, oldest_ts: int, cursor: Optional[str] = None) -> Dict:
        """特定チャンネルのメッセージを取得"""
        params = {
            'channel': channel_id,
            'limit': 300,
            'oldest': oldest_ts
        }

        if cursor:
            params['cursor'] = cursor

        return self._make_request('conversations.history', params)

    def fetch_users(self) -> Dict:
        """ユーザー一覧を取得"""
        return self._make_request('users.list')

    def post_message(self, channel_id: str, blocks: List[Dict]) -> Dict:
        """チャンネルにメッセージを投稿"""
        url = f"{self.base_url}/chat.postMessage"

        payload = {
            "channel": channel_id,
            "blocks": blocks,
        }

        response = requests.post(url, headers={**self.headers, "Content-Type": "application/json"}, json=payload)

        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ 投稿接続エラー: {e}")
            return {"ok": False, "error": str(e)}

        data = response.json()

        if not data.get("ok"):
            print(f"⚠️ 投稿失敗: {data.get('error')}")

        return data


class SlackMessageAnalyzer:
    """メッセージ分析とレポート生成を担当するクラス"""

    def __init__(self, client: SlackApiClient) -> None:
        self.client = client
        self.user_map = {}

    def fetch_all_messages(self, channel_id: str, days: int) -> List[Dict]:
        """指定期間内のすべてのメッセージを取得"""
        messages = []
        has_more = True
        cursor = None

        oldest_ts = int(time.time() - days * 86400)

        print(f"✅ メッセージ取得中...（過去{days}日間）")

        while has_more:
            res = self.client.fetch_messages(channel_id, oldest_ts, cursor)

            if not res.get("ok"):
                break

            messages.extend(res.get('messages', []))
            has_more = res.get('has_more', False)
            cursor = res.get('response_metadata', {}).get('next_cursor')

            # レート制限を考慮
            time.sleep(1)

        print(f"取得メッセージ数: {len(messages)} 件")
        return messages

    def load_user_data(self) -> None:
        """ユーザー情報を取得してマッピングを作成"""
        print("✅ ユーザー情報取得中...")

        res = self.client.fetch_users()

        if not res.get("ok"):
            return

        self.user_map = {
            user['id']: user.get('profile', {}).get('display_name') or
                       user.get('profile', {}).get('real_name') or
                       user['id']
            for user in res.get('members', [])
        }

    def count_messages_by_user(self, messages: List[Dict]) -> Counter:
        """ユーザーごとのメッセージ数をカウント"""
        counter = Counter()

        for msg in messages:
            if (
                'user' in msg and
                msg.get('subtype') is None and
                'bot_id' not in msg
            ):
                counter[msg['user']] += 1

        return counter

    def generate_ranking_report(self, counts: Counter, days: int) -> Tuple[str, List[Dict]]:
        """ランキングレポートのテキストとブロックを生成"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # ランキングテキストの生成
        ranking_lines = []

        # 投稿数の多い順、同数の場合は名前の昇順で安定ソート
        top_users = sorted(
            counts.items(),
            key=lambda kv: (-kv[1], self.user_map.get(kv[0], kv[0]))
        )

        # 同数は同順位、次は連番（詰める方式: 1,1,2,3...）
        medals = {1: "🥇 ", 2: "🥈 ", 3: "🥉 "}
        rank = 0
        prev_count = None
        for (user_id, count) in top_users:
            if count != prev_count:
                rank += 1
                prev_count = count

            name = self.user_map.get(user_id, user_id)
            medal = medals.get(rank, "   ")
            ranking_lines.append(f"{medal}{name}: {count}回")

        ranking_text = "\n".join(ranking_lines)

        # 期間を含むサマリーの作成
        summary = f"*📊投稿数ランキング（期間：{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}）*\n"
        summary += ranking_text

        # Slackブロックの作成
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{summary}"
                }
            }
        ]

        return summary, blocks


def main() -> None:
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description="Slack投稿数ランキング")
    parser.add_argument('--token', required=True, help='Slack Bot Token')
    parser.add_argument('--channel', required=True, help='Slack Channel ID')
    parser.add_argument('--days', type=int, default=7, help='何日前から取得するか（デフォルト: 7日）')
    parser.add_argument('--dry-run', action='store_true', help='Slackに投稿せず内容だけ表示')

    args = parser.parse_args()

    # クライアントの初期化
    client = SlackApiClient(args.token)
    analyzer = SlackMessageAnalyzer(client)

    # ユーザー情報の取得
    analyzer.load_user_data()

    # メッセージの取得
    messages = analyzer.fetch_all_messages(args.channel, args.days)

    # カウント集計
    counts = analyzer.count_messages_by_user(messages)

    # レポート生成
    summary, blocks = analyzer.generate_ranking_report(counts, args.days)

    # 結果の出力/投稿
    if args.dry_run:
        print("✅ [dry-run] 投稿内容:")
        print(summary)
    else:
        res = client.post_message(args.channel, blocks)
        if res.get("ok"):
            print("✅ Slackに投稿しました")


if __name__ == '__main__':
    main()