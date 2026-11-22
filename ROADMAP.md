# PRTS 路线图 / Roadmap（2026-11-09 起，总控维护）

PRTS 要做什么、做到哪了，都以这一份为准。
- 2026-11-09 之前，这些计划分散在以下几处，现在已经合并到这里，原处只留指向本文件的链接：
  - `memory/prts.md`：「设计问题池」「AgentConsole 功能候选」「总控待办」「待讨论」；
  - `AgentConsole/README.md`：「方向」。
- 不在这里的：
  - 愿景和研究上的开放问题：用户写的背景文，`memory/prts.md` §1–§3、附录 B/C，不改动。
  - 研究线 E1–E5 的进度：[`~/research/PRTS/README.md`](../research/PRTS/README.md)，由研究统筹 session 维护。
  - 名词：[GLOSSARY.md](GLOSSARY.md)。
- 状态：✅ 已完成 · 🔨 进行中 · ⏭ 下一步 · 💤 以后再说 · ❓ 等用户决定。
- 编号一旦给出就不再改；完成或放弃的条目移到最后一节。

## 一、下一步（按顺序）

| # | 状态 | 事项 | 要点 |
|---|---|---|---|
| R1 | 🔨 | **question queue（总控主动提问）** | 第 1 步完成（11-12）：`reporter/bin/ask`，新增 timely 紧急度给杂务提醒用。送达：每小时由 launchd 运行 `reporter/bin/remind`，只在有问题时推送（11-12 从 Claude 定时任务改过来，因为后者每次跑完都会弹通知）；每日回顾：`reporter/bin/remind` 全天每小时 :07 按活动结束触发 `recap`，逻辑日 05:00 兜底，完整正文写备忘录，推送前 8 行；旧 recap 定时器需用户卸载、remind 需重新安装（命令见 reporter/README）。Claude 任务 `prts-daily-recap` 继续暂停。分类纠正改在任意 session 里告诉总控。最终所有推送都收到 Ear 手机端（R12）。原记录：送达走 Claude 定时任务（已创建：每小时提醒、每晚回顾），等第一次真实推送来验收。原计划：| 方案见 §三-R1。分三步：`reporter/bin/ask` 和开工时批量问 → 按紧急度推送 → 手机端回答。送达时机依赖 R2 |
| R2 | 🔨 | **用户状态模块 `pulse`** | v1 已实现（11-12）：`pulse day`、`check`、`now`；ChatGPT 从 Chrome 历史读，时间分 active 和 held。11-12 已接入 Codex Computer History（不和 agent 对话的时间也能看到，active 改为实测）。下一步：日报改成按时间线分段（11-12 用户要求）。设计稿 [pulse/README.md](pulse/README.md)。两件事：每日回顾，即有效时间花在输入、输出还是杂务上，学到和产出了什么（先做）；以及感知用户「现在」是否方便被打扰，比如离开、专注、空闲、休息时段。quiet hours、digest 时间这类用户属性归它，不写在 reporter 的 config 里。和 Ear 的区别：Ear 总结已经发生的事，pulse 只看当下。见 §三-R2 |
| R3 | ⏭ | **约 2026-11-21：清理过渡期** | 搜一遍还有没有人用 `~/PRTS/ops/` 的旧路径，没有就删掉 `ops/` 和全局 CLAUDE.md 里的旧路径提示。同时把 `AgentConsole` 改名为 `monitor`，原因见 §三-R3 |
| R4 | ✅ | **手机推送渠道不只靠微信** | 11-12 接入 Bark：`notify phone`，`alert` 改为 Bark + macOS。原记录： 微信受 24 小时 token 限制。11-12 实测：Claude 定时任务的 session 不连 Remote Control，也不能为它打开，所以 PushNotification 推不到手机，这条路排除。候选：Bark 或 ntfy（需要用户在手机上装 app 并给出 key）；macOS 通知（只在用户坐在电脑前时有用）。由 R2 判断此刻该用哪个渠道 |
| R7 | ❓ | **实验：杂务交给 agent** | EchoAsRecord 实施、NatureCalls 对照，比较用户的体感和 pulse 测出的杂务时间。前提：pulse 每日回顾能按项目统计、EchoAsRecord 的架构底线确认、自检就位。设计见 [pulse/experiment-chore-ab.md](pulse/experiment-chore-ab.md) |
| R8 | 🔨 | **Ear → pulse → 总控：录音里有价值的内容主动处理** | 11-13 用户要求今晚搭完整通路（口述笔记 `research/EchoAsRecord/local-notes/2026-11-13-夜间口述-下一步目标.md` 的第 1 件，用户定为最先做）。<br>设计：<br>1. `pulse ear sync` 随 reporter remind 读取新 Ear 的逐句转写（只读，source=old 保留旧库兼容），给每段录音分诊（用户自己的思考、课、组会算 high；别人闲聊算 low）。<br>2. high 的写进 inbox，并用 Bark 推送，标题就是内容。<br>3. 总控在后台挂着 `pulse ear wait`，一有内容就被唤醒，自己判断：总控直接处理（进 todo、ROADMAP 或记忆），派 Codex 做工程活，还是提议新开一个 Claude session。<br>4. 每日回顾加入「离开电脑的时间」，人和 agent 的时间线分开。<br>11-13 实现完成（9fee7c8、232b270）。用真实数据验收：18 段里，只有 00:42–02:05 的口述 5 段判为 high；对话、课、会议判为 normal，只进每日回顾；每天最多推送 4 条。总控已在后台挂上 `ear wait`。11-16 同步改为复用 reporter remind（先 sync 再 check）和 recap（先 sync --no-notify 再 day），删除独立 Ear 定时模板；新来源真实冒烟待总控在沙箱外核实。手机端仓库在 `~/research/octopus-flutter`（NextHCI/octopus-flutter），手机端只读调查（`interaction/state/tasks/flutter-survey/report.md`）的结论：app 的设置里本来就有「自动分段时间 5 分钟」，**不用改代码**。默认 30 分钟，改成 5 分钟以后，延迟估计能降到 10 分钟左右。要实测：说话人跨段的稳定性、耗电、旧 Ear 的负载（段数变成 6 倍）。改公共默认值之前，先和石伟男、shenxing 商量。<br>限制：录音按 20–30 分钟一段上传，所以延迟约 30–50 分钟；要真正实时，得改手机端（流式上传）。 |
| R9 | ❓ | **声纹归属修复** | 11-13 只读调查完成，报告在 `interaction/state/tasks/ear-voiceprint-survey/report.md`。声纹本身没丢，是两层原因：<br>1. **代码缺陷**：匹配器把模型版本号冻结在加载前（`@unknown`），之后用这个旧版本号去筛选候选，用户 15 个正式版本的声纹模板都被排除了。<br>2. **匿名音色抢先**：大量声音先匹配到了没有主人的匿名音色，只看第一名，所以不会落到 Yijie。审阅队列有 120 个待确认、1968 个在积累，09-29 之后没人确认过。<br>新仓库 ③ 只有事件框架，还没有匹配算法。11-13 用户决定：先看新 Ear 的 ③ 能不能解决，已交给「Ear 项目架构」session，它的回复：
- 新 Ear 的 ③ 暂时接不住，估计还要几天工程量。PR #16 已批准，但没合并；还缺登记表类型、常驻部署（journal 只支持 Linux）、确认音色的界面，以及阈值校准。
- ③ 也按 model_version 严格过滤，所以要先核对导入数据的版本。
- 想快速让旧 Ear 认出用户本人，最快的办法仍是报告 §7.1：在旧 Workspace 里绑定几个音色，不用改代码。
11-13 夜里旧 Ear 的版本缺陷已修复，在分支 `fix/speaker-model-version` 上，1140 项测试通过，没有合并、没有上线。迁移只演练了一遍：77 个正式模板保留，690 个缺模型身份凭据，1421 个建议用原音重算，可以直接改标签的为 0。报告在旧 Ear 仓库的 `doc/speaker-model-version-report.md`，上线前要用户同意。GPS 地点名：「GPS地理名字字段映射」session 的 PR #17 已合并（11-13），用的是地图 API 自动起名。手动命名和更正还没做，用户会自己告诉 Ear session。<br>最小修复：<br>- 先由用户在旧 Workspace 里确认几个近期确实是本人的音色；<br>- 再修版本缺陷，并和旧的 `@unknown` 模板一起迁移；<br>- 用历史片段重算质心（材料都在）。<br>改旧 Ear 的代码和服务要用户同意 |
| R10 | ✅ | **用户的待办接 Apple 提醒事项** | 11-13：`reporter/bin/todo add/list/done`，列表「PRTS」，会同步到 iPhone。只放用户自己要做的事；agent 的活进 ROADMAP 或派发任务。日程（Calendar）暂不接，带日期的提醒会自动出现在日历里 |
| R11 | 💤 | **推送策略像推荐系统一样学习** | 用户 11-13 口述：agent 要积极提问但控制数量，根据用户的回复调整，优先问用户更愿意回答的；利用周期性，比如「下周这个时候你会很累，提醒你去放松」；支付记录（如星巴克）可以作为信息源；各种权限（声音、屏幕、键盘、支付）让用户逐项勾选。11-13 先做了一步：推送标题直接用问题本身 |
| R12 | 💤 | **Mouth：给口述的语音反馈** | 用户 11-13 口述：边走边想、边口述设计文档时，希望 AI 用语音回应。最终所有推送都要收到 Ear 手机端 |
| R13 | 💤 | **Ear 手机端稳定性** | 用户 11-13 口述：长录音不能断，被系统杀掉后要自动重启，耗电（感觉录不满 24 小时）。手机端由「Octopus Flutter 音频提取与 EchoAsRecord 集成」session 负责；保活和耗电的现状见 `interaction/state/tasks/flutter-survey/report.md` §2–3（还没有同机耗电实测）。合作仓库，改公共行为前先和石伟男、shenxing 商量。11-14 用户定位：手机只是录音加 GPS 的工具，可以换成更简单的固件；Ear 的价值在电脑上用 agent 通过 MCP 查，不追求实时，离线后能补传就够。新采集端 EarRecorder（iOS）已加入扫码配对、Bonjour 局域网发现，以及经 `vps.shiweinan.com:6950` 的加密中继；最该先验证的是离线一天后能否补齐、agent 能否看出数据同步到几点。整理稿：`~/research/EchoAsRecord/local-notes/2026-11-14-下午-EarRecorder联调与产品定位.md` |
| R14 | 💤 | **采集手机使用情况** | 用户 11-13 口述：手机上在用什么也要采集，可以截图传给电脑；他问电脑上那个「Activity 什么」能不能用在手机上，指的可能是 ActivityWatch 或 Codex Computer History，都没有 iOS 版。可行路线见 flutter-survey 报告 §5：Android 用 UsageStatsManager，iOS 用 Screen Time / DeviceActivity，限制很多。权限要用户逐项勾选（R11） |
| R15 | 💤 | **模型放服务器，不在本地部署** | 用户 11-13 口述：「Ollama 不好，我不想部署在本地」，并提醒「这个事情开始变重了，小心」。依赖第三台服务器（提醒事项里的「服务器装起来」）。用户自己要弄懂的问题已放进提醒事项：Ollama 单机并发能否同时加载多份模型参数 |
| R16 | 💤 | **ASR 常用词纠错，说话人结合环境判断** | Ear 的产品功能，11-13 已转给「Ear 项目架构」，由它在 EchoAsRecord 以 proposed 提案的形式提出。<br>① 常用词误识别，比如「Ear」被转成 year、Eer、夜：可以用纠错表或记忆让 LLM 改正，也可以按用户声音微调、做 embedding。PRTS 的 Ear 分诊已经在用 people.md、yyj.md 做纠错表。<br>② 说话人归属结合环境：例如「骑车时风声里的 A」，把内容、环境声、ASR、声纹合成一个多维判断。这是 R9 之后的扩展。<br>Ear 架构 session 的判断（11-13）：<br>- ① 值得写成提案，范围收窄为「用户词表」：转写本身只追加、不改，词表作为 ④ 的输入并登记依赖；按用户声音微调 ASR 只列为备选。<br>- ② 暂不提，等 ③ 跑起来再说。<br>- 另建议把「合并人物」提前进 MVP：新 ③ 会把用户本人的声音拆成很多未命名人物，和旧 Ear margin 不够是同一个问题。<br>11-13 Ear 架构 session 已在 EchoAsRecord 本地分支 `proposals/asr-glossary-person-merge`（8347e66）上写好三份 proposed 提案：`asr-user-glossary`、`person-merge-mvp`、`place-names-editable`（地名可改、一个地点可有多个别名）。还没推送，也没开 PR。 |
| R6 | 🔨 | **周报改用 `reporter/bin/notify`** | 双发已实现，等用户改 CodexBridge 后关 outbox。周报摘要走 `notify phone`，`weekly_outbox = true` 默认保留 outbox；用户改掉读 `Reporter/outbox` 的 `/auto` 任务后设为 false，兼容链接暂时保留 |
| R17 | ✅ | **事件语义层过滤（slow path）** | 已接上真实来源入口：event add 与 AgentConsole 共用五步 classify；模型输出 level/project/null/reason，包含 pulse 定义及项目列表，失败 L1。白名单默认仍关闭，未调用真实模型验收。见 §三-R17 |
| R18 | ✅ | **Thread / 项目组订阅（个人版）** | 11-15 完成 A–F：统一字段/aliases，B0 四缺口修复，项目与 thread 多订阅、暂停、路由幂等、worktree PR 自动登记，Ear/Computer History 接入，status threads JSON 与 review 契约。Claude 为 outbox + L1 待转发；仅替身验证投递，未安装 launchd，未向真实线程 queue。见 interaction/README.md 与任务报告 |
| R19 | 💤 | **提前行动（投机执行，DS §3.4）** | 用户 11-14：DS 的例子是提前草拟回复邮件；用户的例子是「看到我在上课，就去清华网络学堂把这节课的课件拉到对应目录」。见 §三-R19 |
| R20 | 💤 | **链式召回实验（DS §3.3）** | 用户 11-14：和研究层 E2「上下文压缩 = 页面置换，存根把静默缺页变成显式缺页」最相关，可以设计实验。归研究层，见 §三-R20 |
| R21 | 💤 | **全双工 agent loop（DS §4.1）** | 用户 11-14：Codex 似乎已经能做到。总控核对（11-14）：本机 Codex 的 app-server 协议里有 `turn/steer`（往正在跑的 turn 里注入输入）和 `turn/interrupt`；PRTS 现在只用 `codex queue`（排到下一轮）。待验证 steer 能不能在工具调用还没返回时让模型看到新消息 |
| R22 | 💤 | **手机上看电脑上的页面** | 用户 11-15 提出：电脑上能看的东西，手机上最好也能看，但 AgentConsole、Ear 实时转写等前端现在都只在 localhost 上。总控建议：① 入口用 Cloudflare 命名隧道（用户自己的域名，每个服务一个子域名）加 Cloudflare Access（只允许用户的邮箱登录）。这样手机上不用装东西，也不和 Shadowrocket 冲突。Tailscale 不合适，因为 iOS 同一时间只能开一个 VPN。② 页面改成 PWA，可以添加到主屏幕。③ 推送继续用 Bark，日报全文继续放备忘录。④ Ear 的实时转写直接显示在 EarRecorder app 里，交给 Ear 那边做。安全要求：AgentConsole 上有操作按钮，公网进来默认只读、操作要二次确认，Access 只允许一个人。Cloudflare 登录、授权、Access 设置由用户来做；cloudflared 的常驻服务由用户安装。还没开工 |
| R23 | 💤 | **Eye：自建的「电脑上在做什么」采集，替代 Codex Computer History** | 用户 11-16 提出：要一个功能和能耗都与 Computer History 差不多的替代品。参照：Computer History 的服务占 CPU 约 0.1–1.5%、内存约 50 MB，原始事件流约 4 MB/小时，记录应用、窗口标题、URL、键鼠事件和 ax 文本；见 pulse/README §二。命名：用户提议叫 Eye，以后 AI 眼镜的链路也可能叫 eye。总控建议照 Ear 的做法，**Eye 是一个模块，下面挂多个采集源**：Mac 屏幕活动是第一个源，以后眼镜是另一个源；就像 Ear 下面有手机，也可以接简单固件。**用户 11-16 要求：Eye 要接进新 Ear 的总线结构**：采集结果作为原始数据只追加写入 Ear ①，用 ② adapters 的方式接入，其他模块通过 ① 的事件来消费；不另起一套存储。这样 pulse、日报、R18 的 thread 都能从同一处读到电脑活动和录音。要先弄清楚：① 现有的 raw record 类型能否承载窗口和键鼠事件，还是要新增类型（改 contracts 要走 Ear 的提案流程）；隐私边界，例如是否采集打字正文和 ax 文本，pulse 现在是不读这两样的；采集用的系统权限（辅助功能、屏幕录制）由用户逐项授权。还没开工 |
| R24 | 💤 | **pulse 改为读新 Ear 的活动层，不再自己分诊** | 用户 11-16 问：为什么读新 Ear 要读逐句转写，Ear 数据库的设计不是为了让 agent 更快、更省 token 地取录音信息吗。总控的回答：Ear 的设计确实是让 agent 读 ③ 活动（名称和描述）和 ④ 按规则提取的产物，需要原话时再用 `find_evidence` 按需取；但 ③④ 还没和 ① 联调上线，现在能读的只有原始转写，所以 pulse 暂时自己分诊。分诊用的是 Codex 的额度，每 30 分钟一次调用；总控只读分诊结果，不读转写。等 ③④ 上线后，pulse 改为读活动和产物，去掉自己的分诊，避免和 Ear 重复建模。依赖 Ear 那边的进度。11-20 19:30 用户（在「EAR录音执行与反馈」）提议把判断是否推送的 high/low 并进新 Ear ④ 的输出，并问 Ear 做好后是否还需要 pulse；该 session 建议：客观判断进 ④，推不推是通知策略、放送达侧，pulse 缩成消费方（保留「现在」/focus 和汇报）。用户尚未拍板 |
| R25 | 🔨 | **token 统计与优化** | 用户 11-18 02:41 口述（Ear）：近期技术优化重点转向统计并降低 Claude/Codex 的 token 消耗——统计每次调用的 token 数和合理性、按周出优化报告，AgentConsole 能按天/周看每个 thread 的用量。11-19 用户要求监控整机 token，并用于对比不同 agent 架构的开销（例：Ear 让 Codex 直接读原始数据 vs 用我们的数据格式读；E2 上下文实验还没做完）。第 1 步已派 Codex（任务 `token-meter`）：`interaction/bin/tokens` 增量账本、按天/项目/agent/任务/实验标签汇总，dispatch `--tag`，日报 token 节，AgentConsole `/api/tokens`（前端总控写）。之后：每周优化报告、调用合理性判断。和 M5（额度统计与路由）合并考虑。11-19 22:46 口述补充：log 要细到每次调用、每条逻辑路径、每个请求（含上下文）各花多少 token，从底层理解，这对整个 agent 架构都重要；见 D8 |

