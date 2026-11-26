# interaction：与 agent 交互

负责派发、续跑、一次性唤醒，以及交给总控验收的事件队列。模块间通过 `bin/` 调用命令；结构化模型调用的共享 Python 原语见下文。

| 命令 | 用法 |
|---|---|
| `bin/dispatch` | `<task> <workdir> [prompt文件] [--worktree 分支 [--base ref]] [--roadmap 工程:编号] [--sandbox network或full --approved-by "用户原话或出处"] [--dry] [Codex exec 参数...]`；省略 prompt 时读该任务的 `prompt.md`。异步启动并检查活动；`--dry`（兼容 `DISPATCH_DRY=1`）复制 prompt、记录命令（带 `--worktree` 时也准备工作树），不启动 Codex 或写 registry |
| `bin/roadmap` | `list [工程] [--json]`；`mark 工程 编号 状态 [--evidence 文本]`：解析或提交单条状态与证据 |
| `bin/worktrees` | `list`、`auto [--dry] [--daily] [--now] [--repo PATH...]` 或 `clean [--dry] [--all]`：安全清理工作树 |
| `bin/resume` | `<task> <session UUID> <cwd> <消息文件> [重试次数=6] [间隔秒=600] [--sandbox network或full --approved-by "用户原话或出处"] [--dry]`；同步执行 |
| `bin/wake` | `add <带时区ISO时间或HH:MM> <UUID或精确会话名> <prompt文件> [--name NAME] [--mode resume或queue]`；`list`；`cancel <id>` |
| `bin/github_poll` | 不带参数运行一次，从 registry 的 cwd 派生 GitHub 仓库，PR 变化进入 L1 复核队列 |
| `bin/event` | `add <L0或L1或L2> <source> <text> [--thread KEY] [--project NAME] [--kind KIND] [--id ID]`；`from-agentconsole` 从 stdin 读一个 JSON；`list [--new]`；`ack <id>` |
| `bin/wait` | `<task> [轮询秒=30]`，等待当前运行结束，打印 last.md；退出码为运行结果（75 为重试耗尽）。此命令由总控同步维护 |
| `bin/status` | `[task]`，输出 registry JSONL；`links` 输出显式派发关系 JSONL；`threads [--json]` 输出主线投影；供其他模块只读查询，不访问内部文件 |
| `bin/usage-audit` | `[--weeks N] [--json]`，只读盘点用户功能每周使用次数和连续未用周数；连续至少两周未用标为候选，不删除或停用功能。只有发送记录、没有「用户用了」信号的功能（日报、DDL 提醒、todo、AgentConsole、tokens）标「测不到，不判」，不当候选。每周日由 Claude 定时任务「清理左边栏与功能盘点」运行，有候选就用 `ask add` 入队一个 soon 问题；「固定学习时段」按周数 `study log` 条数，至少跑过两周才判断 |

`wake` 的 HH:MM 按日本时间解释，过去的时分预约到明天；按分钟向上取整。resume 完成表示本轮退出，queue 完成只表示入队。`WAKE_DRY=1` 跳过 Codex，**仍会注册 launchd**。取消仅限未运行任务。

L0 只入队；L1 等总控验收；L2 入队后调用 `reporter/bin/notify alert`。通知失败返回非零，事件仍保留为 new。`ack` 幂等，改为 acked 并追加 acked_at；未知 id 报错。AgentConsole 的 dormant（cwd 出现在 registry）、idle_long、stale 为 L1，host_down 为 L2，其余已知类型为 L0；不写 human inbox。未知 `event` 类型走可选的模型慢速分支：`config/filter.toml` 的 `allowed_sources` 是事件 JSON 中 `source` 的白名单，默认空列表（关闭），未列入的来源不调用模型（AgentConsole 默认 L0，add 保留位置参数级别）；`timeout` 是单次调用超时秒数，默认 60。模型返回 L0/L1/L2、project（可为 null）和理由；调用或校验失败退化为 L1，理由保留错误摘要。add 也经过 classify，位置级别仅作默认；详见 thread 与订阅。

默认数据根为本模块 `state/`，可用绝对路径 `PRTS_INTERACTION_STATE` 覆盖：

