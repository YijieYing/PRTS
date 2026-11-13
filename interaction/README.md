# interaction：与 agent 交互

负责派发、续跑、一次性唤醒，以及交给总控验收的事件队列。模块间只调用 `bin/`。

| 命令 | 用法 |
|---|---|
| `bin/dispatch` | `<task> <workdir> [prompt文件] [--sandbox network或full --approved-by "用户原话或出处"] [--dry] [Codex exec 参数...]`；省略 prompt 时读该任务的 `prompt.md`。异步启动并检查活动；`--dry`（兼容 `DISPATCH_DRY=1`）只复制 prompt、记录命令，不启动 Codex 或写 registry |
| `bin/resume` | `<task> <session UUID> <cwd> <消息文件> [重试次数=6] [间隔秒=600] [--sandbox network或full --approved-by "用户原话或出处"] [--dry]`；同步执行 |
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

`lib/codex` 统一关闭 stdin，默认授予 workspace-write 和仓库 git 目录权限、禁用命令联网，重试 at capacity。dispatch 使用 `CODEX_TRIES` / `CODEX_GAP`（默认 6 / 600），wake 使用 `WAKE_TRIES` / `WAKE_GAP`。容量耗尽返回 75。精确会话名查询依赖 Codex 内部 SQLite 格式，集中在适配层；优先传 UUID。`lib/wake_state` 独占内部状态动作，`bin/wake` 不接受 `_claim` 等内部子命令。

沙盒放宽（R5）：仅 `dispatch` / `resume` 显式指定 `--sandbox network` 或 `--sandbox full` 时生效，每次都必须同时提供非空 `--approved-by "用户原话或出处"`，缺少或只有空白则拒绝，包括 dry-run。批准说明是调用者提供的审计依据，必须来自用户实际授权；工具不会自行取得或验证授权。resume 不继承上轮的放宽和批准。

- `network`：`-c 'sandbox_mode="workspace-write"' -c sandbox_workspace_write.network_access=true`，保留工作区写入范围。
- `full`：`-c 'sandbox_mode="danger-full-access"'`，取消 Codex 沙盒限制。
- 默认：`workspace-write`、`sandbox_workspace_write.network_access=false`；所有模式仍用 `approval_policy="never"`，不在无人值守运行中弹批准提示。
- `start` 事件记录 `sandbox`（`workspace-write` / `network` / `full`）和 `approved_by`（默认 `null`，放宽时原样保留说明）。dry-run 只写命令日志，不执行 Codex、不写 registry；dispatch 写 `run.log`，resume 写 `run-resume-1.log`。
- 原始 Codex 参数和 `CODEX_TOP` 不接受沙盒、批准策略、权限配置及 profile 覆盖；使用上述显式接口。模型及推理配置仍可透传。

仅预览的示例（批准文字需替换成真实用户授权依据）：

```sh
interaction/bin/dispatch example /path/to/repo prompt.md --sandbox network --approved-by "用户授权出处" --dry
interaction/bin/resume example SESSION_UUID /path/to/repo message.md 6 600 --sandbox full --approved-by "用户授权出处" --dry
```

配置依据：[OpenAI 沙盒与网络文档](https://learn.chatgpt.com/docs/agent-approvals-security)。2026-11-13 核对本机 `codex-cli 0.155.1` 的 `exec --help`、`exec resume --help`，并在临时 `CODEX_HOME` 下用 `codex debug prompt-input` 确认 network 配置生成了联网已启用的 workspace-write 权限描述；没有启动放宽沙盒的真实任务。回归测试使用替身验证命令、拒绝路径及 registry，不代表已验证 Unity 构建或实际 socket / 联网行为。

旧 ops 符号链接调用仍有效，属 legacy，待总控在过渡期结束删除。测试：`bash interaction/tests/test_wake.sh` 和 `python3 interaction/tests/test_modules.py`；均使用临时 state、HOME 和替身命令，不触及真实 LaunchAgents、微信或 Codex 会话。

派发关系：dispatch / resume 的 `start` 事件追加可选 `caller: {"kind":"claude"|"codex","id":"…"}`，优先取非空 `CLAUDE_CODE_SESSION_ID`，其次 `CODEX_THREAD_ID`，都没有则省略。dispatch 在启动确认或快速退出时从 run.log 的 `session id: <uuid>` 追加 `thread` 事件；resume 直接记录传入 thread。原有事件字段保留，registry 仍只由 `lib/registry` 追加。

`bin/status links` 每行输出 `{"child":"Codex UUID","parent":"caller id","parent_kind":"claude"或"codex","task":"任务名"}`。按任务最近一次 start 配对其后的 thread；缺 caller 或 thread 就不输出，不沿用上次运行的 caller，也不推测历史关系。

旧任务的回填（2026-11-09，`maintenance/backfill_links.py`）：追加了 `thread` 事件（取自 run.log）和 `caller` 事件（取自 Claude 对话记录里点名这个任务的 dispatch/resume 命令，按记录自带的 sessionId 计；有多个 session 点名同一个任务的跳过）。`status links` 也读 `caller` 事件，事件带 `backfill` 字段注明来源。

`bin/run <prompt文件> [--output-schema <JSON Schema文件>] [-o <最终回复文件>]`：一次同步 `codex exec`，只读沙盒、提示词经 stdin 传入（避免长提示词超过命令行参数上限）、不重试、不写 registry，最终回复打印到 stdout，诊断到 stderr，失败传播退出码。实现复用 `lib/codex`，已有 dispatch/resume 权限不变。

同步适配回归：`python3 interaction/tests/test_run.py`（替身验证只读参数、schema/output 转发、提示词经 stdin、超长提示词和失败退出码）。参数依据本机 `codex exec --help` 及 [OpenAI 非交互模式文档](https://learn.chatgpt.com/docs/non-interactive-mode)。
