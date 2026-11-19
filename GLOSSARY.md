# PRTS 术语表 / Glossary（v0.2，2026-11-07 重构后）

按文件结构解释每个目录、命令和对象的名字。
用词约定：「总控 / controller」指 PRTS 的 Claude 总控会话；「AgentConsole」指监视程序。两者不是一回事。

## 通用约定 / Conventions
每个模块都由下面几类东西组成。代码和数据严格分开，模块之间通过 `bin/` 调用命令；共享 Python 库例外见下文「只走接口」。

| 名字 | English | 含义 | 进 git？ |
|---|---|---|---|
| `README.md` | interface | 模块对外的契约：能做什么、怎么调用。人只需要读这个 | 是 |
| `bin/` | entry points | 对外可执行的命令。别的模块只能调用这里的命令 | 是 |
| `lib/` | internals | 内部代码，外部不调用 | 是 |
| `config/` | configuration | 人可以调的参数（收件人、频率等） | 是 |
| `state/` | runtime state | 运行时产生的数据：日志、记录、排队中的东西。只有本模块写 | 日志不进；记录类例外见各模块 |
| `tests/` | tests | 只在临时目录里跑，不碰真实的 state | 是 |

## 顶层 / Top level
| 目录 | English | 含义 | 唯一写入者 |
|---|---|---|---|
| `human/` | human entry | 给你看的入口：报告链接、待办（inbox）、留言 | 总控，以及你 |
| `memory/` | controller memory | 总控的记忆和开工流程 | 总控 |
| `interaction/` | agent interaction | 和 agent 打交道：派发、续跑、定时唤醒、事件队列 | 本模块 |
| `reporter/` | reporting & notification | 生成内容并送达你：周报、日报、单条通知；以后还负责向你提问 | 本模块 |
| `AgentConsole/` | monitor | 只观察、产生事件，不做判断（独立仓库） | 本模块 |
| `pulse/` | user state（v1，2026-11-12；ROADMAP R2） | 用户本人的状态：一天的有效时间花在输入、输出还是杂务上（每日回顾）；此刻是否方便被打扰。reporter 推送前问它 | 本模块 |
| `maintenance/` | maintenance | 一次性维护脚本和备份，不承诺接口 | — |
| `ops/` | legacy links | 过渡期：只剩指向新位置的链接，2026-11-21 前后删除 | — |
| `GLOSSARY.md` | glossary | 本文件 | 总控 |
| `ROADMAP.md` | roadmap | PRTS 的计划表；其他工程的计划路径在 human/projects.toml 的 roadmap 字段登记 | 总控 |

### pulse 时间线 / pulse timeline
| 名字 | English | 含义 |
|---|---|---|
| 主线 | episode | 日报里把同一件连续活动合并后的时间线单元；由 `main` 段组成，附带经校验的 side 段 |
| 走神 | distraction | 主线进行中与主线无关的短暂活动；只作为主线下的一行，不改变计时 |
| 穿插 | interlude | 为主线或系统做的短暂维护性切换，例如代理设置、登录或找文件；只作为主线下的一行 |
| 短事件 | notable | 时间短但有意义的另一件事；不被主线吞掉，在时间线上单独显示 |

## interaction/（与 agent 交互 / agent interaction）
### 对象 / Objects
| 名字 | English | 含义 |
|---|---|---|
| 任务 | task | 有名字的一件事，由一份 prompt 定义。例：`prts-modularize` |
| 运行 | run | 任务的一次执行，即一次 `codex exec` |
| 会话 | session | Codex 或 Claude 的一段对话，用 UUID 标识；续跑和唤醒都针对会话 |
| 唤醒 | wake | 预约在某个时间续跑某个会话，执行一次后作废 |
| 记录 | registry event | 派发、结束、唤醒、容量重试等动作的流水账 |
| 事件 | event | 需要总控验收或需要你知道的事，按 L0/L1/L2 分级，进入事件队列 |
| 验收 | review | 用户/总控验收任务；bin/review 追加 reviewed=true，--undo 撤销，新运行重置 |
| 大项目 | group | projects.toml 中的工程分组；status threads --json 的 groups 按登记顺序输出 |
| 路线图条目 | roadmap item | 工程计划中的稳定编号、状态、日期与完成证据；roadmap 命令管理，next_ddl 为最早未结束期限 |
| 工作团队 | team | 工程 thread 的订阅者、近期 registry 派发参与会话及 cwd 匹配工程的本机会话；通过 kind:id 对应 AgentConsole 会话 |
| 事件主线 | thread | 同一外部对象或项目的连续事件，thread_key 标识；区别于 Codex 会话 UUID |
| 订阅 | subscription | 项目或 thread 到 codex/claude 目标的显式登记；可暂停、恢复、删除 |
| 路由 | routed | 按订阅投递的审计记录；route.status 标明已入队或待人工转发 |
| 快速路径 | fast path | 规则分级、订阅直通、丢噪声，无模型调用 |
| 慢速路径 | slow path | 仅白名单未知来源调用模型，输出 level/project/reason，失败 L1 |