- `tasks/<task>/`：prompt.md、last.md、run.log / run-resume-N.log，保留既有布局。
- `wakes/<id>/`：spec.json、prompt.txt、运行日志和 last.md。
- `registry.jsonl`：t/name/event 等兼容记录（start 事件含 pid、tries、gap，AgentConsole 用来显示「排队重试」）；唯一写入实现是 `lib/registry`。不进 git（11-19 起），不要 `git restore`/`checkout` 它；需要备份就复制文件。
- `github_poll.jsonl`：PR 游标追加日志，格式和压缩规则见下节；不进 git。
- `events/queue.jsonl`：id/t/level/source/text/status；队列写入与 ack 共用锁。

`lib/codex` 统一关闭 stdin，默认授予 workspace-write 和仓库 git 目录权限、禁用命令联网，重试 at capacity。dispatch 使用 `CODEX_TRIES` / `CODEX_GAP`（默认 6 / 600），wake 使用 `WAKE_TRIES` / `WAKE_GAP`。同一模型连续满载 `CODEX_SWITCH_AFTER`（默认 2）次后，下一次立刻改用 `CODEX_FALLBACK_MODELS`（逗号分隔，默认 `gpt-6-sol`）里的下一个模型（`codex -c model=…`），registry 记 `model_switch {from,to,after_try}`，之后的 capacity 事件带 `model`；本次运行显式指定了模型（`-m`/`--model`/`-c model=`，含 `CODEX_TOP`）或 queue 模式时不换。容量耗尽返回 75。精确会话名查询依赖 Codex 内部 SQLite 格式，集中在适配层；优先传 UUID。`lib/wake_state` 独占内部状态动作，`bin/wake` 不接受 `_claim` 等内部子命令。

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

## token 统计

`bin/tokens sync` 增量读取本机 `~/.claude/projects/**/*.jsonl` 与 `~/.codex/sessions/**/*.jsonl`，账本写入 `state/tokens/`（不进 git），只保存时间、模型、会话、cwd、项目和数字用量。`input` 是非缓存输入；`cache_read` 是缓存输入；`cache_write` 是缓存写入；`output` 已包含 reasoning；`reasoning` 只是 output 的明细，不能再次相加。因此合计为 `input + cache_read + cache_write + output`，不含缓存读为 `input + cache_write + output`。Claude 的 input 不含缓存，按消息 id 跨文件去重；Codex 用 `total_token_usage` 累计值的差值，重复累计事件和复制历史不重复计数，异常重置才采用 `last_token_usage`。文件偏移、inode 和 mtime 让未变化运行无需重读。

`tokens summary [--since DATE] [--until DATE] [--by day|project|agent|model|session|task|tag:KEY] [--tag key=value] [--json]` 默认东京最近七天、逻辑日可用 `--logical-day`；多个 `--by` 组成多维分组，输出 session 数（一个 session 或线程算一次 run，实验对比按它算）、调用次数 calls 和每个 session 的均值；查询自动 sync，`--no-sync` 跳过。`tokens top` 查看会话消耗和标题，`tokens tag SESSION key=value` 追加或覆盖实验标签；dispatch/resume 的 `--tag key=value` 会随 registry 记录。格式变更后用 `tokens sync --rebuild` 清空账本、索引和去重状态再重扫。

实验例：`for arm in raw formatted; do for i in 1 2 3; do interaction/bin/dispatch token-$arm-$i "$PWD" prompt.md --tag exp=ear-read --tag arm=$arm; done; done`，完成后运行 `interaction/bin/tokens summary --by tag:arm --since 2026-11-19 --json` 比较两组。统计不包含 ChatGPT 网页会话或其他机器上的 claude.ai。

## GitHub PR 轮询（R18 B0）

运行 `interaction/bin/github_poll` 扫描一次。通过 `lib/registry` 读取所有历史 cwd，查询各目录的 origin，识别 github.com 的 HTTPS、SSH（含 scp 写法）和 git URL，按 owner/repo 去重；目录失效、没有 origin 或非 GitHub 地址静默跳过。不另设仓库配置表。运行环境须有已认证且能读目标仓库的 `gh`、`git`、Python 3。

