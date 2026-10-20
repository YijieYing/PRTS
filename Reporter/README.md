# Reporter（PRTS 的“说”）
AgentConsole 负责看，Reporter 负责汇总、分级、投递。**只有 Reporter 对外发消息**，而且只发给用户本人。

流水线：`run_weekly.sh [YYYY-MM-DD]`
1. `collect.py`：确定性采集最近 7 天的数据，不用 LLM。包括 git 提交（本机和 lain）、AgentConsole 看到的活跃 session 及其 recap、新增的人类报告、PRTS 进度日志。按 `~/PRTS/human/projects.toml` 打上分类。
2. `compose.md`：只调用一次 `codex exec`，写出 `~/PRTS/human/reports/weekly-*.md` 和微信短版。
3. `deliver.py`：
   - 邮件：通过 Mail.app 用 iCloud 账户发给自己，并确认已进入“已发送”。
   - 微信：把短版放到 `outbox/latest-wechat.txt`，由用户在 CodexBridge 建的 `/auto` 任务读取后转发。原因是 CodexBridge 没有主动发消息的入口，回复必须带上用户最近一条消息里的 context token。

配置：`config.toml`。投递记录：`out/deliveries.jsonl`。
