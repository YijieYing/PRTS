# reporter：报告与通知

负责生成内容并送达用户本人。模块间只调用 `bin/`；渠道实现位于 `lib/channels/`。

| 命令 | 用法 |
|---|---|
| `bin/notify` | `<log或wechat或phone或alert或note> [--title T] (--text TEXT 或 --file PATH) [--url U] [--folder F]`；`--url` 是点开 Bark 推送时打开的链接；`note` 把全文写进 Apple 备忘录文件夹 F（默认 PRTS），同名替换正文，只动这个文件夹 |
| `bin/notify outbox` | 查询 CodexBridge 微信发件箱 |
| `bin/report weekly [YYYY-MM-DD]` | 采集最近七天内容，通过 interaction dispatch 生成周报，再推送手机摘要、邮件投递，并默认暂存微信短版 |
| `bin/report daily` | 校验 aquant 日报后暂存到微信发件箱；重复内容不再投递 |

notify 的 log 只追加 `state/out/notifications.jsonl`；wechat 调用 CodexBridge `weixin notify`；phone 调用 Bark；alert 同时尝试 Bark 与 macOS 弹窗，任一失败返回非零；note 调 `lib/channels/notes`，用 osascript 写 Apple 备忘录（首次需用户允许自动化访问备忘录），只新建或更新给定文件夹里同名的那一条，不读、不删其他备忘录。以 `--` 开头的旧调用等同 wechat，`outbox` 旧调用也保留。微信上下文过期时由 CodexBridge 暂存，等用户下一条消息后补发。

默认数据根为本模块 `state/`，可用绝对路径 `PRTS_REPORTER_STATE` 覆盖：

- `out/`：采集和写作中间文件、渲染 HTML、deliveries.jsonl、notifications.jsonl。
- `outbox/`：latest-wechat.txt、aquant-daily.txt 等，供用户的 CodexBridge `/auto` 任务读取。

`config/config.toml` 配置邮件收件人、微信暂存路径和 aquant 来源；设置 state 覆盖时，微信暂存也使用该根下的 outbox。周报全文仍按既有约定输出到 human/reports。

周报生成后调用 `bin/notify phone`：短版首行是本周最重要的一件事，作为标题；正文最多 4 行摘要，另加一行全文绝对路径（总共不超过 5 行）。写作草稿放在 `state/out/wechat-日期.txt`。`weekly_outbox = true` 默认继续复制短版到 `wechat_outbox`，供现有 CodexBridge `/auto` 读取；关闭 `/auto` 后可设为 `false`，周报不再写 outbox，但保留已有文件和 `reporter/outbox` 兼容链接，也不影响日报。手机推送失败会记录到 deliveries.jsonl 并返回非零；已生成的全文和已暂存的 outbox 保留。内部 `deliver.py --email-only` 仍只处理邮件，供日报使用。

日报来源约定：latest-wechat.txt 首行为 `aquant 日报 YYYY-MM-DD`、不超过 900 字，不含疑似 key；失败时调用 `interaction/bin/event add L1 aquant_daily ...`，不写 human inbox。日报邮件默认关闭，周报仍投递邮件。周报用 `interaction/bin/status` 查询执行结果，不读取对方 state。

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
- `next [--max N]` 按 blocking → timely → soon → whenever、组内创建时间排序，仅预览，不记送达。
  最多取配置中的批量上限；`--max` 可进一步缩小。已到期问题不参与 next/due/render。
- `due --channel claude [--now ISO]` 先调用同仓库 `pulse/bin/pulse now`（关闭 stdin，5 秒超时）。
  quiet 为 true 时只推 blocking；缺失、失败、超时或无有效 quiet 时按非 quiet 处理。
  blocking 距上次送达至少 30 分钟；timely 在下一次 due 时推送一次，不重复（quiet 时暂缓），pulse 的杂务提醒用它；soon 到每日汇总时间后每天最多一次；whenever 不推送。
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
`test_weekly.py` 覆盖默认双发、关闭 outbox、摘要行数、推送失败保留报告和 outbox、email-only 以及 weekly 完整命令链；Bark、WeChat、邮件和派发均使用替身，不真推送。

## 待办：`bin/todo`（2026-11-13）
- 用户自己的待办放在 Apple 提醒事项的「PRTS」列表，会同步到 iPhone；带日期的也会出现在日历里。
- `todo add "<标题>" [--notes N] [--due YYYY-MM-DD[THH:MM]]`、`todo list [--all]`（每行一个 JSON）、`todo done <id>`。只标记完成，从不删除。
- 只放用户本人要做的事。agent 的工作进 `ROADMAP.md` 或派发任务。
- 通过 osascript 操作。这台 Mac 已经允许访问提醒事项，不需要再授权。