只列出 open PR，再读取 comments、reviews、分页 pulls/comments 行内意见及 CI。
用 gh api user 取当前账号，缓存到 state/github_user.json；切换账号后删除缓存再运行。
首次观测（含旧版游标迁移）只建基线，之后仅他人评论/评审/行内意见数量和 CI
汇总变化产生事件，自己的内容和单纯 updatedAt 不触发。registry 的 cwd origin
对应仓库，项目按 cwd 最长登记路径匹配；匹配不到为 null。事件带 gh:owner/repo#N，
经 event classify，L1 是无订阅且不开 slow path 时的默认。
CI failure 优先于 pending，再为 success；无检查 none，未识别 unknown。

默认游标路径 `interaction/state/github_poll.jsonl`，随 `PRTS_INTERACTION_STATE` 更改。每行如：

```json
{"key":"owner/repo#123","updated_at":"2026-11-14T00:00:00Z","comments":2,"ci":"pending","t":"2026-11-14T00:10:00+00:00"}
```

读、比较、事件入队和追加共用稳定锁 `.github_poll.lock`；并发运行遇锁跳过，留到下次。未变化不追加。未配置 roadmap 的仓库仅查询 open，已消失的 PR 不再 view；配置 roadmap 的仓库查询所有状态并检查合并（见下文 M11），关闭或合并的 PR 不保留反馈游标。追加 `{"key":"owner/repo#123","deleted":true,"t":"…"}` 清除游标，不产生关闭事件；重新打开视为首次发现。日志超过 1 MiB 时在同一锁内原子压缩，只保留每个仍被跟踪 PR 的最新游标，不保留历史或关闭项；因此大小随被跟踪 PR 数量而非轮询次数增长。

外部命令 stdin 关闭，每次超时 30 秒。仓库或单个 PR 失败写 stderr，继续其他仓库/PR，失败观测不推进游标。事件成功后才记录游标，失败下轮重试；观测派生稳定事件 ID，入队后游标保存前中断，重送不会重复投递。列表上限显式设为 10000；触及上限时拒绝本仓库本轮结果并报错，避免把被截断的 PR 当作已关闭。

定时模板在 `config/launchd/com.prts.interaction-github-poll.plist`，每 600 秒一次。模板使用 `/Users/prts/PRTS` 的正式路径；用户合并后核对路径及 PATH，先创建 `interaction/state/` 和 `~/Library/LaunchAgents/`，再复制模板到 `~/Library/LaunchAgents/`，自行执行 `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.prts.interaction-github-poll.plist`。stdout/stderr 写 `interaction/state/github_poll.log`。本改动只提供模板，不自动安装。

离线测试：`python3 interaction/tests/test_github_poll.py`，使用临时 state、替身 git/gh 和真实的本地 event 入队。无订阅时默认 L1；有订阅可路由，测试必须隔离 state 并替换 Codex。真实 GitHub 和 launchd 安装不属于此测试覆盖。

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

`worktrees auto` 每小时运行，闲置门槛为 30 分钟；规则 A（远程分支删除且没有未见提交）和规则 B（已合并且满足 7 天保护期）保持不变。`--now` 只跳过闲置检查，仍检查干净、lsof、活派发、锁定和 detached 等条件；`--repo` 可重复指定仓库。没有非主检出的仓库直接跳过，不 fetch。`--daily` 保留作兼容参数。

`clean [--dry] [--all]` 等价于 `auto --now`：默认只处理 `inventory()` 中的登记仓库，`--all` 扩展到 `inventory(True)`。合并验收后立即运行它；输出沿用 auto。lsof、活派发和其它安全检查仍然有效。闲置超过 7 天且规则 A/B 都不成立的工作树只产生一次 L1 `worktrees_stale` 提醒，列表变化后才会再次提醒。

有已跟踪改动或未跟踪文件就跳过；忽略文件不计入改动。未合并时说明原因，并在没有任何远程引用包含当前提交时标为「未推送」。通过检查后仅用 `git worktree remove`、`git branch -d`，不用强制删除。若 `-d` 拒绝（例如 squash 后无可证明已合并的 upstream），工作树已移除而分支保留，并打印原因。`--dry` 只读，不移除工作树或分支；运行中的任务应由调用方验收后再清理。

