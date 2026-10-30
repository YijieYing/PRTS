# PRTS 术语表 / Glossary（草案 v0.1，2026-10-30）

按**目标文件结构**解释每个目录、可执行文件和对象的名字。「现在」列写的是还没迁移时的位置。
用词约定：「总控 / controller」指 PRTS 的 Claude 总控会话；「AgentConsole」指监视程序，两者不是一回事。

## 通用约定 / Conventions
每个模块都由四类东西组成。代码和数据严格分开，模块之间只通过 `bin/` 调用。

| 名字 | English | 含义 | 进 git？ |
|---|---|---|---|
| `README.md` | interface | 模块对外的契约：能做什么、怎么调用。人只需要读这个 | 是 |
| `bin/` | entry points | 对外可执行的命令。别的模块只能调用这里的命令 | 是 |
| `lib/` | internals | 内部代码，外部不调用 | 是 |
| `config/` | configuration | 人可以调的参数（收件人、频率等） | 是 |
| `state/` | runtime state | 运行时产生的数据：日志、记录、排队中的东西。只有本模块写 | 否（个别例外会注明） |

## 顶层 / Top level
| 目录 | English | 含义 | 唯一写入者 | 现在 |
|---|---|---|---|---|
| `human/` | human entry | 给你看的入口：报告链接、待办（inbox）、留言 | 总控，以及你 | 同 |
| `memory/` | controller memory | 总控的记忆和开工流程 | 总控 | 同 |
| `interaction/` | agent interaction | 和 agent 打交道的模块：派发、续跑、定时唤醒、验收 | 本模块 | `ops/` 的一部分 |
| `reporter/` | reporting & notification | 生成内容并送达你：周报、日报、单条通知 | 本模块 | `Reporter/` + `ops/wechat-notify.sh` 等 |
| `AgentConsole/` | monitor | 只观察、产生事件，不做判断（独立仓库） | 本模块 | 同 |
| `maintenance/` | maintenance | 一次性维护脚本，不承诺接口 | — | `ops/` 的一部分 |
| `GLOSSARY.md` | glossary | 本文件 | 总控 | 新 |

## interaction/（与 agent 交互 / agent interaction）
### 对象 / Objects
| 名字 | English | 含义 |
|---|---|---|
| 任务 | task | 有名字的一件事，由一份 prompt 定义。例：`ops-wake` |
| 运行 | run | 任务的一次执行，即一次 `codex exec`；一个任务可以跑多次 |
| 会话 | session | Codex 或 Claude 的一段对话，用 UUID 标识；续跑和唤醒都针对会话 |
| 唤醒 | wake | 预约在某个时间续跑某个会话，执行一次后作废 |
| 事件 | event | 一条记录：开始、结束、唤醒、容量重试等，写在 registry 里 |
| 验收 | review | 总控读事件和结果，决定下一步：续跑、重派、问你，或结束 |

### 命令 / `bin/`
| 命令 | English | 做什么 | 现在 |
|---|---|---|---|
| `dispatch <task> <workdir>` | dispatch | 新开一次运行：读任务的 prompt，用 `codex exec` 启动，并确认真的启动了 | `ops/dispatch.sh` |
| `resume <session> <prompt>` | resume | 在已有会话上再跑一轮；模型满载时自动隔一段时间重试 | `ops/retry_resume.sh` |
| `wake add\|list\|cancel` | wake | 预约、列出、取消定时唤醒 | `ops/wake.sh` |
| `status [task]` | status | 查看任务状态和最后一份报告 | 无（现在手工看 `jobs/`） |
| `review` | review | 验收循环的一次：读新事件，处理能处理的，需要你决定的交给 reporter 通知你 | 无（现在靠总控手工） |

### 内部 / `lib/`
| 名字 | English | 做什么 | 现在 |
|---|---|---|---|
| `registry` | event log I/O | 读写事件日志，是唯一写 registry 的代码 | 散在各个 sh 里 |
| `codex` | Codex adapter | 封装 `codex exec`、`exec resume`、`queue`，包括关闭 stdin 和容量重试 | 散在各个 sh 里 |
| `launchd` | scheduler adapter | 创建、删除一次性 launchd 任务 | `wake.sh` 内 |
| `wake_state` | wake state machine | 唤醒的状态变化：scheduled → running → done/failed/cancelled | `wake.sh` 的 `_claim`/`_finish` |
| `wake_fire` | wake entry | launchd 到点执行的程序；不给人用，所以放在 lib | `ops/wake_run.sh` |

### 数据 / `state/`
| 路径 | English | 内容 | 现在 |
|---|---|---|---|
| `state/tasks/<task>/prompt.md` | task prompt | 任务说明。**例外：进 git**，方便复用和追溯 | `ops/prompts/<task>.md` |
| `state/tasks/<task>/runs/<时间>/` | run record | 一次运行的日志和 `last.md`（Codex 的最终报告） | `ops/jobs/<task>/` |
| `state/wakes/<id>/` | wake record | 唤醒的 spec、prompt 副本和日志 | `ops/wakes/<id>/` |
| `state/registry.jsonl` | event log | 全部事件，一行一条 | `ops/registry.jsonl` |
| `state/events/` | review queue | AgentConsole 送来的待验收事件 | 现在直接写进 `human/inbox.md` |

## reporter/（报告与通知 / reporting & notification）
| 名字 | English | 做什么 | 现在 |
|---|---|---|---|
| `bin/notify <level> <title> --text\|--file` | notify | 送达一条通知。level 决定渠道：log 只记录，wechat 发微信，alert 发微信并弹窗 | `ops/wechat-notify.sh` |
| `bin/report weekly\|daily` | report | 生成并送达周报或日报 | `Reporter/run_weekly.sh`、`aquant_daily.py` |
| `lib/collect`、`compose`、`render` | collect / compose / render | 收集素材、写成文字、排版 | `Reporter/*.py` |
| `lib/channels/wechat`、`email`、`macos` | channels | 各送达渠道的适配器；wechat 调用 CodexBridge 的 `weixin notify` | 分散 |
| `config/` | configuration | 收件人、发送时间 | `Reporter/config.toml` |
| `state/` | delivery log | 已生成的报告和送达记录 | `Reporter/out/`、`Reporter/outbox/` |

## AgentConsole/（监视 / monitor）
| 名字 | English | 含义 |
|---|---|---|
| scan | scan | 定期扫描本机和 lain 上的 agent 会话 |
| event | event | 状态变化，如 working → dormant、主机不可达 |
| handler | handler | 把事件交给 interaction 的验收队列；紧急事件直接调用 `reporter notify`。现在是 `ops/on_event.sh` |
| human watch | human-edit watch | （计划）发现 `human/` 有未提交的改动时，产生「人类修改」事件 |

## maintenance/（维护 / maintenance）
| 名字 | 做什么 | 现在 |
|---|---|---|
| `codex_trim.py` | 截断过长的 Codex 会话 | `ops/` |
| `lain-fix-lid-suspend.sh` | 修 lain 合盖后的日志刷屏 | `ops/` |
| `backups/` | 改全局配置前留的备份 | `ops/backups/` |

## 规则 / Rules
- **单写者**：每个目录只有一个写入者，见上表。
- **不循环读自己**：总控改了 `human/` 就立刻提交。「人类修改」事件只认 `human/` 中**未提交**的改动，所以总控自己的改动不会被再读一遍。
- **只走接口**：模块之间只调用对方的 `bin/`，不读写对方的 `lib/` 或 `state/`。外部工具（Codex、CodexBridge）也只用它们的公开命令。