## 二、以后再说（候选池）

### monitor（AgentConsole）能力
| # | 状态 | 事项 | 要点 |
|---|---|---|---|
| M1 | 💤 | 检测「agent 在等人」 | Codex 的审批请求、Claude 的 blocked 提问 → L2。最直接节省人的注意力。和 R1 合并考虑：它们都是在等人回答的问题 |
| M2 | 💤 | 冲突检测 | 同一个 git 根目录或分支上有两个以上 agent 同时处于 working → L1 |
| M3 | 💤 | 卡死检测 | 已登记的派发任务进程还活着，但 rollout 10 分钟没有增长 → L2。对应 10-19 stdin 卡住的那次事故 |
| M4 | 🔨 | 派发任务自动验收 | 已有：`wait` 唤醒派发者、事件队列。还差：任务结束后自动起一个验收 agent |
| M5 | 💤 | 额度统计与路由 | 按 provider 统计用量（5 小时限额），决定派给谁 |
| M6 | 💤 | 每日摘要 | 用一条汇总代替多条零散提醒；和 R1 的 digest 合并 |
| M7 | 💤 | 项目登记表 | session → 项目 → human 入口，是 D1 话题路由的数据基础。现有 `human/projects.toml` 只给周报分类用 |
| M8 | 💤 | 从观察走向协作和干预 | 任务目录（`goal.md`、`plan.yaml`、`claims.md`、`evidence/`、`human/`、`STOP`），以及五个干预操作：打开证据、要求复现、提反例、改目标、在检查点停止。参考 QED 的文件协议（用户 10-28 同意借 QED、不用 LibreChat）。Claude 的建议：和果蝇 autoresearch 绑在一起做，先做真值考场。详见 [可行性评估](human/reports/2026-10-28-agentconsole-autoresearch-feasibility.md)。顺序未定 |
| M9 | 💤 | `human/` 修改监视 | 发现 `human/` 有未提交的改动时，产生「人类修改」事件。总控自己的改动会立刻提交，所以不会循环 |
| M10 | ✅ | 界面右侧换成「主线任务进度」 | 11-15 已实现（AgentConsole 8360608、08917a6，数据来自 `interaction/bin/status threads --json`），已配置上线；未做浏览器截图验收。原始需求： 用户 11-14 22:10 口述（新 Ear 录音，转写把 AgentConsole 听成了 "Agent Council"）：左侧 session 列表保留，右侧的 session 详情没什么用，换掉或去掉。改为按 thread 展示：每个主线任务推进到哪一步、哪个 agent 在做什么、推进的部分里哪些用户审查过、哪些没有。数据契约已就绪（见 interaction/README）：status threads --json 提供项目/thread、订阅、任务和 reviewed，review/--undo 写验收状态 |
| M11 | ✅ | 工程时间线（甘特）、排序与 DDL 提醒 | 11-17 完成：AgentConsole c40c9e6，PRTS 9992bf7、083443e（DDL 提醒合并），roadmaps b708700 + 总控审核 8e79784；已配置 roadmap_mark 并重启，浏览器验过时间线和展开甘特。原始记录：用户 11-17 提出并同意，派 Codex：m11-roadmaps、m11-data、m11-console，契约见 interaction/state/prompts/m11-contract.md。各工程 roadmap 统一放在 human/roadmaps/，总控审核文字。用户给的 DDL：OS 第 8 章独立实现 11-30（代码在 lain），综合训练大作业 12-18，NatureCalls 12-21；研究类没有硬截止，果蝇组会每周四 15–17，Ear 组会每周四 17–19。① 每个工程的 roadmap 条目带开始日期和 DDL，右侧每个工程一行画迷你时间线，展开后按条目画甘特条。② 大项目可折叠。③ 排序：手动拖动表示重要性，大项目之间可拖，工程只能在同一大项目内拖；自动排序按最近 DDL，先排大项目（大项目 DDL = 下属工程中最近的 DDL），再排工程；无 DDL 的排在后面。④ DDL 临近时由每小时的 remind 推送提醒。⑤ roadmap 节点完成可以手动标，也可以由 agent 按派发、验收和 PR 状态自动标。前置：PRTS 研究、DigitalFly、SomaNet、NatureCalls、OS 课、芯动等工程先提炼出可解析的 roadmap。|