回归：`python3 interaction/tests/test_worktrees.py`，真实临时仓库和裸远程、Codex/gh 替身，子进程关闭 stdin；不清理真实工作树。

## 清理不再用的会话（tidy-sessions）
`interaction/bin/tidy-sessions [--apply]`：归档本机不会再用的 Codex 会话，可用 `codex unarchive <id>` 恢复。只看 AgentConsole `/api/state` 里 dormant（没有进程占用）的会话；空闲 ≥7 天，或者是派发任务的执行者、任务已审查且空闲 ≥2 天，就归档。不加 `--apply` 只列出候选。
Claude app 左边栏的会话只能用 app 自己的 archive_session 工具归档，所以由每周日 10:00 的 Claude 定时任务「清理左边栏」（`~/.claude/scheduled-tasks/prts-tidy-sessions/`）处理：先跑上面的命令，再按同一套空闲规则归档 Claude 会话；每个目录最近的顶层会话保留到空闲 30 天；运行中、置顶、开着 Remote Control 的会话和总控不动。用户 11-18 同意定期清理。

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

classify 顺序：①已有的需复核/紧急规则；②匹配有效 thread 或项目订阅则直通；
③已知 state 噪声或 noise=true 记 L0；④未知来源在 filter.toml 白名单内走模型；
⑤保留调用者默认级别（add 的位置参数，AgentConsole 默认 L0）。
慢速提示包含 pulse 的输入/输出/杂务定义和项目列表，输出
`{level, project: string|null, reason}`，失败 L1；模型新识别项目不在同轮二次投递。

Codex 使用 lib/codex queue 原语；Claude 无程序化投递接口，写
`state/outbox/<local_id>.jsonl` 并保留 L1 `kind=route_pending` 给总控转发。
每目标留一条 kind=routed 的审计事件（route.status 区分成功、待转发）。
queue 失败保留 L1。成功 queue 只代表入队，不代表执行完成。
`event add ... --id <稳定事件ID>` 重复提交无副作用；省略时生成 UUID。
事件锁覆盖路由，routes.jsonl 先记 attempt 再投递；若在投递期间崩溃，
重送同 ID 不盲目重复 queue，而留 route_pending，由总控检查实际投递结果。

AgentConsole 直接以关闭 stdin、捕获 stdout 的子进程调用
`interaction/bin/status threads --json`，不需要 HTTP 服务。
输出一个 JSON 对象，顶层字段为 `generated_at`、`threads`、`groups`。原有 threads 条目契约不变；无活动时 threads=[]，groups 仍列出登记的所有工程：
```json
{"generated_at":"ISO8601","groups":[],"threads":[{"key":"project:EchoAsRecord","kind":"project","project":"EchoAsRecord","title":"EchoAsRecord","subscribers":[{"id":"sub_…","to":"codex:…","paused":false}],"last_event_at":null,"last_event":null,"counts":{"events":0,"routed":0,"pending":0},"tasks":[{"name":"任务名","status":"done","started_at":"ISO8601","report":null,"reviewed":false}]}]}
```
kind 为 project|gh|ear|other，project/last_event_at/last_event/report 可为 null。
tasks.status 为 running|done|failed。任务按最新 start 后的 registry 状态聚合，
按 cwd/worktree.repo 项目、订阅 task/Codex UUID 或事件 task/thread_uuid 归属。
同一事件可同时出现在外部 thread 与所属项目；counts 不含路由审计副本，
routed 为完全直通事件数，pending 为仍处 new 的事件数。
`interaction/bin/review <任务名> [--undo]` 追加 reviewed 记录；新一轮 start 重置 false。

