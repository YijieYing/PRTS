# interaction：与 agent 交互

负责派发、续跑、一次性唤醒，以及交给总控验收的事件队列。模块间通过 `bin/` 调用命令；结构化模型调用的共享 Python 原语见下文。

| 命令 | 用法 |
|---|---|
| `bin/dispatch` | `<task> <workdir> [prompt文件] [--worktree 分支 [--base ref]] [--sandbox network或full --approved-by "用户原话或出处"] [--dry] [Codex exec 参数...]`；省略 prompt 时读该任务的 `prompt.md`。异步启动并检查活动；`--dry`（兼容 `DISPATCH_DRY=1`）复制 prompt、记录命令（带 `--worktree` 时也准备工作树），不启动 Codex 或写 registry |
| `bin/worktrees` | `list` 或 `clean [--dry] [--all]`：列出工作树；只清理干净且已合并的工作树 |
| `bin/resume` | `<task> <session UUID> <cwd> <消息文件> [重试次数=6] [间隔秒=600] [--sandbox network或full --approved-by "用户原话或出处"] [--dry]`；同步执行 |
| `bin/wake` | `add <带时区ISO时间或HH:MM> <UUID或精确会话名> <prompt文件> [--name NAME] [--mode resume或queue]`；`list`；`cancel <id>` |
| `bin/github_poll` | 不带参数运行一次，从 registry 的 cwd 派生 GitHub 仓库，PR 变化进入 L1 复核队列 |
| `bin/event` | `add <L0或L1或L2> <source> <text>`；`from-agentconsole` 从 stdin 读一个 JSON；`list [--new]`；`ack <id>` |
| `bin/wait` | `<task> [轮询秒=30]`，等待当前运行结束，打印 last.md；退出码为运行结果（75 为重试耗尽）。此命令由总控同步维护 |
| `bin/status` | `[task]`，输出 registry JSONL；`links` 输出显式派发关系 JSONL；供其他模块只读查询，不访问内部文件 |

`wake` 的 HH:MM 按日本时间解释，过去的时分预约到明天；按分钟向上取整。resume 完成表示本轮退出，queue 完成只表示入队。`WAKE_DRY=1` 跳过 Codex，**仍会注册 launchd**。取消仅限未运行任务。

L0 只入队；L1 等总控验收；L2 入队后调用 `reporter/bin/notify alert`。通知失败返回非零，事件仍保留为 new。`ack` 幂等，改为 acked 并追加 acked_at；未知 id 报错。AgentConsole 的 dormant（cwd 出现在 registry）、idle_long、stale 为 L1，host_down 为 L2，其余已知类型为 L0；不写 human inbox。未知 `event` 类型走可选的模型慢速分支：`config/filter.toml` 的 `allowed_sources` 是事件 JSON 中 `source` 的白名单，默认空列表（关闭），未列入的来源仍为 L0、不调用模型；`timeout` 是单次调用超时秒数，默认 60。模型返回 L0/L1/L2 和理由；调用或校验失败退化为 L1，理由保留错误摘要。已知类型始终按原规则处理。`add` 仍直接采用调用方指定的级别。

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

共享原语：`lib/schema.py` 提供 `object_schema()` / `validate(value, spec)`；`lib/run_model.py` 的 `classify_with_model(prompt, schema, state_dir, *, run_bin=None, timeout=600)` 复用 `bin/run`，在调用方已创建的数据目录下暂存并清理 prompt/schema，校验 stdout JSON，失败抛异常。`run_bin` 优先，其次 `PRTS_RUN_MODEL`，默认本模块 `bin/run`；Ear 保留 `PULSE_RUN` 覆盖并自行定义 prompt/schema。此共享库是跨模块 Python 复用的显式例外。测试：`python3 interaction/tests/test_filter.py` 和 `python3 pulse/tests/test_ear.py`。

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

## Worktree 派发与清理

```sh
interaction/bin/dispatch feature-task /path/to/repo prompt.md --worktree feature/example
interaction/bin/dispatch other-task /path/to/repo prompt.md --worktree feature/other --base main
interaction/bin/worktrees list
interaction/bin/worktrees clean --dry
interaction/bin/worktrees clean
```