### 总控与多 agent 协作
| # | 状态 | 事项 | 要点 |
|---|---|---|---|
| D1 | 💤 | 话题路由 | 主 session 判断当前话题是否属于某个子 session（比如 Codex 原理 → `research/LearnCodex`），并把后续讨论转过去。可参考 CodexBridge 在单个微信对话框里切换 thread 的做法（LearnCodex/notes/02） |
| D2 | 🔨 | 总控内部分工 | 10-19 的提案是按「状态 vs 推理」拆分，已基本落地：记录 = 文件 + git，单写者；执行 = `interaction/bin/dispatch` 加登记表；监督 = 事件触发；决策 = 总控加人。还差：用短命的子 agent 抽查 |
| D3 | 💤 | Agent 树状监视前端 | 以目录树为骨架，显示每个目录下的 agent、子 agent 和从属关系。前端问题，不急 |
| D4 | 💤 | 「已尝试」和「已验证」分开 | Codex 曾把「发出指令」当成「已成功」。候选做法：写成全局规则（`~/.codex/AGENTS.md`），但要先弄清它的加载机制（LearnCodex/notes/01）。现在只写进了 dispatch 的任务说明惯例 |
| D5 | 💤 | 调查现有技术 | 弄清 Codex、Claude Code 已有的 agent loop、上下文、调度、权限、恢复机制，画一张能力地图（附录 C 第一步）。形式：Codex 读开源代码即可 |
| D6 | 💤 | 日报给学习时间块出题检验 | 用户 11-17 03:09 口述（新 Ear）：日报记了「学到」，但很多东西看了其实没学会；只要是学习的时间块，就出题检验有没有学到。不是所有看过的都要学会，所以只对学习类时间块出题。可接 pulse 的「输入·学到」分类和 R19 提前行动 |
| D7 | 💤 | 人在回路里的位置 | 用户 11-19 16:58 口述（Ear，说话人不确定）：系统设计要给人的参与留足位置，不只追求全自动；评测 agent 时把人与 agent 的协同纳入建模。可作为 R7 实验和研究层评测的设计原则，先等用户确认是他本人说的。11-19 22:49 用户本人口述了相近的意思：能自动执行的都应自动执行；工程里哪些事 agent 能做、哪些要人做，要在 AgentConsole（转写作 Agent Council）前端里区分清楚，这是前端的重要部分 |
| D8 | 💤 | PRTS 实验做成一作论文 | 用户 11-19 22:46 口述（Ear）：PRTS 的实验要更严谨、更有设计、更有趣，考虑写成一作；先把实验设计和方法定下来。素材：R25 token 计量（逐调用/逐路径/含上下文）、E2 上下文实验、Ear 读原始数据 vs 读我们的数据格式、R7 等。另：自动化的筛选标准「产出没人看也没人用就是坏的」已落成 usage-audit（只判测得到的功能）。等用户有空一起定设计 |

