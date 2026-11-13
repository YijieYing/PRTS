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
| R1 | 🔨 | **question queue（总控主动提问）** | 第 1 步完成（11-12）：`reporter/bin/ask`，新增 timely 紧急度给杂务提醒用。送达：每小时由 launchd 运行 `reporter/bin/remind`，只在有问题时推送（11-12 从 Claude 定时任务改过来，因为后者每次跑完都会弹通知）；每晚回顾：11-13 写好了 `reporter/bin/recap`，由 launchd 在 23:40 运行 `pulse day` 并推送（`config/launchd/com.prts.reporter-recap.plist`）。11-13 用户已安装，Claude 任务 `prts-daily-recap` 已暂停。分类纠正改在任意 session 里告诉总控。最终所有推送都收到 Ear 手机端（R12）。原记录：送达走 Claude 定时任务（已创建：每小时提醒、每晚回顾），等第一次真实推送来验收。原计划：| 方案见 §三-R1。分三步：`reporter/bin/ask` 和开工时批量问 → 按紧急度推送 → 手机端回答。送达时机依赖 R2 |
| R2 | 🔨 | **用户状态模块 `pulse`** | v1 已实现（11-12）：`pulse day`、`check`、`now`；ChatGPT 从 Chrome 历史读，时间分 active 和 held。11-12 已接入 Codex Computer History（不和 agent 对话的时间也能看到，active 改为实测）。下一步：日报改成按时间线分段（11-12 用户要求）。设计稿 [pulse/README.md](pulse/README.md)。两件事：每日回顾，即有效时间花在输入、输出还是杂务上，学到和产出了什么（先做）；以及感知用户「现在」是否方便被打扰，比如离开、专注、空闲、休息时段。quiet hours、digest 时间这类用户属性归它，不写在 reporter 的 config 里。和 Ear 的区别：Ear 总结已经发生的事，pulse 只看当下。见 §三-R2 |
| R3 | ⏭ | **约 2026-11-21：清理过渡期** | 搜一遍还有没有人用 `~/PRTS/ops/` 的旧路径，没有就删掉 `ops/` 和全局 CLAUDE.md 里的旧路径提示。同时把 `AgentConsole` 改名为 `monitor`，原因见 §三-R3 |
| R4 | ✅ | **手机推送渠道不只靠微信** | 11-12 接入 Bark：`notify phone`，`alert` 改为 Bark + macOS。原记录： 微信受 24 小时 token 限制。11-12 实测：Claude 定时任务的 session 不连 Remote Control，也不能为它打开，所以 PushNotification 推不到手机，这条路排除。候选：Bark 或 ntfy（需要用户在手机上装 app 并给出 key）；macOS 通知（只在用户坐在电脑前时有用）。由 R2 判断此刻该用哪个渠道 |
| R7 | ❓ | **实验：杂务交给 agent** | EchoAsRecord 实施、NatureCalls 对照，比较用户的体感和 pulse 测出的杂务时间。前提：pulse 每日回顾能按项目统计、EchoAsRecord 的架构底线确认、自检就位。设计见 [pulse/experiment-chore-ab.md](pulse/experiment-chore-ab.md) |
| R8 | 🔨 | **Ear → pulse → 总控：录音里有价值的内容主动处理** | 11-13 用户要求今晚搭完整通路（口述笔记 `research/EchoAsRecord/local-notes/2026-11-13-夜间口述-下一步目标.md` 的第 1 件，用户定为最先做）。<br>设计：<br>1. `pulse ear sync` 每 10 分钟读旧 Ear 的库（只读），给每段录音分诊（用户自己的思考、课、组会算 high；别人闲聊算 low）。<br>2. high 的写进 inbox，并用 Bark 推送，标题就是内容。<br>3. 总控在后台挂着 `pulse ear wait`，一有内容就被唤醒，自己判断：总控直接处理（进 todo、ROADMAP 或记忆），派 Codex 做工程活，还是提议新开一个 Claude session。<br>4. 每日回顾加入「离开电脑的时间」，人和 agent 的时间线分开。<br>11-13 实现完成（9fee7c8、232b270）。用真实数据验收：18 段里，只有 00:42–02:05 的口述 5 段判为 high；对话、课、会议判为 normal，只进每日回顾；每天最多推送 4 条。总控已在后台挂上 `ear wait`。同步的 launchd（11-13 改为每 3 分钟一次）（`pulse/config/launchd/com.prts.pulse-ear.plist`）**等用户安装**。手机端仓库在 `~/research/octopus-flutter`（NextHCI/octopus-flutter），手机端只读调查（`interaction/state/tasks/flutter-survey/report.md`）的结论：app 的设置里本来就有「自动分段时间 5 分钟」，**不用改代码**。默认 30 分钟，改成 5 分钟以后，延迟估计能降到 10 分钟左右。要实测：说话人跨段的稳定性、耗电、旧 Ear 的负载（段数变成 6 倍）。改公共默认值之前，先和石伟男、shenxing 商量。<br>限制：录音按 20–30 分钟一段上传，所以延迟约 30–50 分钟；要真正实时，得改手机端（流式上传）。 |
| R9 | ❓ | **声纹归属修复** | 11-13 只读调查完成，报告在 `interaction/state/tasks/ear-voiceprint-survey/report.md`。声纹本身没丢，是两层原因：<br>1. **代码缺陷**：匹配器把模型版本号冻结在加载前（`@unknown`），之后用这个旧版本号去筛选候选，用户 15 个正式版本的声纹模板都被排除了。<br>2. **匿名音色抢先**：大量声音先匹配到了没有主人的匿名音色，只看第一名，所以不会落到 Yijie。审阅队列有 120 个待确认、1968 个在积累，09-29 之后没人确认过。<br>新仓库 ③ 只有事件框架，还没有匹配算法。11-13 用户决定：先看新 Ear 的 ③ 能不能解决，已交给「Ear 项目架构」session，它的回复：
- 新 Ear 的 ③ 暂时接不住，估计还要几天工程量。PR #16 已批准，但没合并；还缺登记表类型、常驻部署（journal 只支持 Linux）、确认音色的界面，以及阈值校准。
- ③ 也按 model_version 严格过滤，所以要先核对导入数据的版本。
- 想快速让旧 Ear 认出用户本人，最快的办法仍是报告 §7.1：在旧 Workspace 里绑定几个音色，不用改代码。
11-13 夜里旧 Ear 的版本缺陷已修复，在分支 `fix/speaker-model-version` 上，1140 项测试通过，没有合并、没有上线。迁移只演练了一遍：77 个正式模板保留，690 个缺模型身份凭据，1421 个建议用原音重算，可以直接改标签的为 0。报告在旧 Ear 仓库的 `doc/speaker-model-version-report.md`，上线前要用户同意。GPS 地点名：「GPS地理名字字段映射」session 的 PR #17 已合并（11-13），用的是地图 API 自动起名。手动命名和更正还没做，用户会自己告诉 Ear session。<br>最小修复：<br>- 先由用户在旧 Workspace 里确认几个近期确实是本人的音色；<br>- 再修版本缺陷，并和旧的 `@unknown` 模板一起迁移；<br>- 用历史片段重算质心（材料都在）。<br>改旧 Ear 的代码和服务要用户同意 |
| R10 | ✅ | **用户的待办接 Apple 提醒事项** | 11-13：`reporter/bin/todo add/list/done`，列表「PRTS」，会同步到 iPhone。只放用户自己要做的事；agent 的活进 ROADMAP 或派发任务。日程（Calendar）暂不接，带日期的提醒会自动出现在日历里 |
| R11 | 💤 | **推送策略像推荐系统一样学习** | 用户 11-13 口述：agent 要积极提问但控制数量，根据用户的回复调整，优先问用户更愿意回答的；利用周期性，比如「下周这个时候你会很累，提醒你去放松」；支付记录（如星巴克）可以作为信息源；各种权限（声音、屏幕、键盘、支付）让用户逐项勾选。11-13 先做了一步：推送标题直接用问题本身 |
| R12 | 💤 | **Mouth：给口述的语音反馈** | 用户 11-13 口述：边走边想、边口述设计文档时，希望 AI 用语音回应。最终所有推送都要收到 Ear 手机端 |
| R13 | 💤 | **Ear 手机端稳定性** | 用户 11-13 口述：长录音不能断，被系统杀掉后要自动重启，耗电（感觉录不满 24 小时）。手机端由「Octopus Flutter 音频提取与 EchoAsRecord 集成」session 负责；保活和耗电的现状见 `interaction/state/tasks/flutter-survey/report.md` §2–3（还没有同机耗电实测）。合作仓库，改公共行为前先和石伟男、shenxing 商量 |
| R14 | 💤 | **采集手机使用情况** | 用户 11-13 口述：手机上在用什么也要采集，可以截图传给电脑；他问电脑上那个「Activity 什么」能不能用在手机上，指的可能是 ActivityWatch 或 Codex Computer History，都没有 iOS 版。可行路线见 flutter-survey 报告 §5：Android 用 UsageStatsManager，iOS 用 Screen Time / DeviceActivity，限制很多。权限要用户逐项勾选（R11） |
| R15 | 💤 | **模型放服务器，不在本地部署** | 用户 11-13 口述：「Ollama 不好，我不想部署在本地」，并提醒「这个事情开始变重了，小心」。依赖第三台服务器（提醒事项里的「服务器装起来」）。用户自己要弄懂的问题已放进提醒事项：Ollama 单机并发能否同时加载多份模型参数 |
| R16 | 💤 | **ASR 常用词纠错，说话人结合环境判断** | Ear 的产品功能，11-13 已转给「Ear 项目架构」，由它在 EchoAsRecord 以 proposed 提案的形式提出。<br>① 常用词误识别，比如「Ear」被转成 year、Eer、夜：可以用纠错表或记忆让 LLM 改正，也可以按用户声音微调、做 embedding。PRTS 的 Ear 分诊已经在用 people.md、yyj.md 做纠错表。<br>② 说话人归属结合环境：例如「骑车时风声里的 A」，把内容、环境声、ASR、声纹合成一个多维判断。这是 R9 之后的扩展。<br>Ear 架构 session 的判断（11-13）：<br>- ① 值得写成提案，范围收窄为「用户词表」：转写本身只追加、不改，词表作为 ④ 的输入并登记依赖；按用户声音微调 ASR 只列为备选。<br>- ② 暂不提，等 ③ 跑起来再说。<br>- 另建议把「合并人物」提前进 MVP：新 ③ 会把用户本人的声音拆成很多未命名人物，和旧 Ear margin 不够是同一个问题。<br>11-13 Ear 架构 session 已在 EchoAsRecord 本地分支 `proposals/asr-glossary-person-merge`（8347e66）上写好三份 proposed 提案：`asr-user-glossary`、`person-merge-mvp`、`place-names-editable`（地名可改、一个地点可有多个别名）。还没推送，也没开 PR。 |
| R6 | 🔨 | **周报改用 `reporter/bin/notify`** | 双发已实现，等用户改 CodexBridge 后关 outbox。周报摘要走 `notify phone`，`weekly_outbox = true` 默认保留 outbox；用户改掉读 `Reporter/outbox` 的 `/auto` 任务后设为 false，兼容链接暂时保留 |
| R17 | ⏭ | **事件语义层过滤（slow path）** | 11-14 用户同意，依据见 [研究 session 的 PRTS 对照笔记](../research/DsHarness/local-notes/2026-11-14-PRTS对照与diff.md)。`interaction/bin/event` 现在只有纯规则的 fast path（`classify()`），新来源没规则可认时直接归 L0，等于当噪音丢掉。补一条 slow path：规则认不出的事件交模型判一次该不该进复核队列。`pulse/lib/ear.py` 的 `triage()` 已经是这个模式（prompt + `interaction/bin/run --output-schema` + 手写 schema 校验），这次是把它抽成共享库给 `event` 复用，不是重新发明。见 §三-R17 |
| R18 | ⏭ | **Thread / 订阅机制** | 11-14 用户同意，依据同上。dsh-superagent 的 Thread：同一个外部对象（PR、IM 话题）上的连续事件，一旦有 Worker 订阅，后续事件由程序直通，不再经总控决定转发给谁。PRTS 现在没有这样的外部事件源，也没有订阅登记，续接任务全靠总控手动 `wake`/`resume`。分四步，B0 是前提：B0 给 dispatch 开的 PR 接一个最小的 GitHub 轮询 Source；B1 登记 `{thread_key, task}` 订阅；B2 让匹配到订阅的事件自动 `codex queue` 给对应任务，绕开总控；B3（多个任务订阅同一个 thread）先不做。见 §三-R18 |

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