**worktree 由 dispatch 建，不要让 Codex 自己建 worktree。** 一次派发对应一个 worktree；多个分支分别派发。`workdir` 必须属于 Git 仓库，主检出和已有 worktree 均可。统一目录为 `~/.worktrees/<主检出目录名>/<分支名，斜杠换成短横线>`；`PRTS_WORKTREE_ROOT` 可覆盖根目录（测试使用临时目录）。同名仓库或分支路径映射冲突时拒绝，不覆盖目录。

已有分支如果已检出，复用其登记路径（可在统一目录之外）；否则新建 worktree。新分支默认先 `git fetch origin`，从 `origin` 默认分支创建；没有远程时从当前 HEAD 创建。只有其他远程而没有 origin 时须显式给 `--base`。`--base` 只用于新分支；显式指定时不 fetch。创建失败不启动 Codex。start 事件增加 `worktree: {path, branch, repo}`，repo 为主检出路径，cwd 为实际 worktree。沙箱策略不变。`--dry --worktree` 仍会准备 worktree，但不启动 Codex、不写 registry；命令日志记录实际 cwd。

dispatch 不自动清理。**调用方验收、合并之后，运行 `worktrees clean`。** list 输出路径、分支、仓库、改动、合并状态和 registry 中对应任务名。默认只扫描统一根目录中的登记工作树；`--all` 扩展到当前仓库、统一根目录与 registry 所发现仓库的全部登记工作树，始终保留主检出、锁定工作树和 detached HEAD。

clean 使用本地 `origin/<默认分支>` 引用判断提交包含关系（不自动 fetch；需要最新状态时先自行 fetch）；无远程时使用主检出 HEAD。也可通过 `gh pr list --head <分支> --state merged` 识别 squash 合并，限定默认目标分支并核对 PR 的 headRefOid 等于当前提交，防止误用同名旧 PR。gh 不可用或失败时只依赖提交包含关系。

有已跟踪改动或未跟踪文件就跳过；忽略文件不计入改动。未合并时说明原因，并在没有任何远程引用包含当前提交时标为「未推送」。通过检查后仅用 `git worktree remove`、`git branch -d`，不用强制删除。若 `-d` 拒绝（例如 squash 后无可证明已合并的 upstream），工作树已移除而分支保留，并打印原因。`--dry` 只读，不移除工作树或分支；运行中的任务应由调用方验收后再清理。

回归：`python3 interaction/tests/test_worktrees.py`，真实临时仓库和裸远程、Codex/gh 替身，子进程关闭 stdin；不清理真实工作树。

## thread 与订阅

事件可带 `--thread <key> --project <name> --kind <kind>`。规范字段是
`thread_key`、`project`、`kind`；项目 aliases 与 pulse 共用
`interaction/lib/projects.py`，未知名称保留，未归属为 null。
thread_key 约定：GitHub PR 为 `gh:<owner>/<repo>#<n>`；
项目为 `project:<规范名>`；连续录音为 `ear:<首段 capture_id>`。

登记：`subscribe add --project PRTS --to codex:<UUID>` 或
`subscribe add --thread gh:owner/repo#123 --to claude:local_<id>`；
`subscribe list`、`subscribe pause <id>`、`resume <id>`、`remove <id>`。
subscriptions.jsonl 只追加、取最新记录，修改带锁。有效订阅指未删除、未暂停；
不依赖 UI 在线状态，Codex 可排队到已有线程。多个目标可订阅同一项目。
成功的 worktree dispatch 从本次 last.md/run.log 的 PR URL 自动登记到该次
Codex UUID；不自动订阅整个 cwd 项目。需项目范围时手动用上述 --project 命令。
PR URL 提取不能证明链接一定是本次新建的 PR，报告引用的 PR 也可能匹配，
请用 list/remove 管理。绑定桌面 app Auto-fix 的 PR 不要登记 PRTS 订阅；
PRTS 无法判断 app 的 PR 绑定状态。