## 三、展开说明

### R1 question queue
- 已定（2026-11-02）：
  - 问题对象和 `human/questions.md` 视图；
  - 「值不值得问」的规则：查得到的不问；写不出 default 就不问；不急的攒着问；
  - 按紧急度扫描：blocking 每 30 分钟，soon 每天，whenever 等下次开 session；
  - 每批最多 3 条，除非全部都是「干活之前必须解决」；
  - 研究记录：outcome、回答用时、批量大小、`default_ok`；
  - 队列、送达、收答案都归 reporter；总控只决定问不问、拿答案做什么。
- 结构：
  - `reporter/bin/ask`（给 agent 和脚本用的接口，不是给用户的）；
  - `reporter/lib/questions.py`；
  - `reporter/state/questions.jsonl`（只追加：`created / delivered / opened / answered / closed`）。
- 11-12 新增一类问题来源：pulse 发现用户在杂务上花的时间太多时，提醒用户把具体事项交给 agent（见 pulse 设计稿 §三）。
- 用户的入口只有三个：session 里的提问框、编辑 `human/questions.md`、手机上回答（R4 定渠道以后；如果用微信，就是 CodexBridge 的 `/答 Q12 …`）。
- 提问的 session 可以在后台跑 `ask wait Q12`，用户回答后会被唤醒，用法和 `interaction/bin/wait` 一样。
- 分三步：
  1. `ask` 加测试，开工流程加一步；
  2. 定时扫描和推送，送达时机问 R2；
  3. 手机端回答。

