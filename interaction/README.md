# interaction：与 agent 交互

负责派发、续跑、一次性唤醒，以及交给总控验收的事件队列。模块间只调用 `bin/`。

| 命令 | 用法 |
|---|---|
| `bin/dispatch` | `<task> <workdir> [prompt文件] [--sandbox network或full --approved-by "用户原话或出处"] [--dry] [Codex exec 参数...]`；省略 prompt 时读该任务的 `prompt.md`。异步启动并检查活动；`--dry`（兼容 `DISPATCH_DRY=1`）只复制 prompt、记录命令，不启动 Codex 或写 registry |
| `bin/resume` | `<task> <session UUID> <cwd> <消息文件> [重试次数=6] [间隔秒=600] [--sandbox network或full --approved-by "用户原话或出处"] [--dry]`；同步执行 |
| `bin/wake` | `add <带时区ISO时间或HH:MM> <UUID或精确会话名> <prompt文件> [--name NAME] [--mode resume或queue]`；`list`；`cancel <id>` |
| `bin/github_poll` | 不带参数运行一次，从 registry 的 cwd 派生 GitHub 仓库，PR 变化进入 L1 复核队列 |
| `bin/event` | `add <L0或L1或L2> <source> <text>`；`from-agentconsole` 从 stdin 读一个 JSON；`list [--new]`；`ack <id>` |
| `bin/wait` | `<task> [轮询秒=30]`，等待当前运行结束，打印 last.md；退出码为运行结果（75 为重试耗尽）。此命令由总控同步维护 |
| `bin/status` | `[task]`，输出 registry JSONL；`links` 输出显式派发关系 JSONL；供其他模块只读查询，不访问内部文件 |

`wake` 的 HH:MM 按日本时间解释，过去的时分预约到明天；按分钟向上取整。resume 完成表示本轮退出，queue 完成只表示入队。`WAKE_DRY=1` 跳过 Codex，**仍会注册 launchd**。取消仅限未运行任务。

L0 只入队；L1 等总控验收；L2 入队后调用 `reporter/bin/notify alert`。通知失败返回非零，事件仍保留为 new。`ack` 幂等，改为 acked 并追加 acked_at；未知 id 报错。AgentConsole 的 dormant（cwd 出现在 registry）、idle_long、stale 为 L1，host_down 为 L2，其他为 L0；不写 human inbox。

默认数据根为本模块 `state/`，可用绝对路径 `PRTS_INTERACTION_STATE` 覆盖：

- `tasks/<task>/`：prompt.md、last.md、run.log / run-resume-N.log，保留既有布局。
- `wakes/<id>/`：spec.json、prompt.txt、运行日志和 last.md。
- `registry.jsonl`：t/name/event 等兼容记录；唯一写入实现是 `lib/registry`。
- `github_poll.jsonl`：PR 游标追加日志，格式和压缩规则见下节；不进 git。
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


## GitHub PR 轮询（R18 B0）

运行 `interaction/bin/github_poll` 扫描一次。通过 `lib/registry` 读取所有历史 cwd，查询各目录的 origin，识别 github.com 的 HTTPS、SSH（含 scp 写法）和 git URL，按 owner/repo 去重；目录失效、没有 origin 或非 GitHub 地址静默跳过。不另设仓库配置表。运行环境须有已认证且能读目标仓库的 `gh`、`git`、Python 3。

只列出 open PR，再逐个读取评论和 CI。首次发现只建立基线；以后 `updated_at`、评论数、CI 汇总任一改变，调用 `bin/event add L1 github_poll "owner/repo#123 …"`，同一次观测的多项变化合成一条事件。只有更新时间变化也会产生「有更新」。CI 合并 CheckRun 和 StatusContext：failure 优先于 pending，其后为 success；没有检查为 none，未识别值为 unknown；取消、超时和需要操作视为 failure，neutral/skipped 视为成功。这里的评论数来自 `gh pr view` 的 comments，不单独抓取 review 的行内评论。

默认游标路径 `interaction/state/github_poll.jsonl`，随 `PRTS_INTERACTION_STATE` 更改。每行如：

```json
{"key":"owner/repo#123","updated_at":"2026-11-14T00:00:00Z","comments":2,"ci":"pending","t":"2026-11-14T00:10:00+00:00"}
```

读、比较、事件入队和追加共用稳定锁 `.github_poll.lock`；并发运行遇锁跳过，留到下次。未变化不追加。成功列出的 open 集合中已消失的 PR 不再 view，追加 `{"key":"owner/repo#123","deleted":true,"t":"…"}` 清除游标，不产生关闭事件；重新打开视为首次发现。日志超过 1 MiB 时在同一锁内原子压缩，只保留每个仍被跟踪 PR 的最新游标，不保留历史或关闭项；因此大小随被跟踪 PR 数量而非轮询次数增长。

外部命令 stdin 关闭，每次超时 30 秒。仓库或单个 PR 失败写 stderr，继续其他仓库/PR，失败观测不推进游标。事件成功后才记录游标，失败下轮重试；若进程恰在入队成功后、保存游标前中断，可能重复事件（不保证 exactly-once）。列表上限显式设为 10000；触及上限时拒绝本仓库本轮结果并报错，避免把被截断的 PR 当作已关闭。

定时模板在 `config/launchd/com.prts.interaction-github-poll.plist`，每 600 秒一次。模板使用 `/Users/prts/PRTS` 的正式路径；用户合并后核对路径及 PATH，先创建 `interaction/state/` 和 `~/Library/LaunchAgents/`，再复制模板到 `~/Library/LaunchAgents/`，自行执行 `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.prts.interaction-github-poll.plist`。stdout/stderr 写 `interaction/state/github_poll.log`。本改动只提供模板，不自动安装。

离线测试：`python3 interaction/tests/test_github_poll.py`，使用临时 state、替身 git/gh 和真实的本地 event 入队。B0 只产生 L1 事件，等待复核；不登记订阅、不路由、不调用 queue/resume，也不唤醒 agent。真实 GitHub 和 launchd 安装不属于此测试覆盖。
