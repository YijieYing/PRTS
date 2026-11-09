# interaction：与 agent 交互

负责派发、续跑、一次性唤醒，以及交给总控验收的事件队列。模块间只调用 `bin/`。

| 命令 | 用法 |
|---|---|
| `bin/dispatch` | `<task> <workdir> [prompt文件] [Codex exec 参数...]`；省略 prompt 时读该任务的 `prompt.md`。异步启动并检查活动；`DISPATCH_DRY=1` 只复制 prompt、记录命令，不启动 Codex 或写 registry |
| `bin/resume` | `<task> <session UUID> <cwd> <消息文件> [重试次数=6] [间隔秒=600]`；同步执行 |
| `bin/wake` | `add <带时区ISO时间或HH:MM> <UUID或精确会话名> <prompt文件> [--name NAME] [--mode resume或queue]`；`list`；`cancel <id>` |
| `bin/event` | `add <L0或L1或L2> <source> <text>`；`from-agentconsole` 从 stdin 读一个 JSON；`list [--new]`；`ack <id>` |
| `bin/wait` | `<task> [轮询秒=30]`，等待当前运行结束，打印 last.md；退出码为运行结果（75 为重试耗尽）。此命令由总控同步维护 |
| `bin/status` | `[task]`，输出 registry JSONL；`links` 输出显式派发关系 JSONL；供其他模块只读查询，不访问内部文件 |

`wake` 的 HH:MM 按日本时间解释，过去的时分预约到明天；按分钟向上取整。resume 完成表示本轮退出，queue 完成只表示入队。`WAKE_DRY=1` 跳过 Codex，**仍会注册 launchd**。取消仅限未运行任务。

L0 只入队；L1 等总控验收；L2 入队后调用 `reporter/bin/notify alert`。通知失败返回非零，事件仍保留为 new。`ack` 幂等，改为 acked 并追加 acked_at；未知 id 报错。AgentConsole 的 dormant（cwd 出现在 registry）、idle_long、stale 为 L1，host_down 为 L2，其他为 L0；不写 human inbox。

默认数据根为本模块 `state/`，可用绝对路径 `PRTS_INTERACTION_STATE` 覆盖：

- `tasks/<task>/`：prompt.md、last.md、run.log / run-resume-N.log，保留既有布局。
- `wakes/<id>/`：spec.json、prompt.txt、运行日志和 last.md。
- `registry.jsonl`：t/name/event 等兼容记录；唯一写入实现是 `lib/registry`。
- `events/queue.jsonl`：id/t/level/source/text/status；队列写入与 ack 共用锁。

`lib/codex` 统一关闭 stdin、授予 workspace-write 和仓库 git 目录权限、重试 at capacity。dispatch 使用 `CODEX_TRIES` / `CODEX_GAP`（默认 6 / 600），wake 使用 `WAKE_TRIES` / `WAKE_GAP`。容量耗尽返回 75。精确会话名查询依赖 Codex 内部 SQLite 格式，集中在适配层；优先传 UUID。`lib/wake_state` 独占内部状态动作，`bin/wake` 不接受 `_claim` 等内部子命令。

旧 ops 符号链接调用仍有效，属 legacy，待总控在过渡期结束删除。测试：`bash interaction/tests/test_wake.sh` 和 `python3 interaction/tests/test_modules.py`；均使用临时 state、HOME 和替身命令，不触及真实 LaunchAgents、微信或 Codex 会话。

派发关系：dispatch / resume 的 `start` 事件追加可选 `caller: {"kind":"claude"|"codex","id":"…"}`，优先取非空 `CLAUDE_CODE_SESSION_ID`，其次 `CODEX_THREAD_ID`，都没有则省略。dispatch 在启动确认或快速退出时从 run.log 的 `session id: <uuid>` 追加 `thread` 事件；resume 直接记录传入 thread。原有事件字段保留，registry 仍只由 `lib/registry` 追加。

`bin/status links` 每行输出 `{"child":"Codex UUID","parent":"caller id","parent_kind":"claude"或"codex","task":"任务名"}`。按任务最近一次 start 配对其后的 thread；缺 caller 或 thread 就不输出，不沿用上次运行的 caller，也不推测历史关系。本次不回填旧日志。