### R17 事件语义层过滤（slow path）
- 来源：研究 session 读完 DeepSeek Harness 的 `dsh-superagent` 设计文档后做的对照，用户 11-14 同意采用。
- 抽共享库：
  - `interaction/lib/run_model.py`：从 `pulse/lib/ear.py` 的 `triage()` 挪出"写 tempdir prompt+schema → 调 `interaction/bin/run --output-schema` → 校验 → 返回"这一串，参数化 prompt/schema/timeout；`ear.py` 改成调它，不留两份实现。
  - `interaction/lib/schema.py`：挪出现在手写的 `validate()`，两边共用。
- `interaction/bin/event` 加慢速分支：`classify()` 认不出的 `kind`，不再直接归 L0，改成调模型分类器；prompt 判断"要不要进复核队列"，schema 固定为 `{level: L0|L1|L2, reason: string}`，和 `classify()` 的返回契约一致，接入时不改调用方。
  - 只对白名单里的 `source` 启用，新配置 `interaction/config/filter.toml`（格式仿 `reporter/config/questions.toml`）；默认关闭，新来源要显式打开，防止意外烧 token。
  - 模型调用失败或超时，默认判 **L1**（不是 L0）：漏掉一件该管的事，比多问一句贵得多。
- 测试仿 `pulse/tests/test_ear.py` 和 `interaction/tests/test_modules.py` 的替身模式：给 `run_model.py` 一个假的 `bin/run`，覆盖"规则认不出 → 调模型 → 按 schema 落地"和"模型调用失败 → 退到 L1"两条路径。
- 文档：`interaction/README.md` 补慢速分支说明和 `filter.toml` 字段。

