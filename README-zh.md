# karokit (简体中文)

`karokit` 是面向 **Karotter（`karotter.com`）** 的非官方 scraper/API 封装。  
仓库: `appipinopi/karokit`

## 功能

- 无需官方 API Key
- 登录与会话管理（Cookie + Token 刷新）
- karot 的创建、搜索、读取
- 支持私信（DM）
- 支持趋势接口
- 预留付费方案头部注入（`set_paid_plan`）

## 安装（普通用户）

从 PyPI 安装:

```bash
pip install karokit
```

如果 `pip` 版本较旧:

```bash
python -m pip install --upgrade pip
pip install karokit
```

验证安装:

```bash
python -c "import karokit; print(karokit.__version__)"
```

升级:

```bash
pip install -U karokit
```

## 开发安装（从源码）

```bash
pip install -r requirements.txt
pip install -e .
```

## 快速示例

```python
import asyncio
from karokit import Client


async def main() -> None:
    client = Client(locale="zh-CN")
    await client.login(identifier="YOUR_ID_OR_EMAIL", password="YOUR_PASSWORD")

    await client.create_karot("Hello from karokit")
    posts = await client.search_karot("python", "Latest")
    print(len(posts))

    await client.close()


asyncio.run(main())
```

## 主要方法

- `create_karot`
- `search_karot`
- `get_user_karots`
- `send_dm`
- `get_trends`

## 付费化准备

如果 Karotter 未来加入付费方案:

```python
client.set_paid_plan(
    "pro",
    entitlement_token="YOUR_TOKEN",
    extra_headers={"x-your-plan-header": "value"},
)
```

- `402` 会抛出 `PaidPlanRequiredError`
- 可通过 `client.payment_retry_hook` 在刷新付费凭证后重试

## 注意

- 这是非官方客户端，Karotter 侧变更可能导致行为变化。
- 请遵守平台条款与当地法律。