### R2 用户状态模块 `pulse`（2026-11-09 用户定名）
- 2026-11-12：用户提出先做每日回顾，并定义了输入、输出、杂务三类，详见设计稿 [pulse/README.md](pulse/README.md)。下面是 11-09 时的设想，仍然适用于「现在」那部分。
- 管什么：用户此刻的可打扰程度，以及与此相关的个人属性，比如休息时段、习惯在什么时间看 digest。这些属性归用户，不归任何一个功能模块。
- 可能的信号：
  - Mac 的键鼠空闲时间、锁屏、专注模式；
  - 前台应用，例如会议软件；
  - 日历上的忙碌时段；
  - 用户对历史提问的响应时间（从 R1 的数据学习）；
  - 用户手动设置的「别打扰到 X 点」。
- 对外接口（设想）：`pulse now` 返回状态、开始时间、置信度；`pulse next-available` 返回下次可能方便的时间。reporter 推送前先问它。
- 定名经过：用户否决了 `presence`；`rhythm`（偏作息规律）、`focus`（太窄）、`status`（和 `interaction/bin/status` 撞名）也没选。

### R3 AgentConsole 改名为 monitor
- 起因：2026-10-30 讨论模块化时，用户把总控说的「console」（指总控）误认为 AgentConsole。两个名字太像。
- 另外，它只观察、产生事件、不做判断，`monitor` 比 `Console` 更准确。GLOSSARY 已经把它的英文名写成 monitor。
- **11-19 用户口述（Ear 18:23–18:25）**：AgentConsole 太复杂、不好用，想按 项目 / 依赖 / 进度 / deadline / 个人状态 重新组织；统一文件结构、逻辑项目结构和 session 结构；恢复从前端跳到 session 的入口。改名时一起重新设计信息结构，先出方案给用户看再动手。
- 要改的地方：目录、launchd（`com.yijieying.agentconsole`、`com.agentconsole.backup`）、`~/.agentconsole/`、GitHub 仓库名，以及各处文档。用户 2026-11-09 同意，和 R3 的清理一起做。