### R18 Thread / 订阅机制
- 来源同 R17。
- **B0（前提）**：最小的 GitHub 轮询 Source。新增 `interaction/lib/github_poll.py`（或脚本），按 launchd 定时跑，对 `registry.jsonl` 里出现过的 `cwd`（跑过 dispatch 的仓库），用 `gh pr list`/`gh pr view --json comments,statusCheckRollup` 查有没有新评论、CI 状态变化，和上次记录的游标（每个 PR 记 `updated_at`/评论数）做差，有变化就调 `interaction/bin/event add`，事件带上 `thread_key`（形如 `owner/repo#123`）。单独就有价值：PR 有新评论现在要自己去 GitHub 看，接上后至少进事件队列。
- **B1（订阅登记）**：dispatch 出去的任务一旦知道自己开了哪个 PR，记下 `{task, thread_key}`。倾向扫 `last.md`/`run.log` 里 `gh pr create` 产生的 URL 自动抓取，不改任务说明里的约定。新增只读查询 `interaction/bin/status threads`，列出 `{thread_key, task, thread_uuid}`。
- **B2（路由）**：`event add` 收到带 `thread_key` 的事件时先查有没有活着的订阅：有，且任务没被标记"人已经叫停"，直接 `codex queue --thread <uuid> --message <事件内容>`（已有原语，`interaction/lib/codex:93,122-123`），记一条 `routed` 事件留痕，不进 L1 队列。没有匹配，照常走 R17 的 fast/slow path。
- **B3（多对多）**：dsh 允许多个 Worker 订阅同一个 Thread；PRTS 目前一个任务一个 PR 够用，真的出现"两个任务碰到同一个 PR"再加，现在加是过度设计，不排期。
- B0 和 R17 可以并行；B1/B2 依赖 B0 先跑出真实的 `thread_key` 事件。

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
