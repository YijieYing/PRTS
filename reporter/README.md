# reporter（PRTS 的“说”）
AgentConsole 负责看，Reporter 负责汇总、分级、投递。**只有 Reporter 对外发消息**，而且只发给用户本人。

流水线：`run_weekly.sh [YYYY-MM-DD]`
1. `collect.py`：确定性采集最近 7 天的数据，不用 LLM。包括 git 提交（本机和 lain）、AgentConsole 看到的活跃 session 及其 recap、新增的人类报告、PRTS 进度日志。按 `~/PRTS/human/projects.toml` 打上分类。
2. `compose.md`：只调用一次 `codex exec`，写出 `~/PRTS/human/reports/weekly-*.md` 和微信短版。
3. `deliver.py`：
   - 邮件：通过 Mail.app 用 iCloud 账户发给自己，并确认已进入“已发送”。
   - 微信：把短版放到 `outbox/latest-wechat.txt`，由用户在 CodexBridge 建的 `/auto` 任务读取后转发。这是 10-30 之前的做法：当时 CodexBridge 没有主动发消息的入口。现在可以用 `~/PRTS/ops/wechat-notify.sh --file <文件>` 直接推送（token 过期时会等用户下一条消息后补发），Reporter 还没改用它。

配置：`config.toml`。投递记录：`out/deliveries.jsonl`。

## aquant 每日渠道（`aquant_daily.py`）
- 约定：aquant 每个交易日收盘后写 `~/Projects/aquant/outputs/daily/latest-wechat.txt`（首行“aquant 日报 YYYY-MM-DD”，不超过 900 字）和 `YYYY-MM-DD.md` 全文。
- 触发：launchd `com.prts.reporter-aquant-daily` 用 WatchPaths 同时监视 `daily/` 目录和文件本身（rsync 用临时文件加 rename 的方式替换，单独监视文件可能在第一次替换后失效），并每 10 分钟兜底轮询一次。脚本幂等。和 ET 时区及夏令时无关。
- 上游：日报在 lain 上生成（`aquant-multiday.timer`），由 Mac 上的 `com.aquant.daily-pull` 每 10 分钟用 rsync 拉过来。第一份预计在 10/22 05:40–05:50 JST 到达。
- 校验通过后，原子写入 `outbox/aquant-daily.txt`，由用户的 CodexBridge `/auto` 任务在 07:30 JST 转发到微信。不通过（缺日期、超长、含疑似 key）就不转发，并在 `~/PRTS/human/inbox.md` 里记一条。
- 邮件默认关闭（`config.toml` 中的 `aquant_daily_email`）。
