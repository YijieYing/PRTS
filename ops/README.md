# ops：PRTS 自己加的工具与现成功能

本页的作用：分清哪些是 PRTS 为了让 Codex 和 Claude Code（cc）协作而新写的，哪些是 Codex、cc、macOS 本来就有的。新加工具时，在这里补一行。

## 一、现成功能（不是 PRTS 写的，PRTS 只是在调用）

| 来源 | 功能 | PRTS 用它做什么 |
|---|---|---|
| Codex CLI | `codex exec`：无界面跑一个任务；`-o` 把最后回复写到文件 | `dispatch.sh` 派发任务 |
| Codex CLI | `codex exec resume <thread>`：在已有 session 上接着跑一轮 | `retry_resume.sh` |
| Codex CLI | `codex queue --thread <id> --message`：给一个已有 session 排一条消息 | 总控给 aquant 等 session 追加任务 |
| Codex app-server | 线程读写 API | `codex_trim.py` 截断过长的 session |
| Claude 桌面 app / cc | session、分组、`search_session_transcripts`、`start_session`、`SendMessage`、`detach_session` | 总控管理和查找各个 session |
| cc | 自动记忆（`~/.claude/projects/*/memory/`）、`CLAUDE.md`、hooks | 全局规则和总控记忆 |
| macOS | launchd（定时、常驻）、`caffeinate`、`osascript` 通知 | 所有定时和常驻的东西都挂在 launchd 上 |
| CodexBridge 原仓库 | 微信收发、`/auto` 定时任务、秘书记录（`/remind` `/todo` …） | 微信入口 |

注意：Codex 和 cc 本身都**不会**在某个时间点自己醒来。session 只在收到消息时干活。

## 二、PRTS 新增

### 派发与回收（Codex ↔ 总控）
| 文件 | 加入日期 | 作用 |
|---|---|---|
| `dispatch.sh` | 10-20 | 用 `codex exec` 派发任务。关掉 stdin，确认真的启动了，并在 `registry.jsonl` 记 start 和 exit。报告写在 `jobs/<name>/last.md` |
| `registry.jsonl` | 10-20 | 所有派发、续跑、唤醒的事件日志，每行一个 JSON |
| `retry_resume.sh` | 10-22 | 用 `codex exec resume` 续跑；遇到 at capacity 就隔一段时间重试 |
| `on_event.sh` | 10-20 | AgentConsole 的事件处理器（在 `~/.agentconsole/config.json` 的 `on_event` 里配置）。派发任务结束、进程空闲太久、session 过期、主机不可达时，写一行到 `human/inbox.md`，严重的弹系统通知。**它不会唤醒总控**，要等你来找我时才处理 |
| `wake.sh` / `wake_run.sh` | 10-30（Codex 实现中） | 在指定时间唤醒一个 Codex session 去做事。用一次性 launchd 实现，补上「到点叫 agent」这一缺口 |
| `prompts/` | 10-20 | 给 Codex 的任务说明 |
| `jobs/` | 10-20 | 每个派发任务的日志和 `last.md` |
| `aquant-overnight/` | 10-20 | 夜间 supervisor：由 shell 控制轮次，Codex 干活 |

### 通知与提醒
| 文件 | 加入日期 | 作用 |
|---|---|---|
| `wechat-notify.sh` | 10-30 | 本机程序推送微信（包装 CodexBridge 的 `weixin notify`，这个命令也是 PRTS 加的，见下） |
| `unpushed_reminder.sh` | 10-21 | 备份插件的后置钩子：有超过 2 天没推送的提交时，在 inbox 记一行。不会自己推送 |

### 维护
| 文件 | 加入日期 | 作用 |
|---|---|---|
| `codex_trim.py` | 10-20 | 只保留 Codex session 的前 K 轮 |
| `lain-fix-lid-suspend.sh` | 10-18 | 修 lain 合盖后的日志刷屏 |
| `backups/` | — | 改全局配置前留的备份 |

### ops 以外的 PRTS 组件
| 位置 | 作用 |
|---|---|
| `~/PRTS/AgentConsole` | 全机 agent 监视：http://127.0.0.1:7788，launchd 常驻，产生事件交给 `on_event.sh` |
| `~/PRTS/Reporter` | 周报和 aquant 日报的收集、生成、发送 |
| `~/PRTS/human/` | 给你看的入口：报告、inbox、留言 |
| `~/PRTS/memory/` | 总控的记忆，只有总控写 |
| CodexBridge 本地分支 `fix/durable-weixin-replies` | 在原仓库之上加了：回复持久化、`weixin notify` 主动推送、秘书可起草 `/auto add`、`/auto` 一次性时间表、两个小修复。已向原仓库提议（issue #26），尚未合入 |

## 三、触发方式一览

| 想要的效果 | 用什么 |
|---|---|
| 派一个新任务给 Codex | `dispatch.sh` |
| 让已结束的 Codex session 再跑一轮 | `codex queue`，或 `retry_resume.sh` |
| Codex 做完后让总控知道 | AgentConsole → `on_event.sh` → inbox，总控下次开工时验收 |
| 到某个时间点让 agent 去做事 | `wake.sh`（以前没有，10-30 财报事故后补上） |
| 定时跑纯代码（抓行情、发日报） | launchd plist |
| 程序给你发微信 | `wechat-notify.sh` |
