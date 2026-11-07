已完成，提交到当前 `main` 分支，未推送：

- `9a3d20a`：registry、Codex 适配层、wake 内部状态重构。
- `cd26053`：notify 分级与渠道拆分。
- `14c714a`：事件队列及跨模块接口迁移。
- `dadb7a9`：隔离测试。
- `448e454`：模块中文 README。

未修改或提交真实 state、NatureCalls 任务数据及禁改文档；总控同时产生的改动保留原状。

**逐文件变化**

| 文件 | 变化 |
|---|---|
| `interaction/lib/registry` | 新增唯一 registry 写入实现、加锁读取及 cwd 查询 |
| `interaction/lib/codex` | 统一执行、关闭 stdin、git 写权限、容量重试；集中 SQLite 会话名解析 |
| `interaction/lib/wake_state` | 承接预约和内部状态动作 |
| `interaction/lib/wake_fire` | 调用 wake_state 和 codex |
| `interaction/bin/dispatch` | 使用适配层，新增 dry，确保 start 先于 exit |
| `interaction/bin/resume` | 使用适配层，保留旧参数 |
| `interaction/bin/wake` | 公开入口仅接受 add/list/cancel |
| `interaction/bin/status` | 新增只读 registry 查询接口 |
| `interaction/bin/event` | 新增 add/list/ack/from-agentconsole；L2 调用 notify |
| `interaction/tests/test_wake.sh` | 更新布局，全部使用临时目录及替身 |
| `interaction/tests/test_modules.py` | 新增 9 项隔离测试 |
| `reporter/bin/notify` | log/wechat/alert 分级，兼容旧接口 |
| `reporter/lib/channels/log` | 加锁追加 notifications.jsonl |
| `reporter/lib/channels/wechat` | 封装原 CodexBridge CLI |
| `reporter/lib/channels/macos` | 参数化调用 osascript |
| `reporter/lib/aquant_daily.py` | 拒绝原因进入事件队列，支持 state 覆盖 |
| `reporter/lib/deliver.py` | 支持 state 覆盖，修正 HTML 输出目录 |
| `reporter/lib/weekly.sh` | 通过 status 查询结果，支持 state 覆盖 |
| `ops/on_event.sh` | 转调 event from-agentconsole |
| `ops/unpushed_reminder.sh` | 通过 event 入队和查询每日去重 |
| 两个模块 `README.md` | 更新命令、数据布局、兼容行为和测试说明 |

规范术语采用 `registry`、`codex`、`wake_state`、`event`、`channels`；移除了各调用方重复的 registry 写入和 Codex 执行实现。

**接口兼容**

旧 dispatch、resume、wake 公开调用和 notify 无级别/outbox 调用仍可用。新增 `event`、`status`、`DISPATCH_DRY=1`、`PRTS_INTERACTION_STATE`、`PRTS_REPORTER_STATE`。`wake _claim/_fields/_finish/_capacity` 不再是公开入口。既有数据未迁移或改格式。

**验证过**

`python3 interaction/tests/test_modules.py` 完整输出：

```text
test_agentconsole (__main__.Modules.test_agentconsole) ... ok
test_alert_failure_retains_event (__main__.Modules.test_alert_failure_retains_event) ... ok
test_daily_rejection (__main__.Modules.test_daily_rejection) ... ok
test_dispatch_dry_and_resume (__main__.Modules.test_dispatch_dry_and_resume) ... ok
test_dispatch_real_stub (__main__.Modules.test_dispatch_real_stub) ... ok
test_event_add_list_ack (__main__.Modules.test_event_add_list_ack) ... ok
test_notify (__main__.Modules.test_notify) ... ok
test_registry (__main__.Modules.test_registry) ... ok
test_wake_private_commands (__main__.Modules.test_wake_private_commands) ... ok

----------------------------------------------------------------------
Ran 9 tests in 10.430s

OK
```

`bash interaction/tests/test_wake.sh` 完整输出：

```text
20261107T2318-capacity	2026-11-07T23:18:00+09:00	failed	resume	11111111-1111-4111-8111-111111111111	rc=75
20261107T2318-queue	2026-11-07T23:18:00+09:00	done	queue	11111111-1111-4111-8111-111111111111	rc=0
20261107T2318-real	2026-11-07T23:18:00+09:00	done	resume	11111111-1111-4111-8111-111111111111	rc=0
20261107T2318-dry	2026-11-07T23:18:00+09:00	done	resume	11111111-1111-4111-8111-111111111111	rc=0
20261108T2312-tomorrow	2026-11-08T23:12:00+09:00	cancelled	resume	11111111-1111-4111-8111-111111111111	rc=-
20261107T2318-iso	2026-11-07T23:18:00+09:00	cancelled	resume	11111111-1111-4111-8111-111111111111	rc=-
PASS: time, past rejection, alias dedup, cancel, dry, delivery, injection, one-shot, capacity
```

修改过的 shell 脚本通过 `bash -n` / `zsh -n`，指定修改范围通过 `git diff --check`，均无输出。

**试过与未核实**

上述执行均为临时目录隔离测试；没有试发真实微信、弹窗、创建真实 LaunchAgent 或启动真实 Codex 会话。这些外部系统的端到端行为**未核实**。

功能项没有遗留；两点交由总控处理：

- 受保护的 [NOTES.md](/Users/prts/PRTS/interaction/state/wakes/NOTES.md:3) 仍含旧路径，第 41 行仍描述 stdin 传 prompt；未修改。
- 总控并行新增的 `interaction/bin/wait` 未纳入本次实现和测试；README 已说明其当前用途。