### R17 事件语义层过滤（slow path）
- 已完成：共享 run_model/schema；event add 和 from-agentconsole 共用 classify。
- 五步：已知复核/紧急规则 → 有效订阅直通 → 已知噪声 L0 → 白名单模型 → 原默认级别。
- 模型输出 `{level, project: string|null, reason}`，提示包含 pulse §一及项目表；
  未归属允许 null，失败退到 L1。filter.toml 默认空白名单，建议来源 github_poll、ear_agent_work。
- 真实入口已接线，投递和模型行为以 fixture 验证；未启用真实模型过滤。

### R18 Thread / 订阅机制
- **B0 已完成**：GitHub PR 带 gh:owner/repo#N 与路径匹配项目；
  统计他人 comments、reviews、分页行内意见及 CI，当前 gh 账号缓存；
  首次/旧游标迁移只建基线，updatedAt 自身及自己评论不触发。事件进入 classify。
- **B1 已完成**：subscribe 按项目组或 thread 登记多个目标，追加日志加锁，
  pause/resume/remove；成功 worktree dispatch 从报告/日志 PR URL 自动登记到 Codex UUID。
  cwd 匹配项目不自动扩大订阅范围。
- **B2 已完成**：Codex queue；Claude 无接口，outbox + route_pending L1；
  失败或不确定投递保留 L1。稳定事件 ID 去重，每目标审计；暂停时按无订阅。
