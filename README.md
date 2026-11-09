# PRTS：让 Codex 和 Claude Code 协作的本机工具

本页的作用：说明 PRTS 由哪些模块组成，并分清哪些是 PRTS 自己写的，哪些是 Codex、cc、macOS 本来就有的。
- 名词和目录的完整解释在 [GLOSSARY.md](GLOSSARY.md)。
- 给人看的入口在 [human/README.md](human/README.md)。
- 接下来要做什么在 [ROADMAP.md](ROADMAP.md)。
- 新加工具时，在这里补一行。

## 一、现成功能（不是 PRTS 写的，PRTS 只是在调用）

| 来源 | 功能 | PRTS 用它做什么 |
|---|---|---|
| Codex CLI | `codex exec`：无界面跑一个任务；`-o` 把最后回复写到文件 | `interaction/bin/dispatch` 派发任务 |
| Codex CLI | `codex exec resume <thread>`：在已有 session 上接着跑一轮 | `interaction/bin/resume`、`wake` |
| Codex CLI | `codex queue --thread <id> --message`：给一个已有 session 排一条消息 | 总控给 aquant 等 session 追加任务；`wake --mode queue` |
| Codex app-server | 线程读写 API | `maintenance/codex_trim.py` 截断过长的 session |
| Claude 桌面 app / cc | session、分组、`search_session_transcripts`、`start_session`、`SendMessage`、scheduled tasks | 总控管理和查找各个 session |
| cc | 自动记忆（`~/.claude/projects/*/memory/`）、`CLAUDE.md`、hooks | 全局规则和总控记忆 |
| macOS | launchd（定时、常驻）、`caffeinate`、`osascript` 通知 | 所有定时和常驻的东西都挂在 launchd 上 |
| CodexBridge 原仓库 | 微信收发、`/auto` 定时任务、秘书记录（`/remind` `/todo` …） | 微信入口 |

注意：Codex 和 cc 本身都**不会**在某个时间点自己醒来。session 只在收到消息时干活。

## 二、PRTS 的模块（2026-11-07 重构后）

| 模块 | 做什么 | 主要命令 |
|---|---|---|
| [interaction/](interaction/README.md) | 和 agent 打交道：派发、续跑、定时唤醒、事件队列 | `dispatch`、`resume`、`wake`、`event` |
| [reporter/](reporter/README.md) | 送达你：周报、aquant 日报、单条通知 | `report`、`notify` |
| `AgentConsole/` | 全机 agent 监视（http://127.0.0.1:7788，独立仓库），产生事件交给 `interaction/bin/event` | — |
| `maintenance/` | 一次性维护脚本、备份、已结束实验的存档 | — |
| `human/`、`memory/` | 给你看的入口；总控的记忆 | — |
| `ops/` | 过渡期只剩指向新位置的链接，约 2026-11-21 删除 | — |

PRTS 以外的改动：CodexBridge 本地分支 `fix/durable-weixin-replies` 在原仓库之上加了回复持久化、`weixin notify` 主动推送、秘书起草 `/auto add`、`/auto` 一次性时间表和两个小修复。已向原仓库提议（issue #26），尚未合入。

### 历史：各工具加入的时间
| 工具 | 加入日期 | 现在的位置 |
|---|---|---|
| 派发 `dispatch`、记录 `registry.jsonl`、AgentConsole 事件处理 | 10-20 | `interaction/` |
| 续跑 `resume`（遇到 at capacity 自动重试） | 10-22 | `interaction/bin/resume` |
| 未推送提醒（备份插件的后置钩子，不会自己推送） | 10-21 | AgentConsole backup 插件 |
| 微信推送 `notify` | 10-30 | `reporter/bin/notify` |
| 定时唤醒 `wake`（10-30 财报事故后补上） | 10-30 | `interaction/bin/wake` |
| 事件队列 `event`、通知分级 | 11-07 | `interaction/bin/event`、`reporter/bin/notify` |

## 三、触发方式一览

| 想要的效果 | 用什么 |
|---|---|
| 派一个新任务给 Codex | `interaction/bin/dispatch <task> <workdir> <prompt文件>` |
| 让已结束的 Codex session 再跑一轮 | `codex queue`，或 `interaction/bin/resume` |
| Codex 做完后让总控知道 | AgentConsole → `event from-agentconsole` → 事件队列，总控下次开工时验收 |
| 到某个时间点让 agent 去做事 | `interaction/bin/wake` |
| 定时跑纯代码（抓行情、发日报） | launchd plist |
| 程序给你发通知 | `reporter/bin/notify <log\|wechat\|alert>` |

## wake 用法
```sh
interaction/bin/wake add '2026-11-01T05:00+09:00' <codex-thread-uuid> prompt.txt --name earnings   # 在哪个目录执行 add，到点就在哪个目录跑
interaction/bin/wake add '05:00' <uuid> prompt.txt          # 东京时间；已过就顺延到明天
WAKE_DRY=1 interaction/bin/wake add '05:00' <uuid> prompt.txt --name dry   # 只记录要执行的命令，不真跑
interaction/bin/wake list
interaction/bin/wake cancel <id>
```
- 默认用 resume：不管有没有打开的客户端，都一定会跑一轮。queue 只保证消息入队；客户端没开时会不会被处理，目前没有可靠证据。
- 实测：10-30 的 dry 唤醒和真实唤醒都按时触发。11-07 重构后又用 dry 唤醒测了一次新路径：延迟 0.06 分钟，plist 已自动删除。
