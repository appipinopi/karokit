# karokit (日本語)

`karokit` は **Karotter（`karotter.com`）向けの非公式 scraper/API ラッパー**です。

リポジトリ: `appipinopi/karokit`

## 特徴

- 公式 API キー不要
- ログイン/セッション管理（Cookie + トークン更新）
- karot の作成・検索・取得
- DM 対応
- トレンド取得
- 有料プラン化に備えたヘッダ注入 (`set_paid_plan`)

## インストール

```bash
pip install -r requirements.txt
pip install -e .
```

## クイック例

```python
import asyncio
from karokit import Client

USERNAME = "example_user"
EMAIL = "email@example.com"
PASSWORD = "password0000"

client = Client("ja-JP")

async def main():
    await client.login(
        auth_info_1=USERNAME,
        auth_info_2=EMAIL,
        password=PASSWORD,
        cookies_file="cookies.json",
    )

    await client.create_karot("karokit から投稿")

    karots = await client.search_karot("python", "Latest")
    print(len(karots))

    await client.close()

asyncio.run(main())
```

## 主要メソッド

- `create_karot`
- `search_karot`
- `get_user_karots`
- `send_dm`
- `get_trends`

## 有料化への備え

Karotter が有料プラン制になった場合は次のように設定できます。

```python
client.set_paid_plan(
    "pro",
    entitlement_token="YOUR_TOKEN",
    extra_headers={"x-your-plan-header": "value"},
)
```

- `402` は `PaidPlanRequiredError` として判定
- `client.payment_retry_hook` により、課金トークン更新後の再試行が可能

## 注意

- 非公式クライアントのため、Karotter 側の仕様変更で動作が変わる可能性があります。
- 利用規約と法令を守って使用してください。
