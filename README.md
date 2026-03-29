# karokit

`karokit` is an unofficial Python client/scraper for `karotter.com`, with twikit-style compatibility methods.

Repository: `appipinopi/karokit`

## Features

- Login/session support (access token, refresh token, CSRF, cookie export/import)
- Read APIs: timeline, post detail, search, trends, users, notifications, DMs
- Write APIs: create post, like, rekarot, bookmark, react, vote, follow, block, mute
- Extended action APIs: quotes/likes list, analytics, grouped notifications, follow requests
- Realtime support via Socket.IO (`notification`, `dd.newMessage`)
- Twikit-style aliases (`create_tweet`, `favorite_tweet`, `retweet`, `search_tweet`)
- Paid-plan readiness (`set_paid_plan`, `payment_retry_hook`)

## Install

```bash
pip install karokit
```

Development install from source:

```bash
pip install -r requirements.txt
pip install -e .
```

## Quick Example

```python
import asyncio
from karokit import Client


async def main() -> None:
    client = Client(locale="ja-JP")
    await client.login(identifier="YOUR_ID_OR_EMAIL", password="YOUR_PASSWORD")

    await client.create_karot("Hello from karokit")
    await client.like_post(12345)
    await client.follow_user(67890)

    data = await client.get_timeline(page=1, mode="following")
    print(data)
    await client.close()


asyncio.run(main())
```

## Realtime Example (Socket.IO)

```python
import asyncio
from karokit import Client, StreamingClient


async def main() -> None:
    client = Client()
    await client.login(identifier="YOUR_ID_OR_EMAIL", password="YOUR_PASSWORD")

    stream = StreamingClient(client)
    async for notif in stream.realtime_notifications():
        print("notification:", notif)


asyncio.run(main())
```

## Key Methods

- Post: `create_post`, `update_post`, `delete_post`, `record_post_views`
- Engagement: `like_post`, `rekarot_post`, `bookmark_post`, `react_to_post`, `vote_post_poll`
- Follow: `follow_user`, `unfollow_user`, `remove_follower`, `accept_follow_request`
- Notifications: `get_notifications`, `get_grouped_post_notifications`, `get_unread_notification_count`
- DM: `get_dm_groups`, `get_dm_messages`, `send_dm_message`, `send_dm`
- Realtime: `StreamingClient.realtime_notifications`, `StreamingClient.realtime_dm_messages`

## Paid Plan Readiness

If Karotter introduces paid plans, configure extra entitlement headers:

```python
client.set_paid_plan(
    "pro",
    entitlement_token="YOUR_TOKEN",
    extra_headers={"x-your-plan-header": "value"},
)
```

- `402` raises `PaidPlanRequiredError`
- `client.payment_retry_hook` can retry after entitlements are refreshed

## Safety Notes

- This project does not implement illegal bypass/fraud behavior.
- Use rate limits, normal browser-identical headers, and valid authentication only.
- Follow Karotter terms and applicable laws.