新增 `groups` 是「大项目 → 工程 → 工作团队」投影，前端默认显示到工程，展开再显示团队：
```json
{"name":"PRTS","next_ddl":null,"projects":[{"name":"AgentConsole","thread":"project:AgentConsole","paths":["~/PRTS/AgentConsole"],"meetings":[],"roadmap":{"items":[{"id":"M1","title":"检测 agent 在等人","status":"💤","start":null,"ddl":null,"evidence":null,"done":false,"auto":null}],"next_ddl":null,"path":"/Users/prts/PRTS/ROADMAP.md","open":[{"id":"M1","title":"检测 agent 在等人","status":"💤"}],"error":null},"team":[{"kind":"codex","id":"codex:<UUID>","title":"任务名","subscribed":false,"last_active":"ISO8601"}],"tasks_running":0,"tasks_unreviewed":0,"last_event_at":null}]}
```
上例为 groups 数组的一个元素。工程来自 `human/projects.toml`（测试可用 `PRTS_PROJECTS` 替换），
同名项合并 paths、去重并保持登记顺序；group/roadmap/roadmap_prefix/meetings 取同名项第一个非空值。
组按 group 首次出现顺序排列，缺 group 的工程归最后的「未分组」。没有活动或 ROADMAP 也保留工程。
paths 保留配置写法；roadmap.path 展开 `~`，未配置则为 null，open=[]、error=null。

ROADMAP 支持 `| R12 | 💤 | **标题** | …` 编号表格和 `- [ ] 标题` 任务清单，
表格状态含 ✅ 的行和 `[x]`/`[X]` 不算未完成，代码围栏里的示例跳过。
open 按文件顺序最多 5 条；任务清单的 id/status 为 null。读文件失败或未识别任何受支持条目时，
open=[] 且 error 为原因，不中断 status；全部完成或前缀未命中属于正常空结果。
可选 `roadmap_prefix` 只保留指定编号前缀的表格行（无编号清单不匹配前缀）。
共享 PRTS ROADMAP 的「PRTS 总控台」配置 R，「AgentConsole」配置 M。

M11 表格按表头列名识别，列顺序不限：`| 编号 | 状态 | 事项 | 开始 | DDL | 完成证据 |`。
编号也支持 `#`（兼容旧 `ID`），事项也支持「标题」；编号为 `[A-Za-z]+\d+`。
开始、DDL、完成证据可缺省，输出 null；日期为 YYYY-MM-DD。旧 `# / 状态 / 事项 / 要点`
继续支持；代码围栏跳过，清单继续支持。各工程文件登记在 projects.toml 的 roadmap，通常为
`human/roadmaps/<工程名>.md`；PRTS 总控台和 AgentConsole 继续共享 ROADMAP.md。
表格有「类型」列时条目多一个 `kind`；`kind` 为「检查」的条目（由 agent 代查）不发 DDL 提醒。roadmap 文件不在 git 仓库里时（如 `~/outreach/岗位总表.md`），`mark` 只改文件、不提交。
`roadmap.items` 按文件顺序最多 60 条（含已结束），每项为
`{id,title,status,start,ddl,evidence,done,auto}`。✅ 和 ❌ 的 done=true；其余未结束。
`auto` 为 null 或 `{state: pr_open|merged|accepted, url, at: ISO8601}`。
`open` 保留旧最多 5 条与旧状态判定（仅 ✅ 排除；❌ 仍在兼容视图中）。
工程的 `roadmap.next_ddl` 取所有未结束条目的最早 DDL，过期仍算；无日期为 null。
大项目的 `next_ddl` 取其下工程最早日期。工程的 `meetings` 来自可选配置
`meetings = ["Thu 15:00-17:00"]`，输出 `[{weekday:4,start:"15:00",end:"17:00"}]`，周一为 1。

### roadmap 命令与自动完成

- `interaction/bin/roadmap list [工程名] [--json]`：按工程列出条目；JSON 为
  `[{name,roadmap}]`。`--completed-since ISO8601` 额外给出 `completed`，从 Git 提交历史找
  指定时间以来转为 ✅ 且当前仍为 ✅ 的条目，用于组会摘要（包括手工修改）。
- `interaction/bin/roadmap mark <工程名> <编号> <状态> [--evidence 文本]`：状态只允许
  💤、📝、🔨、🔍、✅、❌；未知工程/编号、重复编号和非法状态报错。
  只替换目标行的状态、完成证据单元格；未指定 evidence 时保留证据；无证据列时追加到最后一列。
  证据中的换行折叠、竖线转义。随后在文件所属仓库对该路径执行 `git commit --only`，
  保留其他文件已暂存内容，不 push。该文件已有未提交内容也随该文件提交。
