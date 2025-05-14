import requests
from collections import Counter
import time
from datetime import datetime, timedelta
import argparse

def fetch_all_messages(token, channel_id, days):
    url = 'https://slack.com/api/conversations.history'
    headers = {'Authorization': f'Bearer {token}'}
    messages = []
    has_more = True
    cursor = None

    oldest_ts = int(time.time() - days * 86400)

    while has_more:
        params = {
            'channel': channel_id,
            'limit': 300,
            'oldest': oldest_ts
        }
        if cursor:
            params['cursor'] = cursor

        res = requests.get(url, headers=headers, params=params).json()

        if not res.get("ok"):
            print("⚠️ エラー:", res.get("error"))
            break

        messages.extend(res.get('messages', []))
        has_more = res.get('has_more', False)
        cursor = res.get('response_metadata', {}).get('next_cursor')
        time.sleep(1)

    return messages

def get_usernames(token):
    url = 'https://slack.com/api/users.list'
    headers = {'Authorization': f'Bearer {token}'}
    res = requests.get(url, headers=headers).json()

    if not res.get("ok"):
        print("⚠️ ユーザー一覧取得失敗:", res.get("error"))
        return {}

    return {
        user['id']: user.get('profile', {}).get('display_name') or
                    user.get('profile', {}).get('real_name') or
                    user['id']
        for user in res.get('members', [])
    }

def count_messages_by_user(messages):
    counter = Counter()
    for msg in messages:
        if 'user' in msg and msg.get('subtype') is None:
            counter[msg['user']] += 1
    return counter

def format_ranking(counts, user_map):
    lines = []
    for user_id, count in counts.most_common():
        name = user_map.get(user_id, user_id)
        lines.append(f"{name}: {count}回")
    return "\n".join(lines)

def post_to_slack(token, channel_id, message):
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "channel": channel_id,
        "icon_emoji": ":robot_face:",
        "text": message
    }
    res = requests.post(url, headers=headers, json=payload).json()

    if not res.get("ok"):
        print("⚠️ 投稿失敗:", res.get("error"))
    else:
        print("✅ 結果をSlackに投稿しました")

def main():
    parser = argparse.ArgumentParser(description="Slack投稿数ランキング")
    parser.add_argument('--token', required=True, help='Slack Bot Token')
    parser.add_argument('--channel', required=True, help='Slack Channel ID')
    parser.add_argument('--days', type=int, default=7, help='何日前から取得するか（デフォルト: 7日）')
    args = parser.parse_args()

    slack_token = args.token
    channel_id = args.channel
    days = args.days

    print(f"✅ メッセージ取得中...（過去{days}日間）")
    messages = fetch_all_messages(slack_token, channel_id, days)
    print(f"取得メッセージ数: {len(messages)} 件")

    print("✅ ユーザー情報取得中...")
    user_map = get_usernames(slack_token)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    counts = count_messages_by_user(messages)

    summary = f"📊 投稿数ランキング（期間：{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}）\n"
    summary += format_ranking(counts, user_map)

    post_to_slack(slack_token, channel_id, summary)

if __name__ == '__main__':
    main()