### 命令 / `bin/`
| 命令 | English | 做什么 |
|---|---|---|
| `dispatch <task> <workdir> <prompt文件> [--worktree 分支 [--base ref]]` | dispatch | 新开一次运行：把 prompt 存进任务目录，用 `codex exec` 启动，并确认真的启动了。`--sandbox network或full` 放宽时必须附 `--approved-by "用户原话或出处"`；默认 workspace-write、禁联网。`--dry`（兼容 `DISPATCH_DRY=1`）只记录命令（带 `--worktree` 时也准备工作树）、不执行 Codex 或写 registry |
| `worktrees list / clean [--dry] [--all]` | worktrees | 列出工作树；验收合并后安全清理干净且已合并的工作树，保留无法用 `branch -d` 删除的分支 |
| `resume <task> <session> <cwd> <消息文件>` | resume | 在已有会话上再跑一轮；模型满载时隔一段时间重试。支持同 dispatch 的 `--sandbox` / `--approved-by` / `--dry`，不继承上轮放宽 |
| `subscribe` | subscription registry | add/list/pause/resume/remove 项目或 thread 订阅 |
| `review` | review | 追加任务 reviewed，--undo 撤销 |
| `github_poll` | GitHub polling source | 从 registry 派生仓库，他人评论/评审和 CI 变化交给 classify 分级或直通 |
| `wake add\|list\|cancel` | wake | 预约、列出、取消定时唤醒 |
| `event add <L0\|L1\|L2> <来源> <内容>` | event | 往事件队列加一条；L2 同时通过 reporter 弹通知 |
| `event from-agentconsole` | event | AgentConsole 的事件处理入口（stdin 一条 JSON），按策略分级后入队 |
| `event list [--new]`、`event ack <id>` | event | 总控验收用：看未处理的事件、标记已处理 |

### 内部 / `lib/`
| 名字 | English | 做什么 |
|---|---|---|
| `github_poll.py` | GitHub polling source | GitHub 查询、CI 汇总与游标比较，命令与来源均使用 github_poll |
| `registry` | registry I/O | 唯一写 `state/registry.jsonl` 的代码 |
| `codex` | Codex adapter | 封装 `codex exec`、`exec resume`、`queue`：关闭 stdin、git 写权限、容量重试。会话名到 UUID 的解析也在这里，是唯一依赖 Codex 内部文件的地方 |
| `wake_state` | wake state machine | 唤醒的状态变化：scheduled → running → done / failed / cancelled |
| `wake_fire` | wake entry | launchd 到点执行的程序；不给人用，所以放在 lib |

### 数据 / `state/`
| 路径 | English | 内容 | 进 git？ |
|---|---|---|---|
| `tasks/<task>/prompt.md` | task prompt | 任务说明 | 是 |
| `tasks/<task>/last.md` | run report | 最近一次运行 Codex 的最终报告 | 是 |
| `tasks/<task>/run*.log` | run log | 运行日志 | 否 |
| `wakes/<id>/` | wake record | 唤醒的 spec、prompt 副本和日志 | 否 |
| `github_poll.jsonl` | GitHub cursor | 每个打开 PR 的更新时间、评论数和 CI 状态；追加并定期压缩 | 否 |
| `registry.jsonl` | registry | 全部派发和唤醒记录，一行一条 | 是 |
| `events/queue.jsonl` | event queue | 待验收的事件 | 否 |
| `prompts/` | legacy drop | 过渡期：旧路径 `ops/prompts/` 指向这里；dispatch 会把 prompt 复制进任务目录 | 否 |

