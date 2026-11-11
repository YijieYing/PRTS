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

## ask：问题队列

`bin/ask` 管理提问、送达和回答，当前状态从只追加的 `state/questions.jsonl` 折叠得出。
沿用 `PRTS_REPORTER_STATE`；事件和并发锁 `questions.lock` 都不进 git。
调用者先确认「查不到、值得问、有默认方案」，再入队；pulse 的杂务提醒也使用此接口。

```sh
reporter/bin/ask add "要把部署排查交给 agent 吗？" --why "杂务持续过久" \
  --default "暂不处理" --urgency soon --source pulse --dedupe chore:deploy --project PRTS
reporter/bin/ask list --open --json
reporter/bin/ask next --max 3
reporter/bin/ask due --channel claude
reporter/bin/ask reply "Q12 交给 agent"
reporter/bin/ask answer Q12 "交给 agent" --via session
reporter/bin/ask close Q12 superseded
reporter/bin/ask expire --now 2026-11-13T18:00:00+09:00
reporter/bin/ask render
reporter/bin/ask wait Q12 --poll 30
```

- `add` 打印递增的 `Q1` 等编号；同 dedupe 的未关闭问题返回已有编号，不修改原问题。
  必填 question、why、default、urgency、source、dedupe；可选 `--expires ISO`、`--project P`。
- `list [--open] [--json]` 默认列出全部；JSON 为包含状态、送达历史、答案的数组。
- `next [--max N]` 按 blocking → soon → whenever、组内创建时间排序，仅预览，不记送达。
  最多取配置中的批量上限；`--max` 可进一步缩小。已到期问题不参与 next/due/render。
- `due --channel claude [--now ISO]` 先调用同仓库 `pulse/bin/pulse now`（关闭 stdin，5 秒超时）。
  quiet 为 true 时只推 blocking；缺失、失败、超时或无有效 quiet 时按非 quiet 处理。
  blocking 距上次送达至少 30 分钟，soon 到每日汇总时间后每天最多一次，whenever 不推送。
  所有渠道合并计数；每批最多 3 条，含 blocking 的批次默认每天最多 6 次。
  上限用尽仍可发送 soon。当天未装入一批的 soon 可在下一次调用时送出。
  配置在 `config/questions.toml`：`max_batch`、`blocking_daily_limit`、
  `blocking_interval_minutes`、`soon_time`（默认 18:00）。日界和汇总时间采用运行机器本地时区；
  ISO 时间带偏移时先转本地时间，不带偏移时视为本地时间。
  返回文字就已记录 delivered；没有待推送内容时 stdout 为空，退出 0。
  它不调用外发渠道，也不安装定时任务。Claude 定时 session 负责展示文字和提交回答。
- 用户直接回复「Q12 你的答案」；session 原样交给 `reply "原话"`，每次处理一条，via 为 claude。
  「Q12 你定」关闭为 delegated、记录 default_used，并打印默认方案供调用者执行；
  「Q12 以后」关闭为 deferred；「Q12 别问」关闭为 rejected。deferred 不自动重新排期。
- `answer Q12 "答案" --via session|file|wechat|claude` 记录答案并关闭为 answered。
  普通关闭的问题不能再回答；使用过 default 的问题允许事后更正，同时记录 default_ok。
  重复提交相同的普通答案、重复 close 同一 outcome 不追加事件。
- `close Q12 <outcome>` 可用 deferred、delegated、rejected、expired_unseen、expired_seen、superseded；
  answered 必须通过 answer 提供答案。`expire [--now ISO]` 关闭到期问题：有 opened 为
  expired_seen，其余均为 expired_unseen（包括从未送达）；打印本次关闭的编号。
- `opened Q12 --channel claude` 仅在渠道确实知道已打开时调用，且必须已有送达记录。
  `default-used Q12` 记录调用者已采用默认方案；`default-ok Q12 true|false` 记录事后反馈。
  不因为没人回复就自动执行 default，也不猜测用户已经打开或认可默认方案。
- `wait Q12 [--poll 30]` 可由提问 session 放在后台运行；答案出现或问题关闭后退出 0，
  有答案则打印答案，无答案的关闭则输出空。未知编号/无效参数退出 2，中断退出 130。
- `render` 只打印供 `human/questions.md` 使用的视图和回答说明，不写 human，也不监视文件。
  文件回答由 session 读取后调用 `answer --via file` 导入。

事件均有 `qid`、`t`、`event`：created 包含提问字段；delivered 包含 channel、batch_size、batch_id；
opened 包含 channel；answered 包含 answer、via、latency_s（首次送达至回答的秒数，未送达为 null）；
closed 包含 outcome；default_used 包含 value；default_ok 包含布尔 ok（更改默认方案时为 false）。
不把 delegated 当作用户明确回答，也不为它虚构回答用时。队列读写在文件锁内完成，避免并发编号、去重和送达竞态；
损坏的事件流报错而不跳过或重写历史。

隔离验证：`python3 -m unittest discover -s reporter/tests -v`；现有模块回归：
`python3 interaction/tests/test_modules.py`。问题队列测试复制 bin/lib/config 到临时目录，
使用临时 `PRTS_REPORTER_STATE` 和替身 pulse，所有测试子进程关闭 stdin。