- **总控复核（11-14）四个缺口**：结构化 thread/project、reviews/行内意见、
  自己评论/更新时间去噪、接上 classify 均已修复。app Auto-fix 绑定不可探测，
  已绑定的 PR 不要再订阅 PRTS。
- **数据契约**：status threads --json 严格输出 F 字段，直接供 AgentConsole 调 CLI；
  review/--undo 追加验收状态。详情和边界见 interaction/README.md。

#### R18 个人版（用户 11-14）
- 主要来源 Computer History 与 Ear，GitHub 次之；fast path 同时丢噪声和直通。
- 项目 aliases 与 pulse 共用 projects.py。项目组可有多个 session/线程订阅。
- Ear high 段的 agent_work 以首段 capture 的 ear thread 发事件；
  check 的杂务提醒发 chore_streak，保持现有冷却/dry 约束。无订阅默认 L1。
- 验收边界：fixture/替身回归与真实只读 status；没有启用 launchd、真实 queue 或真实 gh 轮询。
- 交付报告：interaction/state/tasks/r18-threads/report.md。

### R19 提前行动
- 例子：用户在上课时，自动把这节课的课件从网络学堂拉到对应课程目录。
- **触发**：
  - 课表是确定性规则，走 fast path；
  - Ear 分诊的 `kind=class`、GPS 在教学楼可以作为确认信号；
  - 不靠模型猜「是不是在上课」。