- `dispatch <任务> <目录> [prompt] --roadmap <工程名>:<编号>`：启动前校验编号，
  在该次 start registry 记录中登记 roadmap；同名任务续跑继承关联，新 dispatch 不继承旧关联。`review <任务>` 自动写 ✅，证据为任务名；
  `review --undo` 只撤销审查标志，不反向修改 roadmap。
- 复用 `github_poll`：按 PR 仓库路径匹配工程；标题、分支或正文中的独立编号须属于该工程。
  登记了 roadmap 的仓库查询所有状态 PR，以发现轮询间直接合并的 PR；其他仓库保持仅查询打开 PR。
  打开只追加 `pr_open` 供前端显示待验收，不改 Markdown；合并写 ✅，证据为 PR URL。
  已经 ✅/❌ 或已有 accepted/merged 自动记录的条目不再写回；重复 pr_open 不重复登记。
- 自动记录追加到 `interaction/state/roadmap-status.jsonl`，串行写锁为 roadmap.lock；均不提交。
  `PRTS_INTERACTION_STATE` 支持隔离测试。排序与拖动由 AgentConsole 自行存储，PRTS 不维护 order.json。


team 合并订阅、PRTS registry 和本机按目录归属的会话，不依赖 AgentConsole HTTP 服务：
- 未暂停、未删除且订阅该 project thread 的目标全部保留，subscribed=true；PR/ear 等其他 thread 的订阅不扩展为工程订阅。
- 历史团队来自每次 dispatch/resume 的 Codex thread 与 caller；按该次 cwd/worktree.repo 最长目录前缀归属。
  caller 表示派发参与者，不能证明 caller 自身 cwd 在工程内。
  Codex 的 last_active 为该次 start/thread/exit/gave_up 最新时间；caller 仅取 start 时间，review 不算会话活动。
  只有派发记录时 title 为最近派发任务名；未知 title/last_active 为 null。
- 桌面会话复用只读 `AgentConsole/agent_console/scan.py` 的扫描函数（内部 API 兼容依赖；共享读取例外）。
  Claude 从 JSONL 读取 cwd、文件 mtime 作为活动时间，desktop `claude-code-sessions` 提供标题、local ID、归档状态；
  Codex 只读 `state_5.sqlite`，沿用扫描器的标题优先级和 updated_at_ms。无需进程扫描或读取完整对话。
  cwd 与 pulse 共用 projects.match 按最长目录前缀匹配，支持 exact；家目录本身和家目录登记项不匹配。
  已归档 Claude 会话从所有来源排除；缺失 AgentConsole checkout 时仅保留订阅和派发，单源读取失败在 stderr 警告。
- 按 kind:id 去重，订阅覆盖历史身份；历史非订阅成员仅取最近 14 天（含边界，不含未来）最多 10 个。
  显式订阅不受历史窗口/数量限制；订阅者排在最前，两组各按 last_active 倒序、空值最后，同时间按 id 排序。
- AgentConsole 左栏匹配：去掉 `codex:` 后是其 agent.id（Codex 线程 UUID）；
  `claude:` 后是 CLI session ID 时匹配 agent.id，是 `local_…` 时匹配 agent.app_session_id。
  通过 desktop 元数据把 CLI ID（含旧 transcript）统一为 local ID 后去重；无映射时分别保留。
  本机会话标题优先于派发名称，last_active 取各来源最新时间。

tasks_running 统计原有对应 project thread 中 status=running 的任务；tasks_unreviewed 统计
已结束（done/failed）且 reviewed=false 的任务；last_event_at 沿用该 thread，无 thread 则 0/0/null。
新增 fixture 验收：`python3 interaction/tests/test_groups.py`；所有测试 CLI 子进程关闭 stdin。

R18 离线验收：python3 interaction/tests/test_threads.py（含严格字段 schema 校验）；pulse/tests/test_ear.py 与 test_pulse.py 的 PULSE_EVENT 替身验证来源，所有测试状态均隔离。
