# karokit

A simple **Karotter (`karotter.com`) scraper/API wrapper** for Python.

Repository: `appipinopi/karokit`

## Features

- No official API key required
- Login/session support (cookies + token refresh)
- Create/search/get karots
- DM support
- Trends support
- Paid-plan ready header injection (`set_paid_plan`)

## Install

```bash
pip install karokit
```

## Quick Example

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

    await client.create_karot("Example karot")

    karots = await client.search_karot("python", "Latest")
    for item in karots:
        print(item)

    await client.close()

asyncio.run(main())
```

## Main Methods

- `create_karot`
- `search_karot`
- `get_user_karots`
- `send_dm`
- `get_trends`

## Paid Plan Readiness

If Karotter introduces paid plans, configure plan headers like this:

```python
client.set_paid_plan(
    "pro",
    entitlement_token="YOUR_TOKEN",
    extra_headers={"x-your-plan-header": "value"},
)
```

- `402` raises `PaidPlanRequiredError`
- `client.payment_retry_hook` can retry after refreshing paid entitlements

## Notes

- This is an unofficial client and can break when Karotter changes internals.
- Use responsibly and follow the service terms/laws.

## Thank