## 送达（2026-11-12）
- **每小时提醒：`bin/remind`，由 launchd 运行**（`config/launchd/com.prts.reporter-remind.plist`，全天每小时第 7 分钟）。
  - 依次运行 `pulse ear sync --no-notify`、`recap --auto --synced`、`pulse check`、`ask expire`，非 quiet 时再运行 `ask due --channel bark`。
  - 有待推送的问题，才用 `notify alert` 推到手机（Bark）和电脑（macOS 通知）；没有就什么都不发。
  - 推送标题直接用第一条问题本身，多条时注明「共 N 条」（11-13 用户反馈：「PRTS 提醒」这种标题让人不想点开）。
  - Ear 每轮只同步一次；同步失败只记日志，不中断提醒。quiet 时段暂停所有问题推送（包括 blocking），但日报照常写备忘录、照常推送。
  - 日志写在 `state/out/remind.log`。
  - 用户在任意 Claude session 里回复「Q12 …」，通常是 PRTS 总控（手机 Claude app 里也能回），由那个 session 运行 `ask reply` 记录。
  - 为什么不用 Claude 定时任务：每次运行都会开一个 session，即使没东西要问，跑完 app 也会弹「完成」通知（11-12 用户反馈）。原来的 `prts-reminders` 任务已暂停，prompt 留在 `config/claude-tasks/prts-reminders.md` 备查。
  - 安装：`launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.prts.reporter-remind.plist`。plist 要先从 config 复制过去。这一步由用户执行，agent 的权限检查不允许自动装开机常驻任务。
- **每日回顾**：`bin/recap [YYYY-MM-DD]` 先同步 Ear，再生成指定逻辑日（省略日期为当前逻辑日）的回顾。同名「YYYY-MM-DD 回顾」备忘录正文会替换，全文落在 `pulse/state/days/YYYY-MM-DD.md`。全文不受 4000 字符限制；`notify alert --url mobilenotes://` 仍只取去掉空行、小节标题后的前 8 行，标题仍是总计行。
  - 每小时 remind 调用 `recap --auto --synced`：最近一个已完成逻辑日未发则兜底发送；当前逻辑日开始满 18 小时且连续空闲达到 `[recap].idle_minutes`（pulse 配置，默认 90）后可提前结束。默认日界 05:00，所以提前判断从 23:00 开始，凌晨 03:07 生成的日期仍属于前一日；05:07 无论活动是否停止，都补发前一日。不会遍历补发更早历史。
  - 空闲依据 `pulse recap-status`：Computer History 没有活跃分钟，Claude/Codex 没有用户消息，ChatGPT 没有会话访问（现有来源只有浏览历史，作为用户交互的保守代理，不能核实实际发言），Ear 没有最近转写句子。后台 agent 输出不算活动；短句和未分诊句子也会阻止结束。Ear 同步失败、证据读取异常时不提前判定，05:00 兜底仍发送，并沿用 Ear 数据缺失说明。旧 Ear 来源不能提供逐句静默证明，仅走兜底。
  - `state/recap-sent.json`（支持 `PRTS_REPORTER_STATE`）在文件锁内记录各日期的 note/alert/sent。自动发送跳过已完成日期；部分失败只重试未成功的渠道，手动重跑明确允许重新写入和推送。通知服务没有事务确认，外部送达成功至本地登记前崩溃仍可能重发；Bark/macOS 部分成功亦无法精确去重。
  - `bin/recap --dry [YYYY-MM-DD]` 是严格只读预览：使用现存同日分类 JSON 与 Ear 缓存重新渲染到 stdout，不同步、不调用模型、不写 state、不写备忘录、不推送；无同日 JSON 时报错。用于检查完整时间线，不能证明最新远端录音已同步。
  - 自动运行日志在 `state/out/remind.log`。旧的 23:40 recap 模板已删除；旧 Claude 任务 `prts-daily-recap` 也应继续暂停，`config/claude-tasks/` 仅为历史备查。

用户需要卸载已装的 `com.prts.reporter-recap`，并重新安装 remind 模板才会采用全天排程。以下命令由用户执行，本次代码变更不操作已安装任务：

```sh
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.prts.reporter-recap.plist
rm -f ~/Library/LaunchAgents/com.prts.reporter-recap.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.prts.reporter-remind.plist
cp ~/PRTS/reporter/config/launchd/com.prts.reporter-remind.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.prts.reporter-remind.plist
```

未加载的任务执行 bootout 可能提示找不到服务；仍可继续复制和 bootstrap。

### 手机渠道：Bark（2026-11-12）
- `notify phone` 用 Bark 推到 iPhone；`notify alert` = Bark + macOS 通知（之前是微信 + macOS 通知）。`notify wechat` 仍然保留。
- Bark 正文按 UTF-8 字节截到约 2.6 KB（APNs 整个负载上限 4 KB），在行边界截断并注明「已截断，全文见 Mac 通知」（Mac 通知同样截断；日报全文见备忘录「PRTS 日报」）。11-13 每日回顾约 7 KB，未截断时 Bark 返回 413。
- 设备 key 在 `config/secrets.toml`，权限 600，已加入 `.gitignore`，不进 git。
- 为什么不用 Claude app 推送：定时任务的 session 不连 Remote Control，也不能为它打开，PushNotification 到不了手机（11-12 实测）。
