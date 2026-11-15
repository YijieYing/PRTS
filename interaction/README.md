# interaction：与 agent 交互

负责派发、续跑、一次性唤醒，以及交给总控验收的事件队列。模块间通过 `bin/` 调用命令；结构化模型调用的共享 Python 原语见下文。

| 命令 | 用法 |
|---|---|
| `bin/dispatch` | `<task> <workdir> [prompt文件] [--worktree 分支 [--base ref]] [--sandbox network或full --approved-by "用户原话或出处"] [--dry] [Codex exec 参数...]`；省略 prompt 时读该任务的 `prompt.md`。异步启动并检查活动；`--dry`（兼容 `DISPATCH_DRY=1`）复制 prompt、记录命令（带 `--worktree` 时也准备工作树），不启动 Codex 或写 registry |
| `bin/worktrees` | `list` 或 `clean [--dry] [--all]`：列出工作树；只清理干净且已合并的工作树 |
| `bin/resume` | `<task> <session UUID> <cwd> <消息文件> [重试次数=6] [间隔秒=600] [--sandbox network或full --approved-by "用户原话或出处"] [--dry]`；同步执行 |
| `bin/wake` | `add <带时区ISO时间或HH:MM> <UUID或精确会话名> <prompt文件> [--name NAME] [--mode resume或queue]`；`list`；`cancel <id>` |
| `bin/github_poll` | 不带参数运行一次，从 registry 的 cwd 派生 GitHub 仓库，PR 变化进入 L1 复核队列 |
| `bin/event` | `add <L0或L1或L2> <source> <text> [--thread KEY] [--project NAME] [--kind KIND] [--id ID]`；`from-agentconsole` 从 stdin 读一个 JSON；`list [--new]`；`ack <id>` |
| `bin/wait` | `<task> [轮询秒=30]`，等待当前运行结束，打印 last.md；退出码为运行结果（75 为重试耗尽）。此命令由总控同步维护 |
| `bin/status` | `[task]`，输出 registry JSONL；`links` 输出显式派发关系 JSONL；`threads [--json]` 输出主线投影；供其他模块只读查询，不访问内部文件 |

`wake` 的 HH:MM 按日本时间解释，过去的时分预约到明天；按分钟向上取整。resume 完成表示本轮退出，queue 完成只表示入队。`WAKE_DRY=1` 跳过 Codex，**仍会注册 launchd**。取消仅限未运行任务。

L0 只入队；L1 等总控验收；L2 入队后调用 `reporter/bin/notify alert`。通知失败返回非零，事件仍保留为 new。`ack` 幂等，改为 acked 并追加 acked_at；未知 id 报错。AgentConsole 的 dormant（cwd 出现在 registry）、idle_long、stale 为 L1，host_down 为 L2，其余已知类型为 L0；不写 human inbox。未知 `event` 类型走可选的模型慢速分支：`config/filter.toml` 的 `allowed_sources` 是事件 JSON 中 `source` 的白名单，默认空列表（关闭），未列入的来源不调用模型（AgentConsole 默认 L0，add 保留位置参数级别）；`timeout` 是单次调用超时秒数，默认 60。模型返回 L0/L1/L2、project（可为 null）和理由；调用或校验失败退化为 L1，理由保留错误摘要。add 也经过 classify，位置级别仅作默认；详见 thread 与订阅。

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

读、比较、事件入队和追加共用稳定锁 `.github_poll.lock`；并发运行遇锁跳过，留到下次。未变化不追加。成功列出的 open 集合中已消失的 PR 不再 view，追加 `{"key":"owner/repo#123","deleted":true,"t":"…"}` 清除游标，不产生关闭事件；重新打开视为首次发现。日志超过 1 MiB 时在同一锁内原子压缩，只保留每个仍被跟踪 PR 的最新游标，不保留历史或关闭项；因此大小随被跟踪 PR 数量而非轮询次数增长。

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
{"name":"PRTS","projects":[{"name":"AgentConsole","thread":"project:AgentConsole","paths":["~/PRTS/AgentConsole"],"roadmap":{"path":"/Users/prts/PRTS/ROADMAP.md","open":[{"id":"M1","title":"检测 agent 在等人","status":"💤"}],"error":null},"team":[{"kind":"codex","id":"codex:<UUID>","title":"任务名","subscribed":false,"last_active":"ISO8601"}],"tasks_running":0,"tasks_unreviewed":0,"last_event_at":null}]}
```
上例为 groups 数组的一个元素。工程来自 `human/projects.toml`（测试可用 `PRTS_PROJECTS` 替换），
同名项合并 paths、去重并保持登记顺序；group/roadmap/roadmap_prefix 取同名项第一个非空值。
组按 group 首次出现顺序排列，缺 group 的工程归最后的「未分组」。没有活动或 ROADMAP 也保留工程。
paths 保留配置写法；roadmap.path 展开 `~`，未配置则为 null，open=[]、error=null。

ROADMAP 支持 `| R12 | 💤 | **标题** | …` 编号表格和 `- [ ] 标题` 任务清单，
表格状态含 ✅ 的行和 `[x]`/`[X]` 不算未完成，代码围栏里的示例跳过。
open 按文件顺序最多 5 条；任务清单的 id/status 为 null。读文件失败或未识别任何受支持条目时，
open=[] 且 error 为原因，不中断 status；全部完成或前缀未命中属于正常空结果。
可选 `roadmap_prefix` 只保留指定编号前缀的表格行（无编号清单不匹配前缀）。
共享 PRTS ROADMAP 的「PRTS 总控台」配置 R，「AgentConsole」配置 M。

team 使用现有订阅和 PRTS registry，不依赖 AgentConsole HTTP 服务或扫描对话全文：
- 未暂停、未删除且订阅该 project thread 的目标全部保留，subscribed=true；PR/ear 等其他 thread 的订阅不扩展为工程订阅。
- 历史团队来自每次 dispatch/resume 的 Codex thread 与 caller；按该次 cwd/worktree.repo 最长目录前缀归属。
  caller 表示派发参与者，不能证明 caller 自身 cwd 在工程内；未经过 PRTS 派发且未订阅的桌面会话不在此来源中。
  Codex 的 last_active 为该次 start/thread/exit/gave_up 最新时间；caller 仅取 start 时间，review 不算会话活动。
  title 为最近派发任务名（并非桌面自定义标题）；未知 title/last_active 为 null。
- 按 kind:id 去重，订阅覆盖历史身份；历史非订阅成员仅取最近 14 天（含边界，不含未来）最多 10 个。
  显式订阅不受历史窗口/数量限制；整个 team 按 last_active 倒序、空值最后，同时间按 id 排序。
- AgentConsole 左栏匹配：去掉 `codex:` 后是其 agent.id（Codex 线程 UUID）；
  `claude:` 后是 CLI session ID 时匹配 agent.id，是 `local_…` 时匹配 agent.app_session_id。
  两种 Claude ID 在 registry 无映射时分别保留，不推测它们是同一会话。

tasks_running 统计原有对应 project thread 中 status=running 的任务；tasks_unreviewed 统计
已结束（done/failed）且 reviewed=false 的任务；last_event_at 沿用该 thread，无 thread 则 0/0/null。
新增 fixture 验收：`python3 interaction/tests/test_groups.py`；所有测试 CLI 子进程关闭 stdin。

R18 离线验收：python3 interaction/tests/test_threads.py（含严格字段 schema 校验）；pulse/tests/test_ear.py 与 test_pulse.py 的 PULSE_EVENT 替身验证来源，所有测试状态均隔离。