- **动作**：下载课件是只读的，可逆，适合先做，结果只放进本地目录，不对外发任何东西。
- **前提**：网络学堂要登录。agent 不能代输密码，要由用户自己配置一次登录态（可参考开源的 thu-learn-lib / learnX 的做法），凭据不进 git。
- 原则沿用 DS：只先做「做错了也没代价」的准备工作，要对外的动作（发邮件、提交）仍然先问。

### R20 链式召回实验
- DS §3.3：上下文放不下时，把内容卡片截断、留一个 id 指针，模型需要时按 id 一跳一跳读回来。这对应研究层 E2 里的「存根」：E2 发现存根是最大的单一因素，链式召回相当于把一个存根换成可以多跳追溯的引用链。
- 可以设计的对照：单层存根 vs 带 id 的多跳链；看召回准确率、跳数，以及「该回读却没回读」（静默缺页）的比例。
- 实验设计归研究层（`~/research/PRTS`，E2/E4），由研究 session 写，这里只登记方向。

## 四、已完成（最近的在上）
- R5 ✅（2026-11-13）：**Codex 派发的沙盒选项**。dispatch / resume 支持显式 `--sandbox network` / `full`，必须附非空 `--approved-by`，start 事件记录沙盒与批准依据；默认不变，dry-run 与替身回归验证通过，未实际派发放宽沙盒的任务。用法见 [interaction/README.md](interaction/README.md)。
- 2026-11-07：PRTS 按 GLOSSARY 重构：`interaction/`、`reporter/`、`maintenance/`。新增 `wait`（派发者在任务结束时被唤醒）、事件队列（L0/L1/L2）、`notify` 分级。`human/inbox.md` 只由总控写。
- 2026-11-07：全局 CLAUDE.md 写入「写代码交给 Codex」，任何目录启动的 session 都能派 Codex。
- 2026-11-02：`memory/people.md`（身边的人、GitHub 账号对照）；Gmail connector 接通。
- 2026-10-30：`wake`（定时唤醒 Codex session）；`notify`（微信推送）；GLOSSARY v0.1。
- 2026-10-28：共享目录一致性（原设计问题 3）定为单写者 / 目录所有权，先用于研究层（`research/PRTS/AGENTS.md`），11-07 推广到 PRTS 各模块。
- 2026-10-20 至 10-22：dispatch 和登记表、AgentConsole 常驻监视、`resume`（满载重试）、周报、aquant 日报转发、对话备份。

### 决定不做
- aquant 日报的邮件兜底（用户 10-25 决定）。
- 自动刷新微信 token（用户 10-27 决定自己每天给 bot 发消息）。11-09 起改由 R4 解决「不只靠微信」。