## reporter/（报告与通知 / reporting & notification）
| 名字 | English | 做什么 |
|---|---|---|
| `bin/notify <log\|wechat\|phone\|alert\|note> [--title T] (--text\|--file) [--url U] [--folder F]` | notify | 送达一条通知。log 只记录；wechat 发微信；phone 用 Bark 推到 iPhone（`--url` 点开时打开）；alert = Bark + macOS 通知（11-12 起不再发微信）；note 把全文写进 Apple 备忘录文件夹（11-14 起日报全文放这里）。旧用法（不带级别）等同 wechat |
| `bin/ask add\|next\|due\|reply\|answer\|close\|expire\|render\|wait` | ask | 提问队列。紧急度：blocking（每 30 分钟重复提醒）、timely（推送一次）、soon（每日汇总）、whenever（等用户开 session）。见 reporter/README |
| `bin/todo add\|list\|done` | todo | 用户自己的待办，存在 Apple 提醒事项的「PRTS」列表，会同步到 iPhone。见 reporter/README |
| `bin/recap` | recap | 每小时 remind 按活动结束判断，05:00 兜底、按日期幂等；全文不截断写进备忘录，推送前 8 行。支持手动指定逻辑日与只读 --dry。见 reporter/README |
| `bin/remind` | remind | 全天每小时 :07 运行：Ear 静默同步 → recap 结束判断 → pulse check → 非 quiet 时 ask due；日报不受 quiet 限制。见 reporter/README |
| `pulse focus` | focus | 专注时段：set 目标和截止时间，launchd（com.prts.pulse-focus，每 5 分钟）跑 check，偏离目标太久就推送提醒；离开电脑不计。见 pulse/README §十一 |
| `bin/report weekly [日期]` | report | 生成并送达周报 |
| `bin/report daily` | report | 把 aquant 日报校验后放进微信发件箱（launchd 每 10 分钟和文件变化时触发） |
| `lib/collect.py`、`compose.md`、`render.py`、`deliver.py` | collect / compose / render / deliver | 收集素材、写成文字、排版、投递 |
| `lib/channels/` | channels | 各送达渠道的适配器；wechat 调用 CodexBridge 的 `weixin notify`；notes 写 Apple 备忘录 |
| `config/config.toml` | configuration | 收件人、发件箱路径、日报开关 |
| `state/out/` | delivery log | 生成的中间文件和送达记录 |
| `state/outbox/` | outbox | 等 CodexBridge `/auto` 任务取走的文本。`reporter/outbox` 是指向它的链接，因为你的 `/auto` 任务还在读旧路径 |

微信的限制：你 24 小时内没给机器人发过消息时，推送会暂存，等你下一条消息后再补发。

## AgentConsole/（监视 / monitor）
| 名字 | English | 含义 |
|---|---|---|
| scan | scan | 定期扫描本机和 lain 上的 agent 会话 |
| event | event | 状态变化，如 working → dormant、主机不可达 |
| handler | handler | 配置在 `~/.agentconsole/config.json` 的 `on_event`，指向 `interaction/bin/event from-agentconsole` |
| backup plugin | backup | 每天备份 Claude / Codex 对话到 `maintenance/backups/`；它的后置钩子检查未推送的提交，结果交给 `interaction/bin/event` |
| human watch | human-edit watch | （计划）发现 `human/` 有未提交的改动时，产生「人类修改」事件 |

## maintenance/（维护 / maintenance）
| 名字 | 做什么 |
|---|---|
| `codex_trim.py` | 截断过长的 Codex 会话（备份写进 `backups/`） |
| `lain-fix-lid-suspend.sh` | 修 lain 合盖后的日志刷屏 |
| `backups/` | 对话备份、改全局配置前留的备份（不进 git） |
| `archive/aquant-overnight/` | 10-20 的夜间 supervisor 实验，已结束，只留档 |

## 规则 / Rules
- **单写者**：每个目录只有一个写入者，见上表。`human/inbox.md` 只由总控写：各处发现的事先进 `interaction` 的事件队列，总控验收时整理进 inbox。
- **不循环读自己**：总控改了 `human/` 就立刻提交。「人类修改」事件只认 `human/` 中**未提交**的改动，所以总控自己的改动不会被再读一遍。
- **只走接口**：模块之间只调用对方的 `bin/`，不读写对方的 `lib/` 或 `state/`；显式共享库例外为 `interaction/lib/projects.py`（项目别名和路径）、`interaction/lib/schema.py` 和 `interaction/lib/run_model.py`（Ear 与事件分诊共用，领域 prompt/schema 由调用方持有）。外部工具（Codex、CodexBridge）也只用它们的公开命令；唯一的例外写在 `interaction/lib/codex` 里。

Ear：pulse 默认通过新 Ear 的只读 read_transcripts 脚本获取逐句转写，按时间窗切段；source=old 保留旧 SQLite 兼容。同步复用 reporter 的 remind/recap，无独立 Ear 定时器。
