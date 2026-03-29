# karokit (简体中文)

`karokit` 是面向 `karotter.com` 的非官方 scraper/API 封装，结构参考 `twikit`。

- 使用公开 Web 流程
- 不需要官方 API key
- 提供 `twikit` 风格方法（如 `create_tweet`、`search_tweet`）

## 为未来付费化准备

- 通过 `client.set_paid_plan(...)` 注入付费计划头
- `402` 会抛出 `PaidPlanRequiredError`
- 支持 `client.payment_retry_hook` 做令牌刷新后重试
