# PRTS 术语表 / Glossary（v0.2，2026-11-07 重构后）

按文件结构解释每个目录、命令和对象的名字。
用词约定：「总控 / controller」指 PRTS 的 Claude 总控会话；「AgentConsole」指监视程序。两者不是一回事。

## 通用约定 / Conventions
每个模块都由下面几类东西组成。代码和数据严格分开，模块之间只通过 `bin/` 调用。

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
| `ROADMAP.md` | roadmap | 唯一的计划表：下一步、候选池、已完成 | 总控 |

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
| 验收 | review | 总控读事件和结果，决定下一步：续跑、重派、问你，或结束 |

### 命令 / `bin/`
| 命令 | English | 做什么 |
|---|---|---|
| `dispatch <task> <workdir> <prompt文件>` | dispatch | 新开一次运行：把 prompt 存进任务目录，用 `codex exec` 启动，并确认真的启动了。`--sandbox network或full` 放宽时必须附 `--approved-by "用户原话或出处"`；默认 workspace-write、禁联网。`--dry`（兼容 `DISPATCH_DRY=1`）只记录命令、不执行或写 registry |
| `resume <task> <session> <cwd> <消息文件>` | resume | 在已有会话上再跑一轮；模型满载时隔一段时间重试。支持同 dispatch 的 `--sandbox` / `--approved-by` / `--dry`，不继承上轮放宽 |
| `wake add\|list\|cancel` | wake | 预约、列出、取消定时唤醒 |
| `event add <L0\|L1\|L2> <来源> <内容>` | event | 往事件队列加一条；L2 同时通过 reporter 弹通知 |
| `event from-agentconsole` | event | AgentConsole 的事件处理入口（stdin 一条 JSON），按策略分级后入队 |
| `event list [--new]`、`event ack <id>` | event | 总控验收用：看未处理的事件、标记已处理 |

### 内部 / `lib/`
| 名字 | English | 做什么 |
|---|---|---|
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
| `registry.jsonl` | registry | 全部派发和唤醒记录，一行一条 | 是 |
| `events/queue.jsonl` | event queue | 待验收的事件 | 否 |
| `prompts/` | legacy drop | 过渡期：旧路径 `ops/prompts/` 指向这里；dispatch 会把 prompt 复制进任务目录 | 否 |

## reporter/（报告与通知 / reporting & notification）
| 名字 | English | 做什么 |
|---|---|---|
| `bin/notify <log\|wechat\|phone\|alert> [--title T] (--text\|--file)` | notify | 送达一条通知。log 只记录；wechat 发微信；phone 用 Bark 推到 iPhone；alert = Bark + macOS 通知（11-12 起不再发微信）。旧用法（不带级别）等同 wechat |
| `bin/ask add\|next\|due\|reply\|answer\|close\|expire\|render\|wait` | ask | 提问队列。紧急度：blocking（每 30 分钟重复提醒）、timely（推送一次）、soon（每日汇总）、whenever（等用户开 session）。见 reporter/README |
| `bin/todo add\|list\|done` | todo | 用户自己的待办，存在 Apple 提醒事项的「PRTS」列表，会同步到 iPhone。见 reporter/README |
| `bin/remind` | remind | 每小时由 launchd 运行：pulse check → ask due，有问题才推送（Bark + macOS）。见 reporter/README |
| `bin/report weekly [日期]` | report | 生成并送达周报 |
| `bin/report daily` | report | 把 aquant 日报校验后放进微信发件箱（launchd 每 10 分钟和文件变化时触发） |
| `lib/collect.py`、`compose.md`、`render.py`、`deliver.py` | collect / compose / render / deliver | 收集素材、写成文字、排版、投递 |
| `lib/channels/` | channels | 各送达渠道的适配器；wechat 调用 CodexBridge 的 `weixin notify` |
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
- **只走接口**：模块之间只调用对方的 `bin/`，不读写对方的 `lib/` 或 `state/`。外部工具（Codex、CodexBridge）也只用它们的公开命令；唯一的例外写在 `interaction/lib/codex` 里。
