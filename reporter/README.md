# reporter：报告与通知

负责生成内容并送达用户本人。模块间只调用 `bin/`；渠道实现位于 `lib/channels/`。

| 命令 | 用法 |
|---|---|
| `bin/notify` | `<log或wechat或alert> [--title T] (--text TEXT 或 --file PATH)` |
| `bin/notify outbox` | 查询 CodexBridge 微信发件箱 |
| `bin/report weekly [YYYY-MM-DD]` | 采集最近七天内容，通过 interaction dispatch 生成周报，再邮件投递、暂存微信短版 |
| `bin/report daily` | 校验 aquant 日报后暂存到微信发件箱；重复内容不再投递 |

notify 的 log 只追加 `state/out/notifications.jsonl`；wechat 调用 CodexBridge `weixin notify`；alert 同时尝试微信与 macOS 弹窗，任一失败返回非零。以 `--` 开头的旧调用等同 wechat，`outbox` 旧调用也保留。微信上下文过期时由 CodexBridge 暂存，等用户下一条消息后补发。

默认数据根为本模块 `state/`，可用绝对路径 `PRTS_REPORTER_STATE` 覆盖：

- `out/`：采集和写作中间文件、渲染 HTML、deliveries.jsonl、notifications.jsonl。
- `outbox/`：latest-wechat.txt、aquant-daily.txt 等，供用户的 CodexBridge `/auto` 任务读取。

`config/config.toml` 配置邮件收件人、微信暂存路径和 aquant 来源；设置 state 覆盖时，微信暂存也使用该根下的 outbox。周报全文仍按既有约定输出到 human/reports；不是本次迁移的数据格式变更。

日报来源约定：latest-wechat.txt 首行为 `aquant 日报 YYYY-MM-DD`、不超过 900 字，不含疑似 key；失败时调用 `interaction/bin/event add L1 aquant_daily ...`，不写 human inbox。邮件默认关闭。周报用 `interaction/bin/status` 查询执行结果，不读取对方 state。

隔离测试：`python3 interaction/tests/test_modules.py` 覆盖 log、旧通知接口、alert 路由和日报拒绝；外发渠道使用替身，不发送真实通知。
