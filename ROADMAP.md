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
| R1 | 🔨 | **question queue（总控主动提问）** | 第 1 步完成（11-12）：`reporter/bin/ask`，新增 timely 紧急度给杂务提醒用。送达：每小时由 launchd 运行 `reporter/bin/remind`，只在有问题时推送（11-12 从 Claude 定时任务改过来，因为后者每次跑完都会弹通知）；每晚回顾仍是 Claude 定时任务。原记录：送达走 Claude 定时任务（已创建：每小时提醒、每晚回顾），等第一次真实推送来验收。原计划：| 方案见 §三-R1。分三步：`reporter/bin/ask` 和开工时批量问 → 按紧急度推送 → 手机端回答。送达时机依赖 R2 |
| R2 | 🔨 | **用户状态模块 `pulse`** | v1 已实现（11-12）：`pulse day`、`check`、`now`；ChatGPT 从 Chrome 历史读，时间分 active 和 held。11-12 已接入 Codex Computer History（不和 agent 对话的时间也能看到，active 改为实测）。下一步：日报改成按时间线分段（11-12 用户要求）。设计稿 [pulse/README.md](pulse/README.md)。两件事：每日回顾，即有效时间花在输入、输出还是杂务上，学到和产出了什么（先做）；以及感知用户「现在」是否方便被打扰，比如离开、专注、空闲、休息时段。quiet hours、digest 时间这类用户属性归它，不写在 reporter 的 config 里。和 Ear 的区别：Ear 总结已经发生的事，pulse 只看当下。见 §三-R2 |
| R3 | ⏭ | **约 2026-11-21：清理过渡期** | 搜一遍还有没有人用 `~/PRTS/ops/` 的旧路径，没有就删掉 `ops/` 和全局 CLAUDE.md 里的旧路径提示。同时把 `AgentConsole` 改名为 `monitor`，原因见 §三-R3 |
| R4 | ✅ | **手机推送渠道不只靠微信** | 11-12 接入 Bark：`notify phone`，`alert` 改为 Bark + macOS。原记录： 微信受 24 小时 token 限制。11-12 实测：Claude 定时任务的 session 不连 Remote Control，也不能为它打开，所以 PushNotification 推不到手机，这条路排除。候选：Bark 或 ntfy（需要用户在手机上装 app 并给出 key）；macOS 通知（只在用户坐在电脑前时有用）。由 R2 判断此刻该用哪个渠道 |
| R5 | ❓ | **Codex 派发的沙盒选项** | dispatch 默认用 `workspace-write`，不能联网，也不能建本地 socket。NatureCalls 的 Unity 任务因此受阻。需要一个显式、需要用户批准的放宽方式 |
| R7 | ❓ | **实验：杂务交给 agent** | EchoAsRecord 实施、NatureCalls 对照，比较用户的体感和 pulse 测出的杂务时间。前提：pulse 每日回顾能按项目统计、EchoAsRecord 的架构底线确认、自检就位。设计见 [pulse/experiment-chore-ab.md](pulse/experiment-chore-ab.md) |
| R8 | 💤 | **pulse 接入 Ear（EchoAsRecord）的录音信息** | 11-12 用户提出，先记下。让每日回顾也能覆盖不在电脑前的时间：线下的课、组会、讨论，以及当时学到、讨论出了什么。待定：Ear 的产出放在哪、是什么格式（转写、摘要还是事件），要和 Ear 的 session 约定一个只读接口；录音里有别人的声音，回顾里只写用户自己的收获和结论，不写原话。和 R7 的实验同在 EchoAsRecord，接入时注意别把 pulse 的规则带进合作仓库 |
| R6 | ⏭ | **周报改用 `reporter/bin/notify`** | 不再经过 outbox 和 `/auto` 转发。等用户改掉 CodexBridge 里读 `Reporter/outbox` 的 `/auto` 任务以后，删掉 `reporter/outbox` 链接 |

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

### 总控与多 agent 协作
| # | 状态 | 事项 | 要点 |
|---|---|---|---|
| D1 | 💤 | 话题路由 | 主 session 判断当前话题是否属于某个子 session（比如 Codex 原理 → `research/LearnCodex`），并把后续讨论转过去。可参考 CodexBridge 在单个微信对话框里切换 thread 的做法（LearnCodex/notes/02） |
| D2 | 🔨 | 总控内部分工 | 10-19 的提案是按「状态 vs 推理」拆分，已基本落地：记录 = 文件 + git，单写者；执行 = `interaction/bin/dispatch` 加登记表；监督 = 事件触发；决策 = 总控加人。还差：用短命的子 agent 抽查 |
| D3 | 💤 | Agent 树状监视前端 | 以目录树为骨架，显示每个目录下的 agent、子 agent 和从属关系。前端问题，不急 |
| D4 | 💤 | 「已尝试」和「已验证」分开 | Codex 曾把「发出指令」当成「已成功」。候选做法：写成全局规则（`~/.codex/AGENTS.md`），但要先弄清它的加载机制（LearnCodex/notes/01）。现在只写进了 dispatch 的任务说明惯例 |
| D5 | 💤 | 调查现有技术 | 弄清 Codex、Claude Code 已有的 agent loop、上下文、调度、权限、恢复机制，画一张能力地图（附录 C 第一步）。形式：Codex 读开源代码即可 |

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
- 要改的地方：目录、launchd（`com.yijieying.agentconsole`、`com.agentconsole.backup`）、`~/.agentconsole/`、GitHub 仓库名，以及各处文档。用户 2026-11-09 同意，和 R3 的清理一起做。

## 四、已完成（最近的在上）
- 2026-11-07：PRTS 按 GLOSSARY 重构：`interaction/`、`reporter/`、`maintenance/`。新增 `wait`（派发者在任务结束时被唤醒）、事件队列（L0/L1/L2）、`notify` 分级。`human/inbox.md` 只由总控写。
- 2026-11-07：全局 CLAUDE.md 写入「写代码交给 Codex」，任何目录启动的 session 都能派 Codex。
- 2026-11-02：`memory/people.md`（身边的人、GitHub 账号对照）；Gmail connector 接通。
- 2026-10-30：`wake`（定时唤醒 Codex session）；`notify`（微信推送）；GLOSSARY v0.1。
- 2026-10-28：共享目录一致性（原设计问题 3）定为单写者 / 目录所有权，先用于研究层（`research/PRTS/AGENTS.md`），11-07 推广到 PRTS 各模块。
- 2026-10-20 至 10-22：dispatch 和登记表、AgentConsole 常驻监视、`resume`（满载重试）、周报、aquant 日报转发、对话备份。

### 决定不做
- aquant 日报的邮件兜底（用户 10-25 决定）。
- 自动刷新微信 token（用户 10-27 决定自己每天给 bot 发消息）。11-09 起改由 R4 解决「不只靠微信」。
