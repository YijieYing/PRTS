# PRTS — Personal Runtime System
## 项目愿景、问题背景与研究思路同步

**更新日期：2026-10-18**

**性质：长期项目背景与研究备忘录，不是已经冻结的需求文档。**

本文汇总我与 GPT 围绕 Chronos、Jarvis、PRTS、Agentic OS、Human-Agent Interaction 以及 Multi-Agent Systems 的讨论。目的是让 Claude 理解项目为什么出现、我真正希望解决什么问题、已经作出了哪些选择，以及哪些问题依然开放。

请特别注意：**不要把文中所有候选机制视为已经确定的架构。** 我希望先理解已有技术与理论、建立真实的验证场景，再决定值得自己实现的部分。

---

# 〇、速读与工作进度（由 Claude 维护）

> 新会话只读这一节就够了。下面一到三章和附录是背景材料，用到哪部分再按章节去读，不要整篇读（全文约 37KB，很耗上下文）。

**一句话**：当 Agent 已经能承担长期任务时，需要什么样的系统机制，才能让自主执行、共享状态、资源管理和人类决策可靠地协同？关键资源是人类注意力。

**研究总纲（2026-10-28 用户确认）**：人的精力有限，而 agent 的产出速度已超过人能处理的速度。E1–E5 都是它的一部分，评价标准待讨论。

**已定**（详见附录 A）：
- 利用现有 Agent，不自研 Agent Loop。
- 24h 不等于持续推理。
- 人类注意力、决策边界和任务状态是核心问题。
- 分阶段实现，每轮都有可以手测的最小目标。
- 用证据评价，而不是用总结评价。

**分工**：
- GPT：学术讨论和研究问题定义。
- Claude：工程实现和具体问题。
- Codex：具体编码执行。
- Human_Work 备忘录：人工维护（这是对 human/agent 边界的一次实践）。

**当前阶段**：在真实任务上实践总控台（派发 Codex、抽查、记忆分区），同时设计实验 E1 来检验 agent OS 的价值。

## 进度日志

| 日期 | 事项 |
|---|---|
| 2026-10-18 | 建立 `~/PRTS/` 工作区（git）。prts.md 和 yyj.md 移入，原位置改为软链接。确定文件分工：prts.md 记录 PRTS 进度，yyj.md 记录对用户的了解。 |
| 2026-10-18 | 第一次同步就用掉了 9% 上下文：整篇读 prts.md，还因为 cat 输出被截断重读了一次。**这是第一个真实的观测：上下文成本问题。** 对策：增加本节，供新会话速读。 |
| 2026-10-18 | 我主动检查了 lain 的存储，属于**L2 事件**：`/var/log/auth.log*` 占了 159G。原因是笔记本合盖，logind 默认要挂起，但 suspend.target 被 mask 了，于是每秒反复重试挂起并写日志，每小时约 0.85G。剩余空间大约 2.5 天会写满。修复需要 sudo，已交给用户执行。这是一个“Agent 发现问题 → 升级给人”的真实样例。 |
| 2026-10-18 | lain 已修复：用户在 Terminal 面板里自己输入 sudo 密码，Claude 执行了 `ops/lain-fix-lid-suspend.sh`，把合盖动作改为忽略，并过滤掉日志刷屏行（真实登录记录保留）。过滤后 auth.log 从 159G 降到约 450K。**观测**：“已跑完”的口头报告早于真实完成（这次来自人，不是 Agent）；Claude 读终端输出发现还在运行，再次印证附录里“证据 > 声明”的原则；另外脚本对 19G 文件做 `wc -l`，设计得不好。 |
| 2026-10-19 | 第一次横向分工实验：总控 Claude 向 Codex（`codex exec`）派发两个调研任务：AGENTS.md 加载与上下文机制，以及 CodexBridge 的 thread 路由。任务、prompt 和产出归档在 `~/research/LearnCodex`（独立 git 仓库，`codex-src/` 为 rust-v0.155.1 源码）。 |
| 2026-10-19 | 两个 Codex 任务都已完成，Claude 抽查了 6 处源码引用，全部属实。要点：Codex 只在会话开始时读一次 AGENTS.md，之后用缓存（以环境选择和信任级别为键，不看文件 mtime/hash），所以已有会话看不到文件更新；自动压缩阈值约为窗口的 90%；子 agent 共享同一个目录，但没有文件锁，也没有文件变更广播；CodexBridge 不会按话题自动切换 thread，只能靠显式命令。**分工观测**：Codex 适合“有明确交付物、只读调研、需要写源码引用”的任务；Claude 负责派发、抽查和汇总。总控只读了产出笔记（约 190 行），没读源码。 |
| 2026-10-20 | 第一次夜间实验，用“状态 vs 推理”的总控结构：`ops/aquant-overnight/supervisor.sh`（确定性的 shell 加 caffeinate），在 git worktree 中按轮运行 Codex 优化 aquant 的模拟策略，禁止任何下单；另派一个 Codex 做记账 MVP（`~/Projects/ledger`，用官方账单导出，不自动化操作微信）。报告见 `reports/2026-10-19-overnight.md`。 |
| 2026-10-20 | 夜间实验完成。aquant：13 轮 + 收尾全部 exit 0；没有发现可信的盈利策略，也没有下单；Claude 抽查数字和测试，结果一致。记账 MVP 通过验收。总控只被唤醒 4 次。失误：resume 时沙箱的 `.git` 只读导致没能提交，改为由 Claude 创建快照分支作为备份。详见 `reports/2026-10-19-overnight.md`。 |
| 2026-10-20 | (1) aquant 积压改动由 Codex 在 worktree 中整理成 8 个提交，加上 human 入口；验收确认与快照只差新增文档，用 reset --mixed 合入 main，没有碰文件。(2) 记账：354 条导入，234 条原因由 agent 推断，Excel 视图和写回均已验收。(3) AgentConsole supervisor 用 launchd 常驻，扫描本机和 lain，内存 17MB。(4) 上下文分页报告与 Codex 压缩源码笔记。**事故**：codex exec 没关 stdin 导致空等 2 小时；sandbox 下 .git 只读。两者都已固化进 `ops/dispatch.sh`（关闭 stdin、给 .git 写权限、启动后 60 秒内验证真的在干活）。 |
| 2026-10-20 | AgentConsole 推送到私有仓库 github.com/YijieYing/AgentConsole。新增：每轮 recap（Claude 读 wrap_up，Codex 读 task_complete 或 thread_history）、自定义标题、dormant 置灰且可折叠、lain 历史 session 可查看。发现旁路 btw session 里也有用户的提问，总控应把它们视为输入来源（下一步可以加进 inbox）。 |
| 2026-10-20 | AgentConsole 新增：worktree 显示为挂在主仓库下的分支节点；打开 app 或 Terminal；归档（Codex 用 `codex archive`，Claude 移到回收站）；拖动合并（`codex queue` 或剪贴板）；每天提醒长期未用的 session；两栏分开滚动。合并和归档都在一次性测试 session 上验证过。决定：不做内嵌终端，改用“打开”按钮；总控 session 不作为母节点合并进子 session。 |
| 2026-10-20 | 项目改名为 **AgentConsole**（原名 agent-tree）：GitHub 私有仓库 YijieYing/AgentConsole、`~/PRTS/AgentConsole`、Python 包 `agent_console`、状态目录 `~/.agentconsole`、launchd 标签 `com.yijieying.agentconsole`。端口仍是 7788。 |
| 2026-10-20 | AgentConsole 移到 `~/PRTS/AgentConsole`，作为总控台的 supervisor 部分（独立 git 仓库，已加入 PRTS 的 .gitignore）。修复：在 Terminal resume 时带上该 thread 的中转站 profile；idle 提醒持久化去重；inbox 中文乱码。复盘：DigitalFly/ppt/10.15 的 session（jinchi）第 2 轮误用来做 aquant 的 Paper Smoke 准备，通过绝对路径操作 aquant，没有下单，也没有在 DigitalFly 写文件。 |
| 2026-10-20 | 修订 DigitalFly 的 session：分页格式的 thread 不支持 `thread/rollback`，改用官方 `thread/fork`（`lastTurnId` 指定到第 1 轮，`modelProvider` 设为 jinchi）得到新 thread「组会 PPT 分析（10.15）」，只有 1 轮，不含 alpaca；原 thread 已归档（可用 `codex unarchive 01a1445b…` 恢复），rollout 备份在 `ops/backups/`。工具：`ops/codex_trim.py`。AgentConsole 新增“打开者”识别（Codex 用写锁，Claude 用 `~/.claude/sessions` 登记表）。 |
| 2026-10-20 | **Reporter v0**（`~/PRTS/Reporter`）：确定性采集 → 一次 codex 成文 → 投递。第一期周报（10-14~10-20）已生成；邮件通过 Mail.app iCloud 发送，经确认已进入“已发送”和收件箱（第一次查询时还在发件箱，“已发送”说早了，deliver.py 已补上核实）。微信需由用户在 CodexBridge 建 `/auto` 任务读取 `outbox/latest-wechat.txt`，因为 CodexBridge 没有主动发消息的入口。评估了 aquant ML-01（`.worktrees/ml01`）：协议严谨，但 SPY/QQQ 分钟级只用价格特征、用 MSE 选模型偏向零预测、交易数太少，结论“无 alpha”可信；瓶颈在问题设定和执行数据（NBBO），不在模型。 |
| 2026-10-21 | **话题交接**：Ear/GQH lifegraph 数据库的讨论（数据模型、LLM 只用在 Gateway 片段任务、Stack 判定数学、实验 C 链路、背景对话被误标为“食堂吃饭”的案例、A/B 与 C 公平比较的建议）已迁出总控台，写入 `~/.octopus/local/servicehub/geqh25/notes/2026-10-21-from-prts-console.md`，并用 `codex queue` 投递给 geqh25 的 Codex session `01a1595f`（“分析六个文件职责”）。以后这类问题路由到那里，总控不再展开。这是“话题路由”的第一次人工实践。 |
| 2026-10-21 | lifegraph 话题完成交接，两边都已同步：交接文件新增第 7 节（给合作者看的报告 `report-for-collaborators.md` 及其与 `comparison.md` 的同步约定）和第 8 节（统计与图哪个是精髓；建议先做零 token 的平表对照）。已用 `codex queue` 投递给 Codex session `01a1595f`，并用 SendMessage 发给 geqh25 的 Claude session「Ear/Lifegraph 服务开发」。之后用户会回退总控台里这段对话，**以交接文件为准**。 |
| 2026-10-21 | 第二次夜间接管 aquant：caffeinate 运行 12 小时（接着电源）。`supervisor-resume-1021.sh` 等 TUI（pid 89211）跑完 ML-03 当前轮后，用 exec resume 续跑，直到 19:00 ET，或者 worker 回报 ALL DONE。任务：完成 ML-03、测量参考 ETF 实时可用性、写 10-20 收盘报告和方向决策备忘，禁止开 ML-04。修复：resume 时 stdin 没关闭。评估报告：`human/reports/2026-10-21-aquant-ml-assessment.md`。 |
| 2026-10-21 | CodexBridge 微信 14 小时收不到消息，已修复：它的服务环境变量里设了 Clash 代理（`NODE_USE_ENV_PROXY=1`），而访问微信的兜底路径是按解析出的 IP 发请求的，域名写进 NO_PROXY 也匹配不上，长轮询走代理被 RST。修法：CodexBridge 提交 5dce42a，给这条请求单独指定一个直连 agent（可以用 `CODEXBRIDGE_WEIXIN_USE_PROXY=1` 改回走代理）；`weixin.service.env` 的 NO_PROXY 加了微信域名（有备份）。验证：用户 03:13 和 03:21 的两条消息都被收到并回复。aquant 夜间接管：03:19 接管 TUI，第 1 轮确认在工作。 |
| 2026-10-21 | 第二夜验收：8 轮加收尾全部 exit 0，worker 主动报告 ALL DONE 后提前结束（ALL DONE 早停机制第一次生效）。ML-03 被拒绝；参考 ETF 的实时输入凑不齐（收盘前五个同时连续的窗口为 0）；ML-01 前向 0 个信号；没有下单。方向决策等用户来定。 |
| 2026-10-21 | 用户决定 aquant 转向多日周期，评价原则是“钱放在决策层和评价层，不直接拿来训练”。已同步给 aquant：`human/direction-2026-10-21.md`、AGENTS.md 第 5 条、新增 CLAUDE.md（提交 9324907，分支 research/intraday-20261020）；通过跨 session 消息发给 Claude「自动交易机器人 aquant」；通过 `codex queue` 发给 Codex 线程 01a1532a（它当时开在终端里，能否自动读到排队消息还没验证）。这是第一次同时向 Claude 和 Codex 两种 agent 同步同一个决定。 |
| 2026-10-21 | 研究内容迁到 `~/research/PRTS`（独立 git）。状态：E1 等用户读完时钟中断章节；E2 设计 v0 完成（阶段 A 离线重放不需要 API；阶段 B 用 DeepSeek 探针测静默缺页，需要用户提供 key 并确认隐私）；E3 已调研（隐藏状态通信、自创语言、token 平价）；E4（传引用 vs 传值）从“只传指针”的讨论中形成。 |
| 2026-10-21 | 归档了 PRTS 主对话的旧分支 `27b8fd88`（AgentConsole 归档，Claude 的 session 移到 `~/.agentconsole/trash/claude`，可以恢复）。原因：10-21 02:00 用户修订会话、剪掉 Ear/gqh 讨论时，app 从 23:03 处分出了新 session `92dde3e1`，旧的那份留在磁盘上。那段讨论在归档前已完整迁出：交接文件 `~/.octopus/local/servicehub/geqh25/notes/2026-10-21-from-prts-console.md`（8 节），并已送达 geqh25 的 Codex 和 Claude「Ear/Lifegraph 服务开发」。经核实送达，没有重复发送。 |
| 2026-10-21 | **同步：「Codex 角色迁移与备份方案」session**（为将来让 Codex 担任总控做准备）。`ops/backup_claude.sh`：rsync 只增不删，备份 Claude 的 transcript、memory、file-history、桌面端会话元数据，并生成 `INDEX.tsv`；备份目录 `ops/backups/claude`（约 28M，被 git 忽略）。launchd 任务 `com.prts.backup-claude` 每天 03:30 运行，同时把**已提交的** PRTS 和 research/PRTS 推到 GitHub（不自动 commit）。`~/.claude/settings.json` 中 cleanupPeriodDays 改为 36500。PRTS 和 research/PRTS 已建为私有仓库（YijieYing/PRTS、YijieYing/PRTS_research）。另外修复了 Codex CLI 中 computer-use MCP 的路径。 |
| 2026-10-21 | **同步：「自动交易机器人 aquant」session**。把 10-20 影子观察的结果写入 phase6 报告（9bc44b3）；ML-01/02/03 合并进 `research/intraday-20261020`（bda95b3、562fe7b），数据已拷贝，三个 worktree 和分支已删除；main 和 multiday 没有动；记录了“不使用付费数据”的决定。**18:28 起正在设计 24 小时自进化工作流**：每天开盘采集并实测、收盘后通过 CodexBridge 发微信汇报、Claude 负责决策和监控、Codex 负责实施，lain 上可承担的工作需要评估后汇报。它会复用 PRTS 的 dispatch、Reporter 和 CodexBridge，需要和总控协调，避免两边同时写同一组件。 |
| 2026-10-21 | 应 aquant session 的请求，Reporter 新增“aquant 每日渠道”：`Reporter/aquant_daily.py`，由 launchd `com.prts.reporter-aquant-daily` 通过 WatchPaths 监视 `~/Projects/aquant/outputs/daily/latest-wechat.txt` 触发，每天 07:15 兜底；校验后写入 `outbox/aquant-daily.txt`，用户的 `/auto` 在 07:30 JST 转发。邮件默认关闭。用临时目录测过 4 种校验情况；**端到端触发还没验证**（要等 aquant 第一次真正生成日报）。aquant 的 P1（趋势/动量）已由它通过 dispatch 派发（aquant-p1-trend，worktree `.worktrees/multiday`）。 |
| 2026-10-21 | 备份工具通用化为 **AgentConsole `plugins/backup`**（已推送到私有仓库 f501516）：支持 Claude 和 Codex，只增不删，默认排除含密钥的文件，SQLite 用备份接口拷贝，生成跨工具的 INDEX.tsv。PRTS 迁移：配置 `~/.agentconsole/backup.json`（dest=`~/PRTS/ops/backups`，打开 settings 和桌面配置的备份）；launchd 由 `com.prts.backup-claude` 换成 `com.agentconsole.backup`（03:30）；删除旧的 `ops/backup_claude.sh`；git push 移到本地 hook `ops/backup_hook_push.sh`。修复：launchd 没有代理导致 push 连不上 GitHub，hook 改为读取系统代理，另加 60 秒超时、禁止交互提示。**用户澄清：推送的只是工具本身；备份数据从未上传**（已核实 GitHub 上 PRTS 仓库没有任何 `ops/backups` 下的文件）。 |
| 2026-10-21 | 用户决定去掉每天自动推送 GitHub 的 hook。备份插件的 post_hook 改为 `ops/unpushed_reminder.sh`：只检查不推送，有已提交但超过 2 天未推送的内容就写一条到 inbox。总控开工流程（INDEX 第 2 步）也加了这项检查，用户要求总控适时提醒他“推 github”。E2 设计升到 v0.2：存根成为与置换策略正交的独立因子（RQ2d），全交叉 7×4×2，先跑试点。 |
| 2026-10-21 | aquant 日报上游：在 lain 上生成（aquant-multiday.timer），Mac 上的 `com.aquant.daily-pull` 每 10 分钟 rsync 拉取（原子 rename）。Reporter 的触发加固为监视目录、监视文件，再加每 10 分钟轮询。**待验证**：第一份真实日报在 10/22 05:40–05:50 JST 到达；已挂后台检查，截止 07:20 JST，赶在用户 07:30 的 /auto 之前。 |
| 2026-10-21 | **事故**：用户在编辑 `~/research/PRTS/.env` 时没有保存，编辑器留下的 `.env.save`（54 字节，开头是 `PRTS_RESEARCH_KEY=`，很可能含有真实的 DeepSeek key）没被 `.gitignore`（当时只写了 `.env`）覆盖，被总控用 `git add -A` 提交进 a146bf8，并随“推 github”推到了私有仓库 PRTS_research。处理：本地删除该文件；忽略规则扩大为 `.env`、`.env.*`、`*.env`；amend 成 b207ece（去掉该文件，其余不变），已强制推送（远端已确认没有 env 文件）。**用户确认 .env.save 是空的**（编辑器没有保存），没有真实泄露，所以不用作废 key。**教训**：提交前必须看暂存列表（`git status --short`），不要盲目 `git add -A`；忽略规则要覆盖密钥文件的各种变体。key 的变量名定为 `PRTS_RESEARCH_KEY`。 |
| 2026-10-21 | **事故 2**：用户写入的 `~/research/PRTS/.env`（PRTS_RESEARCH_KEY）消失。排查结果：Codex 阶段 A 的执行记录里没有任何命令碰过 .env；最可能是总控自己的操作：19:14:51 `mv .env.save .env`（没有检查目标是否存在，可能覆盖了用户刚写入的文件），19:17:03 `rm -f .env .env.save`（顺手把 .env 也删了）。已请用户重新写入。**规则**：改名一律用 `mv -n`；删除前必须确认删的是什么、文件属于谁；用户的密钥文件，总控只读不写不删。 |
| 2026-10-21 | 用户指出，总控多次只回答或只执行了多点消息中的一部分。总控自查出三个原因：(1) 带问题的 wrap_up 会结束本轮，之后不能再写文字，本想放在最后的回答就被截掉了（39 次 wrap_up 中有 25 次带问题）；(2) 计划列表只记行动，不记问题；(3) 本轮工具输出太长，把原始问题挤到很远，相当于一次**轮内静默缺页**，是 E2 研究现象的真实样本。对策写进 Claude 的自动 memory（answer-every-point）：每个点（包括问题）都进计划；问题先用文字回答；结束前逐点核对。key 已验证可用（余额 ¥108.37）。 |
| 2026-10-21 | E2 阶段 A v1 完成（e1af9ae，测试 15 项通过，没有提交原始数据），但**验收不通过**：Codex code-mode 的 `exec` 调用（JS 包着 `tools.exec_command({cmd})`，常串多条命令）没有被解析，unknown 占 76%，文件页重复引用为 0，Codex 只覆盖了 32/140 个 thread。唯一可用的结论：完全相同内容的重读极少（26 次）。已派 v2 修正（e2-phaseA-v2）：按路径和范围作为文件页键，拆分复合命令，提高覆盖，验收线 unknown < 25%，并增加重用距离分析。 |
| 2026-10-21 | **E2 阶段 A v2 通过验收**（74d2a14）：Codex 覆盖 141/141（含 zstd），unknown 23.5%，文件重读 823 次（同页），抽查 files.csv 汇总一致。16k 窗口下的缺页：OPT 112 < LARGEST 701 < LRU 806 < FIFO 832 < CC 969 < CODEX 1153 < TYPE 1323。重用距离 P50 约 2.4 万、P90 约 27 万 token。不等大小的页会导致少量 Belady 式反常（FIFO 和 LRU 各 2 个）。**度量盲区**：用户消息不会被“重读”，所以 TYPE 和 CODEX 留住用户约束的价值在阶段 A 看不到，要靠阶段 B 测。报告：`human/reports/2026-10-21-E2-phaseA.md`。 |
| 2026-10-21 | E2 设计 v0.3：加入术语表、对照措施编号 C1–C10（C1 闭卷、C2 神谕、C3 答案泄漏检查、C4 判分、C5 刷新排除、C6 摘要上界、C7 缺页下限与推断标签分组、C8 冻结与预注册、C9 隐私、C10 成本），以及效度威胁对照表；约定以后每个实验都按这个结构写。用户确认 unknown 的处理顺序：语法树补全 → 阶段 B 试点 → 视情况用 LLM 推断。语法树补全已派发（e2-phaseA-ast）。 |
| 2026-10-21 | E2 C7 语法树补全通过验收（7e43758，46 项测试）：新增静态读取 588 次、写入 21 次；按调用计算的 unknown 只从 23.54% 降到 23.33%（口径：一次调用里只要有一个操作解析不了就算 unknown）；缺页数整体增加约 10%；**各窗口下的策略排名不变**，结论对补全稳健。阶段 B 准备工作已派发（e2-phaseB-prep：40 个候选探针、调用器、dry-run 成本估算，不调用 API）。真正发送前需要用户审查 `results/phaseB/probes-review.md`。 |
| 2026-10-21 | E2 阶段 B 准备完成（2b0d9c1：调用器、65 项离线测试、没有调用 API），但**选出的探针为 0/40**：文件切点不在白名单 session 里；约束类则因为隐私规则是按关键词整段拒绝（key、token、记账、aquant……），真实对话全部命中（token 在 LLM 讨论里无处不在）。Codex 没有凑数，如实报告。总控建议改为“按真实敏感内容逐处遮盖”：用正则识别 key 格式、个人信息（邮箱、手机号、学号）；记账和账户类页面替换为等长占位；aquant 的研究讨论保留；答案落在遮盖区的探针剔除。**等用户决定隐私策略。** |
| 2026-10-22 | 用户确认隐私策略改为逐处遮盖（E2 设计 v0.4：C9 遮盖真实秘密、个人信息，记账和账户页用等长占位，aquant 研究讨论保留；新增 C9b：答案落在遮盖区的探针剔除）。用户问到 C7 和 C8，已解释“重读”（缺页下限）和“固定种子”（可复现）。已派发探针重选（e2-phaseB-probes，不调用 API）；白名单新增 E2、AgentConsole、Reporter 的派发任务 session。 |
| 2026-10-22 | 探针重选任务两次因为 OpenAI 的 `Selected model is at capacity` 中断（工作区里的修改都在，测试通过）。新增 `ops/retry_resume.sh`：遇到容量不足就每 10 分钟用 `codex exec resume` 续跑同一个 thread，最多 6 次，并把事件记进 registry。没有擅自换模型，也没有改用用户的中转站。 |
| 2026-10-22 | 查明 Codex 报错“Selected model is at capacity”的含义：服务端返回 HTTP 503，错误码为 `server_is_overloaded` 或 `slow_down`（见 codex-rs/codex-api/src/api_bridge.rs），也就是**这个模型的服务容量不足，不是用户额度问题**（额度错误走 rate_limit_exceeded 和 UsageLimitExceeded）。当时周额度已用 78%，没有触发任何限制，计划为 prolite，10-27 17:41 JST 重置；模型 gpt-6-astra。出错时间是美国东部下午高峰（15:20–15:45 ET），同一时间 aquant 也在派发 Codex 任务（同账号同模型并发）。社区报告并发会提高出错频率。Codex 对这种错误不会自动重试，所以由 `retry_resume.sh` 每 10 分钟重试（官方建议等约 15 分钟或换模型）。 |
| 2026-10-22 | 检验 at capacity 是否真是服务端问题，结论是**基本可以确定**。证据：① 源码中这条报错对应 HTTP 503 加 `server_is_overloaded`/`slow_down`；② 失败的 thread 用的是官方 `openai` provider，不经过中转站（jinchi 的 hachimiapi.rimi.uk 是别的 session 在用）；③ 额度没有触发任何限制；④ 04:50 用同一个账号和模型发了一个极短的请求，11 秒内正常返回，说明容量恢复，是暂时性的；⑤ 社区近期有很多同样的报告，出错时正值美国东部下午高峰。OpenAI 状态页显示没有事故（容量饱和通常不发公告）。无法排除：本地日志没有保存原始错误码，所以分不清是 `slow_down`（账号级限速）还是模型过载；aquant 的并发任务可能也有影响。另外，gpt-6.1-sol 在 ChatGPT 账号下不可用（400），不能作为后备模型。 |
| 2026-10-22 | 探针重选完成（aaa4a82，75 项测试）。后几轮续跑虽然报了容量不足，但每轮中断前都推进了一部分，最终完成；retry_resume.sh 把“日志里出现 at capacity”当作失败，判断有误，已由总控手动停止。结果：**约束类 20/20，文件类 0/20**（文件候选全部被剔除：重用距离不足 16k、各策略意见一致、实际范围无法核实等）。审查表经总控正则扫描，没有密钥或个人信息。dry-run：538 次请求，约 827 万输入 token（bytes/4）。**DeepSeek 可用模型只有 deepseek-flash 和 deepseek-v4-pro**，调用器默认值已从 deepseek-chat 改为 deepseek-flash，写进 C8。审查表已发给用户，等待确认后跑试点。 |
| 2026-10-22 | **E2 阶段 B 试点开跑**：用户批准了 20 条约束类探针（审批记录：research/PRTS `results/phaseB/review-approval.md`）。模型 deepseek-flash。冒烟测试（C01）：C1 闭卷答错、C2 神谕答对，8 个条件全部答对，**但 C3 显示答案 lain 在各条件的驻留页里普遍泄漏**（PRTS 主 session 反复提到），所以这条探针测不出策略差异，分析时要按 C3 单独列出。成本：每条探针约 ¥0.36（58.5 万输入 token，缓存命中 13%），全部估计约 ¥7（起始余额 ¥108.37）。剩余 19 条在后台运行，日志 `results/raw/E2/calls-pilot.jsonl`。 |
| 2026-10-22 | 试点第一次运行在 C02（FIFO、16k、有存根）崩溃：模型通过存根意识到缺了信息并调用 recall，但取回了错误的页，又请求了无效 id，超过 3 次上限后调用器直接抛异常退出。这是一个有意义的结果（知道自己忘了、尝试取回但失败），不应该让程序崩溃。已修改：取回失败作为一种结果（outcome=recall_failed，判为答错，标为显式尝试）计分，然后继续（research/PRTS 提交，75 项测试通过）。崩溃日志保留为 calls-pilot-crashed.jsonl，19 条探针重跑中。 |
| 2026-10-22 | **E2 阶段 B 试点完成**，花费 ¥3.71。主要发现：FIFO 下目标页被逐出的 23 对比较中，**无存根时静默缺页 15/23，有存根时 4/23**；11 对结果不同的全部有利于存根，McNemar 精确检验 p≈0.001。类 Codex 策略会固定保留用户消息，所以约束类探针测不出它，必须补文件类探针。C3 字面匹配高估了泄漏。判分 v2（去掉反引号和标点，另加宽松分）。6 条探针原本被 C2 误剔除，原因就是判分过严，已离线重新判分。正式实验建议：16 个条件约 ¥40（余额 ¥104.66），关闭无存根条件下的 recall。报告：`human/reports/2026-10-22-E2-pilot.md`。 |
| 2026-10-22 | aquant 第一份日报**没有生成**：lain 上的 aquant-multiday.service 在北京时间 05:30 失败（Forward data download incomplete），下一次在北京时间 07:00 运行。Reporter 工作正常，但端到端链路仍未验证。已通知 aquant session 排查。另外查明 inbox 乱码的真正原因：macOS 自带 bash 3.2 在 UTF-8 环境下会把变量后紧跟的全角字符当成变量名的一部分（`$title（`），已改成 `${title}`；设置 locale 的那次修复没有对准根因，并清理了 inbox 里的乱码行。 |
| 2026-10-22 | aquant session 查明日报失败的两个原因，都与网络和代理无关：① 下载结束时间设成了当天 23:59:59Z，Alpaca 免费套餐拒绝最近 15 分钟的 SIP 数据（403），所以当天运行必然失败，改为“现在减 16 分钟”；② FRED 正在维护，DTB3 无效，改为回退到最近一份有效缓存并加标记。修好后会在 lain 上补生成 10-21 日报。总控已挂监视（最多 4 小时），等日报被转发或被拒绝时验收端到端。注意：补发的日报晚于 07:30，/auto 不会自动转发，需要用户在微信里手动触发一次。 |
| 2026-10-22 | **aquant 日报链路验证通过（到 outbox 为止）**：aquant 在 lain 上部署修复 6e96186，补生成了 10-21 日报。Mac 在 07:32 拉取，Reporter 在 07:32:09 记录 staged 2026-10-21，共 424 字。总控独立核对：首行正确，没有疑似 key，outbox 与源文件逐字一致；随后再次触发记为 unchanged（幂等）。说明监视目录的触发方式有效。最后一段（outbox → 微信）要等明早 07:30 的 /auto 才能验证；今天这份比 /auto 晚了 2 分钟，需要用户手动触发。 |
| 2026-10-22 | E2 设计 v0.5（与用户讨论试点之后）：“约束类”改名为**用户探针**；用户探针和文件探针分层、各 50 条，分层报告，另给按自然比例加权的结果（类 Codex 在用户探针上占优是它的设计取舍，要报告）；条件恢复全交叉 56 个，余额不够就请用户充值（用户要求，已存入 Claude 记忆 research-budget）；新增 C11 满上下文基线，作为“看见了但没用上”的噪声地板；C3 只排除假成功，答错照常计为缺页；C4 v3 要求 JSON 回答、双判分、人审分歧、审计被剔除的探针；查明无存根时那次 recall 的来源：页 id 是连续编号，模型按规律猜出来的。所以无存根不提供 recall，有存根时页 id 随机化。用户想手动压缩上下文：总控无法自己触发，需要用户在输入框执行 /compact 并说明保留重点。 |
| 2026-10-22 | 用户：“现在开始E2正式实验”。已派发 Codex 任务 e2-v05-prep（规格 `research/PRTS experiments/E2/job-phaseB-v05.md`，不调用 API）：调用器支持全部 7 种策略和 56 个条件，加上 C11；OPT 按 t 之后的真实引用串计算，不预知探针；CC 是近似复刻；无存根不提供 recall，页 id 随机化；JSON 回答；第二判分模型用 deepseek-v4-pro；文件探针改为“读过的文件里的事实”，不再要求重读；每类收集约 65 个候选；analyze.py 和预注册草稿；dry-run 预算。自然配比的权重无法从阶段 A 得到，改为报告敏感性曲线 w∈[0,1]。运行顺序：用户人审探针 → C1/C2/C11 → 剔除审计人审 → 冻结 → 56 个条件 → 判分分歧人审。 |
| 2026-10-22 | e2-v05-prep 完成（9fd13b7，102 项测试通过）：只收集到用户探针 23 条、文件探针 16 条，原 9 个来源已经用尽；预算 ¥31（算上 recall 上限 ≤¥75）；发现缺陷：每个块各有独立 id，所以 LRU 和 FIFO 完全相同。**用户批准新增三组来源**（个人编码项目、课程作业、AIInfra/ArtAgent；审批记录在 `results/phaseB/sources-approval-v05.md`）。总控决定：旧的 C01–C20 按新规则统一处理，只保留 6 条（C02、C05、C08、C10、C14、C15）。已派发 e2-v05b：扩充来源、页按资源 key 确定身份（以修复 LRU 和 OPT）、重新生成审查表和预算。 |
| 2026-10-22 | e2-v05b 完成（ba310a8，110 项测试通过）：候选用户探针 40 条、文件探针 65 条，共 105 条（新来源贡献多数；3 个短 Claude session 均被排除），旧探针保留 6 条。总控离线核查：LRU 与 FIFO 的驻留集几乎相同（420 个“探针×窗口”组合中只有 1 个不同，前缀里重读很少）；OPT 只有 33 个不同，目标驻留情况与 FIFO 完全一样，说明“显式缺页最优”不等于“保住所需信息”（可以作为 RQ2b 的论点）。目标驻留：用户探针在 TYPE、CC、CODEX 下多数驻留；文件探针在 CODEX 下最差（32k 时 10/65）。预算约 ¥108（recall 全部用满的极端情况 ¥225），建议余额 ≥¥150。**等用户审查 105 条探针**（`results/raw/E2/probes-v05-review.md`）并确认余额。 |
| 2026-10-22 | 用户以 U43（“普通 C# 类”）为例，问同义、子集、语义范围更大的回答怎么判，并要求模型给出明确引用。E2 设计 **v0.6**：C4 v4，每题自带评分键（required、accept、reject，人审后冻结），判为三档：对、partial、错；主分析把 partial 算错。回答要附逐字引用（evidence），按出处分类：只有出处是 p* 才算“保住”，出处是其他页或摘要算“别处得到”，没有有效引用算“推断或猜测”。新增 C12 上下文推断基线（满上下文去掉 p*，答对就剔除）。已派发 e2-v06。 |
| 2026-10-22 | e2-v06 完成（d305804，132 项测试通过），总控修了一处问题（0eeae48）：reject 中不属于标准答案片段的（例如 MonoBehaviour）原来判 partial，改为判错；片段型的（例如“C# 类”）仍判 partial。有 14 条 weak 探针（用户 8 条、文件 6 条），总控建议保留，让 C1/C12 来实测，并作为子层报告。预算约 ¥113（recall 全用满的极端情况 ¥230）。用户探针层只有 40 个候选，有效探针可能不到 50 条。审查表 v0.6 已发给用户。 |
| 2026-10-22 | 用户以 U22 为例问并列项的情况（答“不要创建自己的数据库”）。总控验证 v0.6 判分：答成并列项判了 partial，把整串列出来反而判对，两个都是漏洞。处理：评分键加 siblings，并把 required 拆成 key（区分性要素）和 frame（框架要素）；提到并列项一律判错；prompt 要求只给一个答案。已派发 e2-v06b。另外，用户的语言偏好已记入 yyj.md。 |
| 2026-10-22 | e2-v06b 完成（d38ba86，144 项测试通过）：80/105 条探针有并列项（用户探针 17 条、文件探针 63 条）；U22 和 U43 的各种回答，总控抽查判分全部符合预期。审查表 v0.6b 已发给用户，**等用户审查，并确认余额 ≥¥150**。 |
| 2026-10-23 | 用户认为把要素拆成 key/frame、给并列项单设判则都不符合直觉，写死的判则很难做好。用户的思路是：先调研有没有人做过；尽量约束 DeepSeek 的输出，而不是去判断无穷多种回答；判不了的再交给 LLM（例如 Codex）兜底。新建 `~/research/alignment`（git 仓库），派发 Codex 调研 alignment-grading-survey（联网检索；dispatch.sh 新增 CODEX_TOP 环境变量，用来传 `--search` 这类顶层参数）。**E2 的探针审查暂停**，等调研结果出来再定判分方案。用户要求本 session 一律用中文。 |
| 2026-10-23 | 判分调研完成：`~/research/alignment/notes/01-answer-grading.md`。推荐方案 C：保留无选项短答，答案整句等于预审别名时直接判对，其余一律交给 LLM 判（语义兜底），退出 key/frame/siblings 规则，旧规则只作 legacy 对照；选择题（A）作为单独的“辨认”测试，逐字片段（B）用来测原文保真。主要证据：Kamalloo 2023（词面匹配低估正确率）、LongMemEval（judge 与人工一致率 97–98%）。DeepSeek 只有工具调用在 strict 模式下支持 enum，json_object 不能约束取值。**等用户决定三件事**：主测量目标、引用的角色、人工复核预算与可复现要求。 |
| 2026-10-23 | 用户决定：主测量用方案 C；**强制引用**（理由：先定位原文再作答，可以减少长上下文中“本该找到却没找到”的干扰）；人工复核不设上限，Codex 判分不重跑（原始判决就是判分记录）。E2 设计 v0.7（判分链：解析 → 规则层只认整句等于预审别名 → 其余全部交给 Codex 判 → 人工终裁和审计；用试点回答加构造的对照例做校准）。已派发 e2-v07。 |
| 2026-10-23 | e2-v07 完成（6501fef，175 项测试通过）。**总控在验收时发现试点结论无效**：deepseek-flash 默认开启推理，试点每次回答只给了 256 个输出 token，有 31/151 次回答把预算全部耗在推理上，输出为空；摘要调用（预算 2000）227 次中 223 次被截断。剔除截断后，存根效应只剩 10 对、2 比 0、p=0.5，原来的“65%→17%”主要是截断造成的。试点报告已加更正。正式实验需要决定是否开启推理：开启时 max_tokens 设为 16k，额外费用约 ¥45–90，错峰运行可以减半；关闭则 `thinking: disabled`。校准挪到基线阶段之后，因为试点的真实回答太简单，大多被截断。 |
| 2026-10-23 | 用户决定**开启推理**（max_tokens 16384，与窗口预留分开；e2-v07b 0581a4f）。总控决定：带 tools 时 API 要求回传推理，但这部分**不计入模拟窗口 W**，否则只有有存根的条件会被挤压；回传量单独记录。冒烟测试（C02，约 ¥1）：没有截断；温度无效，同一请求的回答写法会变化；摘要更长，每次 12–32 秒。预算修正为错峰约 ¥250、高峰约 ¥500，串行需要约 45 小时，必须并发。余额 ¥203.85。超时改为 600 秒并加重试。 |
| 2026-10-23 | 运行器完成（c87f371，214 项测试通过）：分基线和主阶段两步运行，支持并发、续跑、错峰闸门和预算闸门。基线阶段中 C2 和 C11 各重复 3 次，用来测推理模式的随机波动；C2 改为 3 次里多数答对才保留。按冒烟测试数据估算（错峰）：基线 ¥29、840 次调用、约 5 分钟；主阶段 ¥296、13,040 次调用、8 并发约 7 小时，不含 recall 和重试。余额 ¥203.85，建议充值到 ≥¥450。**等用户审查 v0.7 审查表**（`results/raw/E2/probes-v07-review.md`）。 |
| 2026-10-23 | **用户批准 v0.7 探针集**（105 条，审批记录 `results/phaseB/review-approval-v07.md`，运行副本 `probes-v07-approved.jsonl`），保持开推理，充值到 ¥450 以上。审查表中出现的删除线是 Markdown 把 `~/` 路径当作删除线标记造成的，已加转义（ff2f79b）。05:40 UTC 启动**基线阶段**：840 个单元，8 并发，只在错峰时段运行，预算闸门 ¥45，余额低于 ¥60 时停止，日志 `calls-formal-baseline.jsonl`。06:00–10:00 UTC 是高峰时段，期间会自动暂停。 |
| 2026-10-23 | 基线阶段完成：用户要求不等错峰，总控在高峰时段跑完了剩下的 60 个单元；共 840 个单元、¥23.66、截断 1 次；IncompleteRead 断流已加入重试（另外补跑了 2 个单元）。规则层判了 706 条，其余 98 个不同的输入交给 Codex 判分（4 批）。建议保留的有效探针：用户 23 条（另 1 条待审）、文件 43 条（另 8 条待审），都低于 50 条的目标；剔除原因主要是 C12 答对（用户 16 条、文件 13 条），也就是答案在别处同样能找到。按判定后的标签看，三次重复的一致性很高（C2 104/105、C11 101/103），随机性主要体现在写法上。人工终裁 94 条，整理成 `baseline-review/终裁表.md` 发给用户（表中列出了机器判定，以节省用户时间，代价是人工判断不再完全独立）。 |
| 2026-10-23 | 用户审阅终裁表：要求删除 F32，其余同意机器判定；同意由 Codex 来判（用户认为 Codex 的标准比自己还严）。总控澄清：只有 C2 答错才剔除，C1 或 C12 答错正说明探针有效，C11 只作为噪声地板。用户关心问函数名的题错误率高：查明错误都出现在 C1/C12，C2 和 C11 几乎全对；同参数列表的干扰项只有 F32、F39 两条，均剔除；U28 是题目设计问题，剔除。随机性很小，保持开启推理。**有效探针 72 条（用户 23 条、文件 49 条）**，待冻结（`probes-v07-frozen.jsonl`，sha 84ddca8a…）。余额 ¥181.38；主阶段错峰预计约 ¥200，算上 recall 上限约 ¥350。 |
| 2026-10-23 | 用户问基线不可复现时是否该改用不推理重跑。总控回答：只是写法变，判分结果一致率达 97–99%；关推理也不能保证可复现；靠存档原始回答保证可复现。补充措施是在主阶段重复一小部分条件来测噪声（约 ¥10，主阶段跑完后补跑）。用户同意，**冻结 72 条**（`results/phaseB/freeze-v07.json`），已充值，余额 ¥281.38。08:45 UTC 启动主阶段：4,032 个单元，8 并发，只在错峰时段运行，10:00 UTC（北京时间 18:00）自动开跑，预算闸门 ¥260，余额低于 ¥20 时停止，用 caffeinate 防止休眠；日志 `calls-formal-main.jsonl`。 |
| 2026-10-23 | 主阶段进行到 1656/4032（¥91）时，因为一次余额查询失败（网络抖动），运行器以 balance_error 停下，实际余额还有 ¥197。已改为：余额查询失败会重试，连续 3 次失败才停止。23:28（北京时间）续跑。截断 77 次，其中 73 次是 CODEX 的摘要调用（32k 下 36 次），摘要被推理和长输出耗尽了 16k 预算，分析时要单独报告“CODEX 摘要截断率”。按当前进度推算，主阶段总花费约 ¥220。 |
| 2026-10-24 | 用户问是否有必要把生成上限设为 16k。总控：这个上限是我们自己定的（DeepSeek 推理模式默认 64k），截断主要发生在 CODEX 的摘要上。决定：主阶段不在中途改上限，跑完后把所有出现过截断的单元按 64k 上限重跑，写到单独的日志；分析时用重跑结果替换原结果。上限只在被触及时才起作用，所以这样做等价于一开始就用 64k，额外花费约 ¥20–40。运行器已新增 `--only` 和 `--generation-limit` 参数（日志 manifest 会记录上限，不同上限的日志不会混在一起）。 |
| 2026-10-24 | 04:00（北京时间）主阶段 3836/4032，¥183，失败 25 个单元（传输错误）、截断 104 次，预计 20 分钟内跑完。用户今天全天外出。总控布置了无人值守流程：`autopilot_main.sh`（已在后台启动）会等主阶段结束，然后依次补跑失败单元、以 64k 上限重跑截断单元（75 个，日志 calls-formal-main-64k）、做噪声重复（FIFO 和 CODEX@16k 共 288 个单元，日志 calls-formal-main-rep2），每一步都有预算闸门。另派发 e2-analysis（离线判分与分析流水线 + 报告草稿）。之后总控运行 Codex 判分，整理人工终裁表，等用户回来审。 |
| 2026-10-24 | 主阶段 4032 个单元全部完成（¥187.6）。初步结果（部分判分）：无存根时被逐出的信息几乎全部变成静默缺页，有存根时转为显式取回；TYPE、CC、CODEX 固定保留用户消息，对用户探针很有效；文件探针上 CODEX 不如 FIFO；8k 有存根时，取回后放不下的单元很多（文件探针 34/49），原因是被取回的页本身就有 3–8k、一次常取回多页，与是否推理无关。修复：合法的 JSON 片段不再算格式错误（实际只影响 3 条）；人工队列不再收录机器能判定的异常（从 1021 条降到 336 条）。用户同意做 E3 分词器实测和 E2 真实 token 重算；不急着写论文，改为调研：已有工作和更好的压缩方法写入 `research/PRTS/reference/`，美国教授（12–15 位高契合度）写入 `research/PRTS/outreach/`。已派发 e2-token-recount（直接用日志里的 prompt_tokens，不需要下载）、ref-compression-survey、outreach-professors。E3 需要下载分词器（tiktoken 和 HF 上的 tokenizer.json），**等用户批准下载**。 |
| 2026-10-24 | 用户批准 E3 下载。总控从官方 HF 仓库下载了 DeepSeek-V3 和 Qwen2.5 的 tokenizer.json，并在 `.venv-tok` 中装了 tiktoken 和 tokenizers（tokenizers/ 已加入 gitignore），已派发 e3-tokenizers。三项任务完成：(1) 真实 token 重算（f5e211f）：真实 token 与代理单位之比的中位数为 1.043，W=8k 约等于 8.6k 真实 token。(2) reference/（3c39a70）：最相关的已有工作是 Pichay、ReadAgent、Factory 的压缩评测；建议优先尝试“页内分段取回 + 可寻址摘要”，最小实验 12 个条件、864 个单元。(3) outreach/（7834234）：12 位教授，契合度 5/5 的有 Yongfeng Zhang、Joseph Gonzalez、Kai-Wei Chang、Graham Neubig、Mohit Bansal、James Zou；另附英文研究简介草稿。 |
| 2026-10-24 | E3 分词器实测完成（5d45ee0）：以中文为 1，英文约 0.7–0.9，日文约 1.2，法文约 0.9–1.1；改成列表或 JSON 格式可省 25–29%。E2 全部运行完成：64k 重跑 ¥27（重跑后无截断），噪声重复 ¥42（被预算闸门停在 267/288，总控补跑完）。Codex 判分完成，人工队列 364 条（`main-review/终裁表.md`）。初步结果报告：`human/reports/2026-10-24-E2-main.md`。要点：存根把静默缺页几乎全部转成显式缺页，但 3179 次 recall 只有 289 次取到 p*；用户消息固定保留就几乎不丢；文件探针上 CODEX 明显不如 FIFO；OPT 不比 FIFO 更能保住所需信息；噪声翻转率 0–23%。E2 总花费约 ¥280，余额 ¥143 左右。**等用户审查 364 条终裁表。** |
| 2026-10-27 | 微信秘书自动建记录：秘书回复末尾输出 ```codexbridge 指令块，bridge 去掉后代为执行（只放行新建 /remind /todo /note /log，每次最多 5 条，自动建的提醒直接生效；定时任务和补发回复不执行）。Codex 实现并测试（94c20af，在 CodexBridge 部署分支 fix/durable-weixin-replies 上，未 push），已重启服务。**待用户在微信实测一次**。已知风险：没有去重，保存成功但投递失败时手动重发会重复建。 |
| 2026-10-27 | secretary/PROJECTS.md 重写为当前路径，AGENTS.md 规定路径只看 PROJECTS.md；~/.claude/CLAUDE.md 和 ~/.codex/AGENTS.md 加了“改动时同步更新文档”规则（备份在 ops/backups/）；yyj.md 记录 Claude 决策、Codex 执行的额度分工。 |
| 2026-10-28 | 用户提出两条新线：AgentConsole 从观察升级为能分工、回传失败、提醒和接受人工干预的系统（参考 QED、LibreChat），以及把果蝇/线虫的刺激—响应辨识当 autoresearch 试验场，并要求避免 overnight 结果看不懂。Claude 写了可行性评估（`human/reports/2026-10-28-agentconsole-autoresearch-feasibility.md`）：两件事绑在一起做。GPT 提的 5 节点网络在 worm_effectome 的 Exp1 已有 300 节点版本，现在改作人能逐项核对的考场，并按真值阶梯逐级放开；研究题改为比较合作结构下人的核查成本。设计问题池第 6 条。等用户定顺序。 |
| 2026-10-28 | 用户决定：借 QED，不用 LibreChat；PRTS 每个研究方向一个专用 session，另设研究统筹 session「PRTS 研究统筹：新建研究方向与状态表」（`local_3c429145-cee0-478c-8517-f533a99ac312`）负责新建方向、维护 `research/PRTS/README.md`。写权限按目录划分：统筹写根目录、notes、reference、outreach，各方向只写自己的 `experiments/E<n>/`、`results/E<n>/` 和 `STATUS.md`，互相只读，只提交自己的路径。已让统筹登记总纲和 E5（多 agent 合作结构 × 人的核查成本）。用户澄清：果蝇目前是按步骤管控的研究，不是 autoresearch；理想的 autoresearch 是"给一个 benchmark，让 AI 一直干到超过为止，人尽量不管"。候选试验场：胡瑞的计划（用 fast weight 给脑网络加容量去赢 MLP），由 autoresearch 尽力实现，同时对照打乱图、随机图和同参数 MLP，用来检验他的方案能否证明连接组的作用。评估写在可行性报告 §5。总控最初只看了他的 PPT，漏掉了 DigitalFly 10-23 的讨论，已加入检索顺序规则（INDEX.md、全局 CLAUDE.md）。研究统筹已脱离总控，成为顶层 session，更新时通知各方向 session，不再回报总控。 |
| 2026-10-30 | AgentConsole 修复（3d81008，未推送）：Claude 桌面 app 换 transcript 后，旧 transcript 被当成另一个 session 显示（例如 E2 改名前的「PRTS 项目尝试」）。现在改读 app 的元数据 `~/Library/Application Support/Claude/claude-code-sessions/*/*/local_*.json`（`cliSessionId`、`priorCliSessionIds`、`title`、`isArchived`），把旧 transcript 折叠到当前 session 下，标题以 app 的为准，app 里已归档的默认隐藏，也不再计数或发提醒。5 个测试通过，已重启服务并核对。过期清理按设计只做提醒（14 天）；dormant 共 92 个，都在 14 天以内，其中 62 个是已经结束的 codex exec 派发任务。是否自动归档已验收的派发任务，等用户决定。 |
| 2026-10-30 | CodexBridge 新功能（cbcfaa6 + e1fa93d，已部署到 fix/durable-weixin-replies，未推送）：(A) `weixin notify`，本机程序可以直接推送微信。总控封装成 `~/PRTS/ops/wechat-notify.sh --file/--text`，`outbox` 参数可查状态。token 超过 24h 失效时，消息会等用户下一条消息后补发。实测送达。(B) 秘书现在可以在 codexbridge 块里发 `/auto add` 草稿，确认和删除仍只能由用户做。(C) `/auto` 新增一次性时间表 `once`。起因：用户让 aquant 的 Codex session（`01a18913`）监控 AMZN 财报，需要把结果发到微信；已用 codex queue 告诉该 session 写入 `Reporter/outbox/amzn-earnings.txt` 并调用 wechat-notify。网络问题仍未解决：10-29 日报因连接 43.163.179.90 超时没有送达。 |
| 2026-10-30 | 上游提议：Gan-Xing/CodexBridge 已近 4 个月没有维护，直接提 PR 不划算，所以先开了 issue https://github.com/Gan-Xing/CodexBridge/issues/26 ，提议「回复持久化」和「weixin notify」；维护者有回应再拆成 PR。AMZN 财报推送全是「未核实」，原因：aquant 的监控只自动抓行情，财报实际值要等有人核实后写入 `evidence.json`，但 Codex session 04:33 就结束了，之后没有任何东西去写这个文件。因此只推送了 05:20 一条，「电话会后」阶段也一直卡住（要求先核实电话会已结束）。另外，lain 的 ssh 拉取有超时。 |
| 2026-10-30 | 新增 `ops/wake.sh`（Codex 实现，a484436）：用一次性 launchd 在指定时间唤醒 Codex session，默认用 `codex exec resume`。Codex 的沙盒没法写 LaunchAgents，所以由总控实测：dry 唤醒和真实唤醒都按时触发，测试 session 回复 pong2，plist 已自删。新增 `ops/README.md`，区分 PRTS 自己做的工具和 Codex、cc 原有的功能；AGENTS.md 加了事件监控规则（每个阶段都要安排唤醒，未核实要写进结论）。 |
| 2026-11-02 | 新建 `memory/people.md`，yyj.md §5 改成指针。内容：GitHub/邮箱对照（用户确认 aytony=安阳，石伟男、喻纯从提交推断），FlyBrain 组（老板李国齐；最靠谱的学长陈白雨，做 BrainFuse；唐元宏），清华 HCI（喻纯、石伟男），以及待问清单。主动提问机制记为设计问题池第 7 条（未决定）。Gmail：connector 目录里有官方 Gmail，但还没连接，需要用户自己在 Connectors 里授权。 |
| 2026-11-02 | 用户补充：yuchun=喻纯；唐元宏属于果蝇组；陈伟浩是喻纯组的博士后；用户没有严格意义上的导师；其余待问的人暂时不重要（已写进 people.md）。Gmail connector 已接上（herryying30@gmail.com），实测能读。主动提问写成提案 v1（设计问题池第 7 条）：问题对象、值不值得问的规则、叫醒/送达/回收表、分三步做。等用户定。 |
| 2026-11-02 | `Reporter/` 改名为 `reporter/`（af926c4），launchd 的 aquant 日报 plist 已改路径并重新加载，手动触发一次正常。aquant `event.py` 里还写着旧路径 `Reporter/outbox`，因为文件系统不区分大小写所以照常工作；那是 aquant 的文件，没改。主动提问：按用户反馈修订（问题队列归 reporter、按紧急度扫描、每批最多 3 条、outcome 数据结构），见设计问题池第 7 条。 |
| 2026-11-07 | NatureCalls「代码库架构概览」session 说“没法直接联系 Codex”，把任务说明丢给用户转交。原因：派 Codex 的规则只写在 `/Users/prts` 的自动记忆、yyj.md 和 AGENTS.md 里，在别的目录启动的 session 看不到。修复：全局 `~/.claude/CLAUDE.md` 新增「写代码交给 Codex」一节（用户批准），并转告了该 session。重构时这一节的路径要一起改（列入第 5 步）。另：af926c4 的大小写改名只提交了内容改动，已补提交。重构计划已给出（5 步，等用户确认）。 |
| 2026-11-07 | **PRTS 按 GLOSSARY 重构**（用户批准）。(1) `maintenance/`：codex_trim、lain 修复、backups（865M，不进 git）、`archive/aquant-overnight`（af09c85）。(2) `reporter/` 分成 bin/lib/config/state；launchd 日报改成调用 `bin/report daily`，测试通过；保留 `reporter/outbox` 链接，因为用户的 CodexBridge `/auto` 任务还读旧路径。(3) `interaction/`：bin/{dispatch,resume,wake}、lib/wake_fire、state/{tasks,wakes,registry.jsonl}；ops/jobs 和 ops/prompts 合并成 `state/tasks/<任务>/`（ad1dba6）。用新路径实测了一次 dry 唤醒：延迟 0.06 分钟，plist 已删除。重构时 NatureCalls 派的 Codex 任务正在跑，它通过旧路径链接正常写回了 exit 和 last.md。它自己因为网络代理不可达，没能开始工作。(4) `ops/` 只留链接，约 11-21 删除。(5) 代码部分（registry 和 codex 适配层、wake 内部、event 队列、notify 分级、inbox 只由总控写、测试）派给 Codex（任务名 `prts-modularize`）。文档：GLOSSARY v0.2、根目录 README（由 ops/README 改写）、AGENTS.md、human/README、INDEX、全局 CLAUDE.md、自动记忆。 |
| 2026-11-07 | 重构收尾：Codex `prts-modularize` 提交了 5 个（9a3d20a..448e454）：registry 和 codex 适配层、wake_state、event 队列、notify 分级、测试、模块 README。总控复核时修了 4 处：(a) resume 不写 start 记录，`wait` 会误判，已补上；(b) 新增 `interaction/bin/wait`，并按用户批准在全局 CLAUDE.md 加上「派完在后台 wait」；(c) L0 事件只记录，不进验收队列；(d) 测试继承了调用方的 stdin，被替身程序读住而卡死，改成显式传空 stdin。两套测试在本机通过。AgentConsole：on_event 改成用 shlex 拆分命令，配置指向 `interaction/bin/event from-agentconsole`；未推送提醒挪进 `AgentConsole/plugins/backup/`。实测过：一条事件进队列再 ack、notify log、未推送钩子。`human/inbox.md` 从今天起只由总控写。fork 提出的问题：派 Codex 的 session 收不到结束通知，已用 `wait` 解决。 |
| 2026-11-09 | 新建 `~/PRTS/ROADMAP.md`（用户要求）作为唯一的计划表。合并了 prts.md 的总控待办、待讨论、设计问题池、AgentConsole 功能候选，以及 AgentConsole README 的「方向」，原处改成链接，并给出旧编号的对应关系。用户同意 AgentConsole 改名为 monitor（R3，和 11-21 的清理一起做）。用户指出 quiet hours 和 digest 时间是用户属性，不该写进 reporter 的 config，应归一个新的用户状态模块（R2，暂名 presence，名字待定）；推送不应过度依赖微信（R4）。顺手把 prts.md 末尾两条误放的 10-27 记录挪回了日志。 |
| 2026-11-09 | AgentConsole 嵌套显示：(1) 由桌面 app 启动的 session 按元数据 `spawnedFrom` 挂到启动者下面（d082c89）；(2) Codex 派发任务挂到派发者下面：Codex 让 dispatch 和 resume 记录 `caller` 与 `thread`，新增 `status links`，AgentConsole 新增配置项 `links`（PRTS 6a65831，AgentConsole c0306b8）；(3) 总控按证据回填了 44 条旧关系：thread 取自 run.log，caller 取自对话记录里的派发命令，按记录自带的 sessionId 计，避免把 fork 的副本算成派发者；13 个有歧义的跳过。查明：NOT HUMAN 的剧本、前后端任务是「代码风格」11-01 派的，只有 v2 和修订一的后端是 NOT HUMAN 自己派的。**修了一个 bug**：`lib/codex` 在整份日志里找 "at capacity"，日志里只要引用了这句话（比如读到 lib/codex 源码），已经完成的任务就会被当成满载重跑。dispatch-links 因此白跑了 3 遍，已停掉；现在只在失败、且最后 20 行里出现这句话时才重试，并加了回归测试（f407d61）。`wait` 首次实际使用：按设计唤醒了总控。 |
| 2026-11-09 | 用户状态模块定名为 `pulse`（R2）。ROADMAP 和 GLOSSARY 已更新。 |
| 2026-11-12 | 用户回顾 11-11：想不起学了什么、产出了什么。总控遍历了全部 Claude 和 Codex 对话、git 提交，给出带时间戳的回顾，结论是大部分时间花在工程杂务上。但那次回顾漏掉了用户下午在网页版 GPT 上的学习（有效连接和结构连接）。用户定义了**输入（学习）、输出（创造）、杂务**，要求杂务尽量交给 agent。已写入：`pulse/README.md` 设计稿 v0.1（先做每日回顾）、`AGENTS.md` 第一条规则、prts.md 附录 D 第 11 条、yyj.md §2，以及 ROADMAP R2 和 GLOSSARY。 |
| 2026-11-12 | pulse 补充：(1) ChatGPT 网页版可以从 Chrome 本地历史读到对话标题和打开时间，只读 chatgpt.com 的记录，几乎不占资源，不用截图。查到 11-11 下午 15:46–17:49 的「概念和定义」，以及 11:33 传热学、13:14 因果辨识和果蝇连接组方法等学习对话。(2) 用户想做实验：EchoAsRecord 实施「杂务交给 agent」，NatureCalls 对照。前提是加强自检（比如 11-10 查重复实现和接口偏差）和保留最小的架构思考（文件结构加 glossary）。设计稿 `pulse/experiment-chore-ab.md`，ROADMAP R7。(3) 杂务过多时，pulse 通过 question queue 提醒用户，pulse 设计稿 §三。 |
| 2026-11-12 | 已推送 PRTS 和 AgentConsole（都是私有仓库）。Codex 实现了 `reporter/bin/ask`（c7139d8、647f455）和 pulse v1（b02b1ae、c7a168b、aa4beb2），以及 `interaction/bin/run`（1323630）。总控验收：(1) 11-11 的真实回顾：分类 81 秒，学到和产出的条目准确；第一轮时间统计不对（ChatGPT 和单条消息都算成 0 分钟），改用 Chrome 的 visit_duration 和按字数估算以后，输入 107、输出 85、杂务 245 分钟。(2) 杂务提醒：19:45 回放不触发是对的，18:13–19:47 之间没有任何记录。按半小时扫描 11-11，18:30（Octopus 上传排查，active 39 分钟，占窗口 53%）、22:00（音频 API 配置 45 分钟）、17:00（Ear 重判接口，连续 45 分钟）都会触发。18:30 已真实进入队列（Q2）。(3) 总控补了 timely 紧急度（推送一次、不重复），pulse 的提醒用它（d5375bb）；回复示例改用真实编号（ddd5088）。(4) 创建 Claude 定时任务被权限检查拦下了，prompt 存在 `reporter/config/claude-tasks/`，等用户处理。 |
| 2026-11-12 | 用户批准后，总控创建了两个 Claude 定时任务（Auto 模式）：「PRTS 提醒」`prts-reminders`，每小时第 7 分钟，9:00 到次日 0:00；「PRTS 每日回顾」`prts-daily-recap`，每晚 23:40。立即试跑（run_scheduled_task）被权限检查拦下了，等用户在侧边栏点 Run now，或等 7:07 的第一次自动运行。验收待做：Q2 推到手机、用户回复、`ask reply` 记录。 |
| 2026-11-12 | 第一次真实投递（用户手动 Run now）。session 照原样展示了 Q2，也调用了 PushNotification，但**手机没收到，电脑显示「通知未发送」**。原因：只有用户自己开的 session 才会自动连 Remote Control，定时任务的 session 是 `off`；而且 Remote Control 不能给无人值守的 session 打开。所以「Claude 定时任务 + PushNotification」这条路推不到手机。同时修了 pulse check 在家目录下运行失败的问题：`interaction/bin/run` 加了 `--skip-git-repo-check`（e193f2c）。手机渠道改走 ROADMAP R4，等用户选。另外，定时任务的运行记录显示在侧边栏的 Scheduled 里，不在普通 session 列表里。 |
| 2026-11-12 | 手机渠道改用 Bark（用户装好了 app，给了 key）。新增 `reporter/lib/channels/bark`，key 存在 `reporter/config/secrets.toml`（600 权限，gitignore）。`notify` 新增 `phone` 级别，`alert` 改为 Bark + macOS 通知，不再发微信；interaction 的 L2 事件也因此改走 Bark。测试里对 Bark 用替身，保证不会真推到手机。实推测试返回 200。两个定时任务的 prompt 改为用 `notify alert` 推送（update_scheduled_task 没被拦）。新加了验收问题 Q3（timely），等用户点 Run now。 |
| 2026-11-12 | **Bark 验收通过**：手机在 02:26 收到「PRTS 测试」；12:15 收到 Q3（Q3 是 02:29 建的 timely 问题，等休息时段 05:00–12:00 结束后的第一次每小时运行才推）；电脑弹窗也收到了。Q3 在 12:17 被回答（「电脑收到了」），手机也收到了，由用户 22:40 口头确认。22:07 和 22:12 AgentConsole 连发两条 L2「lain 不可达」，22:42 实测 lain 正常（已运行 35 天），说明是短暂断连，这个提醒太灵敏。Computer History：用户决定先用它，读取范围见 pulse/README §二；接入已派给 Codex（`pulse-computer-history`）。 |
| 2026-11-12 | 用户反馈：每小时的 Claude 定时任务没有问题要问时也弹通知（每次运行都开 session，跑完 app 就提示「完成」）。改为 `reporter/bin/remind`（纯代码，只在有问题时推送），由 launchd 运行；`prts-reminders` 已暂停。安装 launchd 被 auto 模式的权限检查拦下（Unauthorized Persistence），plist 放在 `reporter/config/launchd/`，**等用户自己装**；装上之前，每小时的提醒处于停止状态。总控负责处理「Q数字 …」形式的回复（INDEX 第 5 步）。 |
| 2026-11-13 | 日报改为按时间线分段（用户 11-12 要求）：Codex 做了 de41cc5 和 728d799。总控用 11-12 的真实分类验收：2911 字；系统程序和「来回切换」的段已并进零碎；计算机段和对话段重叠时，以「同时：」挂在对话段下。每日回顾任务改为原样推送这份 md（19ba935）。遗留：浏览行情、搜索 invoice 这类活动被算作「输入·学到」，分类标准偏宽，待用户定。ROADMAP 新增 R8：接入 Ear 的录音。 |
| 2026-11-13 | 用户在 Ear 的 local-notes 放了 11-12 夜间口述的整理（七件事加两件补充），要求今晚搭完整的 Ear+pulse 通路，并实现有价值的内容主动处理。做了这些：<br>- 新增 `reporter/bin/todo`（Apple 提醒事项「PRTS」列表），把口述里用户自己的 10 件事写进去；<br>- ROADMAP 新增 R8 设计、R9 声纹、R10 待办、R11 推送策略、R12 Mouth；<br>- 推送标题改用问题本身；<br>- 派出 `pulse-ear`（sync 分诊、inbox、`ear wait`、回顾加入录音和 agent 分节）和 `ear-voiceprint-survey`（只读）；<br>- INDEX 加上总控挂 `ear wait` 的规则。<br>发现：旧 Ear 有完整的声纹链路，登记了 12 人，但 10-14 以后 resolution 几乎全为空，`voiceprints` 表为 0 行。 |
| 2026-11-13 | Ear 通路验收。pulse ear 由 Codex 实现（9fee7c8、232b270）。总控在沙盒外用真实数据跑：第一轮 11 段判为 high，太多；收紧到「用户本人主导、在产出想法或计划」以后，只剩夜间口述 5 段，判对了。冒烟时积压的 inbox 已用 `ear ack` 清掉，总控在后台挂上 `ear wait`。声纹调查结论写进 R9：模型版本号冻结在加载前，是代码缺陷；匿名音色抢先匹配；09-29 后没人确认过。修复等用户同意。用户给了手机端仓库 NextHCI/octopus-flutter，已克隆到 `~/research/octopus-flutter`，登记进 projects.toml；只读调查已派出（`flutter-survey`）。 |
| 2026-11-13 | 口述任务分派（用户要求在各工作区开 session）：<br>- 声纹和 GPS→地点：发消息给「Ear 项目架构」；<br>- FlyBrain 两篇文章的数学学习材料：发消息给「线虫网络参数反推验证」；<br>- 新开 4 个 session：harness-reading（`~/research/DsHarness`）、os-study-plan（`~/research/Infra`）、naturecalls-finish、xindong-budget。<br>申请材料等 Harness 导读出来后再做；服务器需要用户自己装；具身计划暂缓。手机端调查结论：app 设置里就能选 5 分钟一段，Ear 同步改为每 3 分钟一次。 |
| 2026-11-13 | 整理（用户要求）：<br>- 归档 15 个旧的「PRTS 提醒」定时任务 session；<br>- Harness 导读和 OS 计划两个 session 从总控名下移到顶层；OS 计划的文件先放到 `~/school/26秋重要作业/OS`，后按用户要求改放 `~/research/Infra/os-course/`（入口 `~/research/Infra/README.md`），并告诉它 lain 上有同步仓库；<br>- 用户删了 NatureCalls 和芯动这两个 session，芯动的预算草稿已经写成文件；<br>- 存储：删掉冒烟时复制的旧 Ear 库（1 GB）。现状：PRTS 约 1.2 GB，其中 maintenance/backups 约 1.05 GB，是 AgentConsole 备份的 Claude 和 Codex 对话；Computer History 只有 8 MB，会自己滚动清理；~/.codex 2.4 GB，大头是 Codex 自带的 packages，不归我们管。 |
| 2026-11-13 | 夜间任务（用户同意 1–4 项，以及旧 Ear 的修复）。派给 Codex：<br>- `night-ac-alerts`：不可达要连续失败才报，空闲进程按天汇总；<br>- `night-weekly-notify`：周报改为双发，R6；<br>- `night-dispatch-sandbox`：显式放宽沙盒，必须带 approved-by，R5；<br>- `night-oldear-version`：在分支上修复版本缺陷，迁移只做 dry-run，不写库、不重启。<br>`human/inbox.md` 的 224 行过期条目已归档到 `maintenance/archive/`。PRTS（20 个提交）和 research/PRTS（12 个）已推到 GitHub（用户同意）。<br>用户说明：GPS 不能靠缩短录音分段来解决，已经交给「Octopus Flutter 音频提取与 EchoAsRecord 集成」session；NatureCalls 用户自己开了 session；codex 基线以后再说。 |
| 2026-11-13 | 夜间任务验收：4 个都 rc=0。<br>- AgentConsole：45fd56d、6219305，15 项测试通过。总控已用 `launchctl kickstart` 重启 `com.yijieying.agentconsole`，服务正常。<br>- 周报双发：73dd929。<br>- 沙盒选项：bd8119f、fed4278，R5 完成。<br>- 总控重跑了 PRTS 全部测试，全过。<br>- 修正了 GLOSSARY 第 76 行过时的 notify 说明。<br>- 旧 Ear：分支 fix/speaker-model-version，迁移演练里没有一个模板能直接改标签，大部分要用原音重算，等用户决定。 |
| 2026-11-13 | 「Ear 夜间口述整理」session 转来口述 §1 里 ROADMAP 还没有的 6 条。处理如下：<br>- 新增 R13（手机端稳定性）、R14（手机使用情况）、R15（模型放服务器）、R16（ASR 纠错和环境说话人，已转「Ear 项目架构」以提案的形式提出）；<br>- 第 6 条每晚回顾脱离 Claude：写好 `reporter/bin/recap` 和 launchd plist，用替身测试通过，**等用户安装**；<br>- AGENTS.md 加一条：分支和提交规范由 agent 自己管。<br>GPS 地点名 PR #17 已合并。旧 Ear 第三轮演练：迁移全部通过，误认 0/15；但本人 5 段的 margin 只有 0.01–0.04，低于 0.08，接受 0/5。总控按约定停在上线前，等用户决定。 |

## 计划与待办

已合并进 [`~/PRTS/ROADMAP.md`](../ROADMAP.md)（2026-11-09）。原来的「总控待办」「待讨论」「设计问题池」「AgentConsole 功能候选」都在那里，按编号引用（R1、M1、D1……）。
- 进度日志里提到的「设计问题池第 N 条」对应关系：1→D1，2→D2，3→已完成（单写者），4→D3，5→D4，6→M8，7→R1。
- 「AgentConsole 功能候选第 N 条」对应 M1–M7。

## 研究线 E2：上下文压缩 = 页面置换
设计和状态见 `~/research/PRTS/`（README 是实验状态表）。背景见 `human/reports/2026-10-20-context-paging.md`。关键点：缺页可能是静默的，所以评价指标必须包括隐式缺页（因为缺信息而犯的错）。下一步是用本机 rollout 做离线重放。

## 实验设计草案 E1：总控台 vs 单 agent vs 子 agent（2026-10-20，未执行）

**为什么难选场景**：agent OS 只有在下面几个条件同时出现时才可能有优势：
- 任务超过一个上下文窗口；
- 多个任务并发，并且共享状态；
- 中途需要人类做决定；
- 中途会出故障。

如果场景太简单，单 agent 必然胜出。所以要准备两类工作包：
- **对照包**：预期没有差别，用来检验实验本身是否公平；
- **压力包**：同时具备上面四个条件。

**可重放的真实工作包**：从自己的仓库里冻结某个 commit，取约 6 个任务，每个任务都配上隐藏的验收脚本。
- T1：整理积压改动并提交。验收：与快照的 diff 为空，测试通过。
- T2：给 ledger 加一个功能并导入。验收：测试通过，隐藏 fixture 也通过。
- T3：写一份带源码引用的调研笔记。验收：脚本随机抽查引用是否准确。
- T4：做到中途需要人类决定。由脚本模拟人类，按固定答案回答。
- T5：注入故障，例如 `.git` 只读或断网。
- T6：两个任务要写同一个共享文件，制造冲突。

**三个条件**，worker 用同一模型，任务文本相同，都从同一 commit 新建 worktree，每个条件重复 3 次：
- A：一个 Codex session 顺序完成全部任务。
- B：一个 Codex 开 multi_agent 子 agent。
- C：PRTS 总控，即 Claude + 确定性 supervisor + 登记表 + 事件触发的抽查。

**指标**：
- 隐藏验收的通过率；
- 打断人类的次数，以及其中有必要的比例；
- **虚报完成数**（声称完成但验收不通过）；
- 冲突和返工；
- token 和成本；
- 墙钟时间；
- 总控消耗的上下文。

**已有的试点证据（n=1，2026-10-19 夜间）**：
- 派发前没有查登记表，导致一个 worker 重复劳动。这说明登记表有价值。
- 沙箱的 `.git` 只读导致提交失败。worker 如实上报了，没有虚报；总控抽查后补救。这说明“验收层”有价值。
- 以上都是轶事，不能当作结论。

**下一步**：先用 T1、T2、T5 做一个三任务的小试点，把验收脚本和模拟人类的脚本写出来，用来检验这个实验能不能跑通。

---

# 一、背景：当前 Agent 能力与人与 AI 交互的问题

## 1.1 从 Chatbot 到 Agent：能力与交互模式正在发生变化

传统 LLM 主要遵循同步的 Request–Response 模式：

- 人提出问题。
- 模型思考并返回答案。
- 人检查答案，继续提出问题。

现在，Codex、Claude Code 以及其他 Agent 系统已经可以读取工程文件、修改代码、运行命令、执行测试、调用外部服务、管理任务上下文，甚至将任务交给子 Agent。

这一变化意味着 Agent 不再只是回答问题的工具，而是逐渐成为能够承担具体工作的执行主体。

但由此出现了新的问题：

**当 Agent 可以在没有人类持续参与的情况下执行工作时，究竟应该如何组织这种工作？**

现有系统已经支持不同程度的并行执行、自动化、记忆和后台任务，但长期自主执行、跨任务管理、人类干预策略等能力仍有改进空间。

PRTS 所考虑的不是重新发明一个模型，而是研究这些 Agent 之上的运行与交互机制。

## 1.2 核心矛盾：AI 执行速度逐渐超过人类监督速度

这是我们最早明确提出的核心问题之一。

在软件开发中，Agent 已经可以很快地完成一个任务、修改大量代码、产生复杂的设计方案。

但人类仍然需要：

- 理解它做了什么。
- 判断是否符合自己的目标。
- 检查重要决策。
- 处理异常与歧义。
- 将结果与其他项目或长期计划整合。

于是出现两种不理想的极端。

**极端 A：人类监督每一步。**

人不得不持续阅读 Agent 的输出、审批操作、处理询问。Agent 虽然执行得更快，但人的注意力成为整个系统的瓶颈。

**极端 B：Agent 完全自主。**

人不再知道系统具体做到了哪里，也难以及时发现方向错误、约束遗失、隐含假设改变或者重要决策被擅自完成。

真正的问题并不是在这两个极端中作出选择，而是：

> 如何在尽量减少人类注意力投入的同时，保留必要的决策权、可理解性与纠错能力？

我们曾把这一方向概括为：

**Agentic OS 可以被理解为一个管理 Human Attention 的 Control Plane。**

它不仅管理 CPU、内存、Token 和工具调用，也管理有限且昂贵的人类注意力。

不过，这还是一个有待具体化和验证的研究视角，而非已经完成的系统定义。

## 1.3 现有交互方式的几个结构性问题

### A. 任务与 Session 的碎片化

现实工作具有长期目标和复杂依赖。

但 Agent 的工作经常被分散到不同的 Chat、Thread、Session、Worktree、应用和机器中。

这些对象并不天然对应一个完整的项目。

例如：

- 一个研究项目可能同时包含文献调研、代码实验和报告编写。
- 一个 Agent 完成了实验，另一个 Agent 不知道其结果。
- 历史对话保留着当时的判断，但现实中的项目文件已经改变。
- 人类需要反复解释相同背景。

问题不仅是如何保存更多对话，更是：

**如何形成持续、可恢复、跨 Session 一致的工作状态？**

### B. 上下文增长、压缩与记忆可靠性

长时运行的 Agent 必然积累大量历史信息。

但上下文窗口有限，完整重放成本高，压缩又可能丢失重要内容。

我们特别关心：

- 哪些内容是长期约束，不能遗忘？
- 哪些只是已经过时的计划？
- 哪些是事实，哪些是推测？
- 某个结论是否仍然被当前的文件和实验结果支持？
- 多个 Agent 如何获得适合各自工作的上下文？
- 是否需要让所有 Agent 共享全部信息？

单纯增加上下文长度，未必能解决状态一致性问题。

一个有价值的区分是：

**对话历史不是系统状态，摘要不是事实来源，记忆也不等于授权。**

### C. 人类询问、审批与等待造成执行中断

Agent 执行过程中经常遇到不确定性。

有些确实必须询问人，例如架构取舍或不可逆操作；有些则可以采用合理默认值继续执行。

如果全部询问，会造成大量不必要的打断。

如果全部自行决定，又可能偏离意图。

因此需要研究：

- 什么情况下应该询问？
- 什么时候可以采用默认策略？
- 哪些决定可以延迟？
- 能否先完成不依赖人类回答的其他工作？
- 多个 Agent 的问题是否应该合并处理？

我们的一个早期设想是 **Agent Queue**：

它不只是等待 Agent 执行的任务队列，更重要的是记录：

> 哪些工作在交给 Agent 之前，仍然存在必须由人类解除的依赖（Human Dependencies）？

这进一步引出了人机协作中的异步调度问题。

### D. 可观测性不足与结果验证困难

Agent 可能报告“已经完成”，但实际情况可能是：

- 修改了文件但未测试。
- 运行了测试但没有覆盖关键需求。
- 完成了某个局部任务但没有推进整体目标。
- 工作被限流、断线、依赖缺失或权限问题阻塞。
- 中间结果被更新，旧结论却仍然被其他 Agent 使用。

因此我们希望区分：

1. Agent 声称自己完成了什么。
2. 系统记录它实际上执行了什么。
3. 外部证据能够验证什么。
4. 人类最终接受了什么。

这使得日志、执行轨迹、文件差异、测试结果、状态快照和来源记录成为重要的系统组成部分。

它也关系到 Agent 能否可靠地解释自己的工作。

### E. 多 Agent 并发缺乏高层协调

目前已经可以同时运行多个 Agent，但能启动多个 Agent 不等于能够有效管理多个 Agent。

我们关心的问题包括：

- 谁决定任务应该分配给哪个 Agent？
- 如何判断任务可以并行还是必须串行？
- 是否允许一个 Agent 修改另一个 Agent 正在依赖的状态？
- 哪些信息需要同步？
- 如何检测重复劳动与冲突？
- Agent 的结果是直接写入共享状态，还是提交待验证的变更？
- 谁负责将局部结果整合到长期目标中？

这里的重点不是简单的 Agent 数量，而是 **协作结构、状态一致性与任务所有权**。

### F. 长期自主性带来的安全、资源和信任问题

长期运行意味着系统可能持续访问设备、文件、账户和服务。

这会带来：

- 误操作的影响范围扩大。
- 权限长期存在带来的风险。
- 隐私和个人活动数据的治理问题。
- Token、API 调用、CPU、内存、电量的持续消耗。
- Agent 空闲、休眠、唤醒、超时与失败恢复问题。

PRTS 的最终愿景是具有很高设备访问能力的个人 Agent，但这不意味着无条件批准所有操作。

应当区分：

**能够访问某项资源、被授权执行某项操作、以及应该在当前情境中执行该操作。**

---

# 二、PRTS 的设想：从全天候个人 Agent 到注意力与任务运行系统

## 2.1 项目的历史演化

PRTS 并不是一开始就被设计为 Agent Runtime。

其演化大致有四个阶段。

### 阶段 1：Chronos——个人时间与任务管理

最初的 Chronos 主要围绕：

- 时间轴上的日程与提醒。
- 将模糊任务拆分为可执行事项。
- 跟踪计划和执行情况。
- 观察用户正在做什么。
- 根据状态提供提醒或调整建议。

早期软件已经有时间轴前端与部分状态监督功能。

但实际开发暴露了问题：为了建立一个完整的个人管理系统，容易投入大量精力自研任务类型、数据库、运行时、前端和服务间接口。

这些工程工作未必直接推进最终目标。

### 阶段 2：Ambient / Jarvis——持续存在的个人智能体

进一步的设想不再局限于日程管理。

我们希望系统能够整合不同来源的信息，逐渐了解用户的长期目标和实时状态，并在合适时机主动工作。

核心是从被动等待输入，转向长期持续的服务。

例如：

- 用户正在上课，系统能够更新课程相关上下文。
- 用户正在完成项目，系统能够了解当前进度。
- 用户提出一个灵感，系统能够保存、分类并在之后继续推进。
- 用户不主动询问时，系统仍能处理已授权的工作。
- 用户重新回来时，系统能够解释这段时间发生了什么。

这更接近一个持续工作的个人 Agent，而非一组独立 Chatbot。

### 阶段 3：不再从零实现所有专用 Agent

2026 年 10 月前后，一个重要策略变化是：

**不再优先为每一种需求独立开发完整的专用 Agent。**

此前的 Chronos、Tanngo、Note 等项目存在不同程度的功能重叠，而 Codex、ChatGPT 等现有系统的通用执行能力迅速增强。

因此新的倾向是：

- 直接使用成熟 Agent 完成具体任务。
- 尽量减少自研的模型调用循环和通用工具系统。
- 必须自己维护的内容集中在个人长期状态、任务、权限、协作与交互机制。
- 在理解真实问题之前，不提前冻结庞大的数据结构和服务架构。

Tanngo 的复习需求可以并入通用工作流；Note 的部分能力可以通过 GPT 与已有 Ear 数据管线完成，而不必继续扩展独立系统。

### 阶段 4：PRTS——Personal Runtime System

项目最终命名为 PRTS，定位逐渐从个人应用转向 **Systems for Agents**。

即：把成熟的 Agent 视为执行主体，探索其上层或周围所需要的运行机制。

PRTS 不是另写一个操作系统内核，也不是重新训练基础模型。

目前较清晰的方向是：

> 面向长期目标与持续运行场景，为个人提供协调 Agent、组织任务状态、管理上下文、分配人类注意力和控制执行权限的系统机制。

但其最终研究边界仍然开放。

## 2.2 24h Agent：持续工作，而不是持续推理

这是愿景中最明确的部分。

理想情况下，Agent 可以在一天的大部分时间内持续承担工作，而不是每次都需要人类重新启动一次对话。

但这不应等同于让 LLM 永远运行推理循环。

更合理的候选模式是：

- 系统轻量常驻。
- 根据事件、定时器和任务状态唤醒。
- 有工作时启动合适的 Agent。
- 外部条件尚未满足时进入等待。
- 可以休眠和恢复。
- 出错时有明确的恢复策略。
- 用户可以随时暂停、干预或改变方向。

曾经遇到的实际问题是：Chronos 的 ambient 运行可能让 MacBook Air 长期占用资源、发热和耗电。

所以 **24h 可用性和计算资源的有效管理** 本身就是系统需求，而不是附带优化。

未来也可能考虑本地设备与云端运行环境的配合。

## 2.3 系统需要理解三种层次的状态

我们曾提出 PRTS 第一阶段的一个核心目标：

**识别用户正在做什么。**

但这里的“正在做”至少有三个层次。

### 长期层：Goals / Projects

例如：

- 本学期课程与实验。
- PRTS 研究与工程。
- Neuroscience 与 SwarmBot 的探索。
- Outreach 与申请。
- 长期学习任务。

这一层回答：我在努力实现哪些目标？

### 中期层：Tasks / WorkItems

例如：

- 完成某个 OS 实验。
- 阅读一组论文。
- 调试某个项目。
- 准备一份研究计划。

这一层回答：哪些工作正在推进，哪些已经完成或被阻塞？

### 短期与实时层：Activity / Current Context

例如：

- 当前正在使用什么工具。
- 正在上课、阅读、编程还是休息。
- 某个执行中的 Agent 正在做什么。
- 最近有没有新的事件改变当前计划。

这一层回答：此时此刻发生了什么？

一个重要原则是：**不要将观察推断直接当作事实。**

比如看到某个编辑器处于前台，不意味着用户一定在认真编程；检测到课程录音，也不意味着所有 ASR 内容都与课堂有关。

需要保留信息来源、时间和不确定性。

## 2.4 信息来源与个人计算环境

设想中的主要输入与输出来源包括：

| 来源 | 可能承担的功能 |
|---|---|
| Ear / Octopus | 音频、ASR、人物、事件及环境上下文 |
| 清华 Info / 网络学堂 | 课程、作业、通知等信息 |
| 微信 | 移动端快速输入、消息、轻量秘书和提醒 |
| Apple Calendar / Reminders | 日程、提醒、任务状态 |
| Codex / Claude Code | 工程任务执行、状态与结果 |
| 本机系统与项目文件 | 工作状态、文件变更、运行环境和执行证据 |
| ChatGPT | 研究讨论、推理、规划、解释和辅助分析 |

其中部分已经有独立工程基础，但 **这些来源尚未被统一为可工作的 PRTS 系统**。

例如 Ear 有现成的音频分析和层级事件表示；Chronos 已有部分时间轴与状态监督能力；CodexBridge 可以作为微信侧轻量入口。

我们曾讨论 Eye：是否需要独立的计算机或手机活动观察服务，但并未决定必须实现 Eye，也不能假定它已经存在。

同样，心理状态、疲劳和认知负荷的推断目前仍属于探索性设想。

## 2.5 WorkItem：将模糊意图转变成可持续推进的工作

Chronos 时期，我们讨论过一个有价值的区分：

**创造一项工作** 和 **执行一项工作**，并不是同一件事。

一个人可能想到：

“我应该研究一下小模型能否承担 Agent 调度决策。”

但这不意味着已经形成了可执行任务。

这件事可能需要：

- 界定问题。
- 查阅已有研究。
- 形成具体假设。
- 确定实验与比较基线。
- 安排资源。
- 交给合适的执行者。

因此，一个候选的 WorkItem 模型可能含有：

- Goal：目标。
- Context：背景和约束。
- Dependencies：依赖。
- Owner：当前责任主体。
- State：当前状态。
- Next Action：下一步动作。
- Evidence：可验证证据。
- Human Decision：等待人类回答的问题。

这里真正重要的不是字段名字，而是：

**工作应当具有独立于对话 Session 的身份、状态和生命周期。**

人类不必记住 Agent 对话的全部内容，Agent 也不必靠反复阅读历史聊天才能判断下一步。

但目前不应该为此提前设计庞大的数据库。

## 2.6 人类注意力：PRTS 最有研究价值的资源之一

传统 OS 的调度主要围绕计算资源。

但在 Human-Agent 系统中，人类具有非常不同的特征：

- 注意力有限。
- 不同任务之间存在切换成本。
- 疲劳会影响判断。
- 某些决策不能由 Agent 替代。
- 长期目标并不总能用简单优先级表示。

Agent 与 Human 不应该被简单抽象成两种等价 Worker。

一个可能的方向是将系统事件分为不同注意力等级：

**L0：静默记录。**

普通执行进度、工具调用、例行成功和低风险状态变化。

**L1：可随时查看的解释。**

阶段总结、风险提示、下一步计划、多个项目的综合状态。

**L2：需要中断人类的事件。**

重大架构取舍、难以恢复的操作、关键目标冲突、连续失败或者不可自行消除的歧义。

这一分层只是候选机制，分类标准、动态优先级和触发阈值仍需实验。

更进一步的研究问题是：

> 对于一个事件，在什么条件下应当立即打断用户，延迟汇报，或者交给 Agent 自行处理？

可以考虑任务收益、风险、紧急程度、用户的当前活动和切换成本等变量，但不应预设一个未经验证的效用函数。

## 2.7 Observer / Explainer：让 Agent 能解释自己在做什么

长期 Agent 不应只有执行能力。

系统还应能随时回答：

- 已经完成了什么？
- 正在做什么？
- 下一步准备做什么？
- 为什么做这件事？
- 什么正在阻止它继续？
- 哪些决定需要我来作出？
- 上一段自主执行期间发生了什么？

早期构想是独立的 Observer / Explainer。

这里至少存在两种能力：

**Observability：系统能够提供真实、结构化、可追溯的运行状态。**

**Explanation：模型能够面向人类解释这些状态，并指出有意义的问题。**

不能用后者替代前者。

理想情况下，解释来自真实的任务状态和执行日志，而不是另一个 LLM 对原始聊天记录的主观总结。

至于 Observer 是否具有暂停 Agent、修改任务或重新调度的权力，仍未决定。

## 2.8 多 Agent 合作：水平分工与垂直分工

2026 年 10 月 18 日，我们讨论了 GPT、Claude 和 Codex 的职责分配。

存在两条路线。

### 水平分工

将相对独立的研究或项目分配给不同 Agent。

例如 PRTS、SwarmBot、NeuroScience 三条研究线可以部分独立推进，从而减少上下文耦合和协调成本。

这种方式适合独立任务，但不一定解决同一个复杂项目的长期监督问题。

### 垂直分工

按照抽象层级和职责进行分工。

一个候选结构为：

- Human：设定目标、控制关键取舍、验收重要成果。
- GPT / Claude：研究、规划、解释、综合分析。
- Claude Supervisor：项目阶段监督、风险检查、汇报与任务协调。
- Deterministic Control Plane：保存任务状态、执行权限、路由规则与事件。
- Codex Workers：具体编程、测试、修改文件和提交结果。

这并不意味着必须单独运行五种服务。

相反，关键问题是：**哪些层次确实值得拆开，哪些现有产品已经可以承担？**

尤其需要避免另一个强模型持续盯着 Codex 的每一步，最终使监督成本大于收益。

一个更有希望的候选模式是：

- 正常执行时仅记录事件。
- 阶段完成时审查关键产物。
- 失败或异常时启动分析。
- 重大决策升级给人。
- 汇报聚焦于重要变化。

这仍需要与单 Agent 执行、仅阶段监督以及持续监督等基线比较。

## 2.9 自主性与 Self-improvement

我们还讨论过一个更远期的愿景：

当人没有新指令时，Agent 是否可以继续推进长期目标？

例如：

- 整理研究进度。
- 发现项目中的明显问题。
- 检查未完成任务。
- 阅读新资料。
- 提出改进建议。
- 维护必要的工作环境。

进一步，它是否能改进自己的 Prompt、工具和任务流程？

这与我希望了解的 RSI（Recursive Self-Improvement）相关。

但这里必须区分：

1. Agent 自主完成任务。
2. Agent 发现并提出工作流改进。
3. Agent 在验证后修改自身系统机制。
4. Agent 具有真正开放式的自我改进能力。

目前我只把它们作为不同层次的研究与实验问题，不认为现有 PRTS 已经能够进行开放式 RSI。

特别是系统对自身机制的修改必须具有验证、回退与权限边界。

---

# 三、参考方向：OS、分布式系统及其他研究范式

## 3.1 操作系统：从 Agent 执行循环到 Agent Runtime

这是 PRTS 最直接的理论参照之一。

但我希望借鉴的是操作系统解决问题的抽象和机制，而不是为了名称上的 Agentic OS 去重新实现 Linux 或修改内核。

候选映射如下：

| OS 概念 | 在 PRTS 中可研究的对应问题 |
|---|---|
| Process / Thread | Agent、Task、Session 的身份与生命周期 |
| Scheduling | 多任务和多 Agent 的优先级与执行安排 |
| Interrupt | Agent 何时打断用户或其他任务 |
| Blocking / Wakeup | 等待人类回答、外部事件或资源 |
| Memory Management | 上下文保留、压缩、检索、失效 |
| IPC | Agent 间消息、任务交接与结果传递 |
| Filesystem / Persistence | 长期状态、记录和可恢复工作 |
| Isolation | Worktree、Sandbox、任务资源边界 |
| Capability / Permission | 哪个 Agent 能执行什么操作 |
| Resource Accounting | Token、延迟、成本、CPU、能耗 |
| Checkpoint / Recovery | 暂停、断线恢复、失败回滚 |
| Observability | 状态、日志、追踪与性能分析 |

这一类比的价值，在于把表面上模糊的 Agent 协作问题拆解成可以分析的系统机制。

但不能机械照搬。

例如 Agent 一次推理调用不等于 CPU 的时间片，语义任务的调度成本也不能只用执行时间衡量。

OS 是重要的启发来源，而非自动正确的答案。

### 与当前 OS 学习的联系

我正在学习 rCore / Rust OS，课程包含任务管理、地址空间、进程、文件系统、IPC、并发等内容。

这可以成为理解系统设计原则的基础。

但 PRTS 研究不必直接依赖底层内核实现，优先关注能转化为实际 Agent 问题的抽象和机制。

## 3.2 分布式系统：状态一致性、异步执行与恢复

当多个 Agent 在不同 Session、设备或服务上工作时，问题逐渐接近分布式系统。

尤其值得考虑：

### 任务队列与异步消息

Agent 可以提交结果、等待依赖、订阅事件，而不必全体保持同步运行。

### 事件记录与状态恢复

一个 Agent 为什么进入当前状态，应当能够根据持久化记录解释，而不是依赖它当前的上下文窗口。

### 幂等性

断线重试或重复消费结果时，不应该造成重复执行和重复写入。

### 一致性与冲突控制

两个 Agent 基于不同版本的项目状态行动时，需要识别冲突。

### 事务与回滚

重要操作应当具有清晰的提交边界，并尽可能支持恢复。

### 故障模型

区分 Agent 推理失败、工具失败、网络失败、权限失败、运行环境失败与任务条件尚未满足。

这里并非所有分布式系统技术都需要实现。

真正需要研究的是：在具体的 Agent 场景中，哪些一致性和恢复保证有实际价值，成本又有多高？

## 3.3 控制论：闭环监督、状态估计与决策

我们曾讨论过 Control Theory、Observer、MPC 等理论是否能为 PRTS 提供参考。

直观上存在相似性：

- 系统有目标状态。
- 环境不断变化。
- Agent 对环境施加动作。
- Observer 获取测量信息。
- 系统根据反馈调整行动。

但 Agent 与人机协作不是简单的连续动力学系统。

长期目标可能无法充分数学化，人的偏好不稳定，操作和观测之间也存在语义上的不确定性。

因此控制论目前是 **候选解释框架**，不是必须采用的总体架构。

比较值得探索的是：

- 可观测性与可控制性。
- 状态估计与不确定性。
- 有反馈的任务执行。
- 多层时间尺度上的决策。
- 异常检测与纠偏。

是否需要 MPC、POMDP、形式化的效用函数或其他控制算法，应当由真实问题决定。

## 3.4 认知科学、心理学与人机交互

如果 PRTS 的核心之一是管理人类注意力，那么只参考计算机 OS 显然不够。

我们讨论过需要了解：

- 注意力切换成本。
- 认知负荷与工作记忆。
- 中断时机与任务恢复。
- 疲劳和决策能力变化。
- 人与自动化系统之间的信任。
- Human-AI Shared Autonomy。
- 用户对自主 Agent 的控制感。

一个基本区别是：

**人类不是响应时间更慢的 Agent。**

人的注意力结构、目标变化、动机和社会责任，使得“人机资源调度”不同于普通计算资源调度。

但目前不准备直接建立一个心理状态预测模型，也不希望过早引入无法验证的生物学叙事。

这条方向需要先做文献与已有系统调查。

## 3.5 类型系统、形式化方法与权限

这与我目前学习的类型系统和未来想了解的形式化方法存在联系。

长期运行系统中的一个重要问题是：

哪些行为只需要 Agent 提议，哪些可以自动执行，哪些必须具备特定授权？

可以考虑：

- Typed Task / Typed Tool Invocation。
- 状态机约束。
- Capability-based Security。
- Effect Systems。
- Contracts / Preconditions / Postconditions。
- 不可逆操作的显式授权。
- 一部分安全性质的自动验证。

但形式化方法也存在边界。

例如可以检查某个操作是否具有权限，却不一定能形式化判断某份研究总结是否真正符合用户的长期学术兴趣。

因此可能需要将 **可验证的规则和语义性决策** 分开处理。

## 3.6 Agent 研究与现有平台：不要重复实现已经成熟的能力

2026 年 10 月，一个重要的现实变化是：

OpenAI、Anthropic 等已经在探索更长时间的 Agent、自主工作、上下文管理、多 Agent 协同与后台运行。

尤其是 dot 的推出，让我意识到最初设想的一部分可能已经成为商业产品的明确方向。

因此，PRTS 不能仅仅因为“实现了 24 小时个人 Agent”就认为自己具有研究价值。

应该优先研究现有产品仍然不充分解决的问题，或提出可测量的系统改进。

### 值得调查的产品与平台

**Codex / Codex Harness**

- Agent Loop 与工具调用。
- Thread、Turn、Session。
- App Server、SDK 与程序化执行。
- Worktree、Sandbox、Approval。
- 执行日志和状态事件。
- 多 Agent 并行、上下文与恢复。

**Claude Code**

- 项目级记忆与上下文管理。
- Subagents、后台任务与任务分解。
- Hooks、Skills、权限控制。
- Agent SDK。
- 多 Agent 协作及长任务管理。

**OpenAI dot**

- 全天候工作。
- 云端执行与跨应用连接。
- 目标的长期推进。
- 主动工作、反馈与审批。
- 与人类注意力管理有关的交互设计。

应区分公开宣传、官方能力说明、实际可调用 API，以及自己环境中真正可以正常使用的功能。

### 值得阅读的研究工作

以下作为初始文献线索，而非已经完成的深入文献综述：

**AIOS: LLM Agent Operating System (2024)**  
https://arxiv.org/abs/2403.16971

研究将调度、上下文管理、存储和资源管理抽象为 Agent OS 服务。

**AgentRM: An OS-Inspired Resource Manager for LLM Agent Systems (2026)**  
https://arxiv.org/abs/2603.13110

直接研究 Agent 的调度问题、僵尸任务、限流级联和上下文退化。与 PRTS 的资源管理问题非常接近。

**Agent libOS (2026)**  
https://arxiv.org/abs/2606.03895

研究长期 Agent 的生命周期、权限、Human Queue、Checkpoint 和审计机制。可以作为系统层参照。

**ACON: Optimizing Context Compression for Long-horizon LLM Agents (2025)**  
https://arxiv.org/abs/2510.00615

研究长任务上下文压缩以及将压缩能力蒸馏给小模型。

**MemTrace: State-Consistent Memory for Long-Horizon Coding Agents (2026)**  
https://arxiv.org/abs/2610.04838

研究长期编码 Agent 的记忆与当前仓库状态的一致性。

这些工作说明，PRTS 的若干问题已经有人研究，因此需要进行严格的已有工作分析，不能默认具有新颖性。

## 3.7 小模型决策移交

在六条长期工作方向中，我还特别提出：

**研究能否将 Agent 的某些决策从强模型移交给小模型。**

这与 PRTS 有潜在关联。

例如：

- 事件分类。
- 任务路由。
- 是否需要唤醒强模型。
- 简单状态更新。
- 初步异常检测。
- 部分上下文压缩。

假设是这些操作可能具有相对稳定的输入输出结构，使用强模型未必总是最优。

但必须考虑误判的连锁后果。

例如一个廉价的小模型错误地判断某条信息不重要，可能导致整条长期任务线遗失关键约束。

因此需要比较计算成本、延迟、可靠性与错误代价，而不仅是小模型能否在单次分类上取得足够高的准确率。

## 3.8 研究范式：机制创新不能脱离强基线

我们对 PRTS 的研究价值曾有过一次重要争论。

问题是：

如果只是自研一个调度或记忆机制，在一个较弱的 Benchmark 上优于几个简单 Baseline，这种研究可能很难说明它对真正先进的 Agent 有什么价值。

另一方面，也不可能直接将 OpenAI 或 Anthropic 的商业产品作为完全透明、可随意修改的实验平台。

所以我们目前倾向于：

**先找到真实且可以复现的问题，再实现最小的可检验机制。**

比较理想的研究方式是：

1. 在已有强 Agent 上复现一个真实问题。
2. 明确问题究竟出在模型、Harness、任务设计还是系统运行机制。
3. 建立可重复的评估场景。
4. 在有限范围内实现一个机制。
5. 与强产品基线、简单系统基线比较。
6. 通过受控消融分析效果来自什么。
7. 判断这一发现具有多大的普适性。

不应在没有真实问题和评价依据之前，把完整 PRTS 原型视为论文成果。

---

# 附录 A：目前已经确定的选择

截至 2026 年 10 月 18 日，较为明确的共识包括：

1. **项目名称为 PRTS（Personal Runtime System）。** 它继承 Chronos、Jarvis 的个人 Agent 愿景，但研究兴趣逐渐转向 Systems for Agents。

2. **充分利用现有 Agent 能力。** 不优先自研通用 LLM Agent Loop、工具调用系统和整套编程执行器。

3. **24h 是长期愿景，但并不意味着 LLM 必须一直推理。** 资源占用与可靠恢复必须认真考虑。

4. **人类注意力、决策边界与任务状态是核心问题。** 不能让所有工作依赖人类逐步确认。

5. **保留长期目标和实际执行之间的区分。** WorkItem、Human Dependencies、Agent Queue 等仍是重要候选概念。

6. **当前关注三条学术研究方向：PRTS、SwarmBot、NeuroScience。** 其中 PRTS 与已有 HCI、软件工程、Agent 使用经验联系最直接。

7. **PRTS 兼具工程和研究目标。** 工程上可以先追求可用，研究上则需要独立建立假设、验证与基线。

8. **分阶段实现。** 尽可能让每一轮工程改动具有可以手工测试的最小目标。

9. **保留人类对重要操作的控制权。** 高权限 Agent 不等于无约束 Agent。

10. **通过真实证据评价 Agent 工作。** 不把自然语言总结等同于实际完成情况。

# 附录 B：仍然开放的问题

以下问题不应该被 Claude 或 Codex 擅自视为已经决定。

### 产品与系统边界

- PRTS 究竟是独立 App、后台服务、Agent Harness 扩展，还是一组轻量协调机制？
- 应该在 Codex 之上增加哪些能力？
- dot 等现有产品已经解决到什么程度？
- 用户个人数据应由什么系统维护为权威来源？

### 调度与自主性

- Agent 在用户不参与时应该主动推进哪些任务？
- 多项目之间如何分配优先级？
- 何时应该暂停、等待、切换或继续？
- 可以自主修改计划到什么程度？
- 是否需要不同 Agent 之间的抢占机制？

### 人类注意力

- 如何定义一次有效的打断？
- 是否能够测量减少的人类注意力投入？
- 问题批处理是否比实时澄清更有效？
- 人类的注意力状态是否值得被显式建模？
- 如何避免系统为了减少打断而隐藏重要风险？

### 上下文与记忆

- 工作状态由什么数据结构表示？
- 如何处理相互矛盾或已经过期的记忆？
- 不同 Agent 的上下文应该共享到什么程度？
- 如何验证压缩后的状态没有丢失关键约束？
- 怎样让长任务能够跨 Session 恢复？

### 权限与监督

- 哪些操作需要人类批准？
- Observer 只是解释，还是能够控制 Executor？
- 是否应当采用分层 Agent 管理模式？
- Supervisor 的额外成本能否带来实质收益？
- 如何处理 Agent 自己修改系统规则的问题？

### 学术研究

- PRTS 的哪个问题真正具有足够强的新颖性？
- 已有系统研究在多大程度上覆盖这些问题？
- 能否设计兼具真实性与可重复性的测试任务？
- 如何证明机制有效，而不是模型或 Prompt 恰好更好？
- 最适合的研究领域究竟是 Systems、HCI、Agent Research，还是它们的交叉？

---

# 附录 C：当前工程状态与下一步原则

## 已有基础

- Chronos：时间轴、日程提醒、部分状态监督逻辑，以及用于授权修改和记录的旧 Runtime。旧 Runtime 不是完整的长期调度器。
- Ear / Octopus：音频、ASR、人物及事件分析管线，可作为未来的环境信息来源。
- Codex：本地编程与执行能力，已经用于多个项目。
- Claude Code：准备参与项目监督、研究及工程协调。
- CodexBridge / 微信：已有移动端轻量秘书方向的实践。
- macOS、Linux、云端 VM：已有多个执行环境。

## 尚未完成

- 统一的 PRTS Runtime。
- 可靠的全天候个人状态管理。
- 完整的跨 Agent 调度。
- 已验证的注意力优化机制。
- 跨 Agent 一致性与恢复机制。
- 小模型决策移交实验。
- 正式研究 Benchmark 与系统论文。

这些不能仅因为已有相关组件，就认为已经实现。

## 近期合理路线

**第一步：调查现有技术。**

真正理解 Codex、Claude Code 等已有的 Agent Loop、上下文、调度、权限、恢复机制，建立清晰的系统能力地图。

**第二步：选择真实问题。**

优先使用自己的研究和工程任务作为持续运行的测试环境，而不是立即建立一个庞大且虚构的任务世界。

**第三步：构建最小闭环。**

例如在一个真实项目中验证：

目标定义 → Agent 执行 → 状态记录 → 阶段验证 → 异常升级 → 人类决策 → Agent 恢复。

先保证这些环节真实、可靠、可观测。

**第四步：逐步引入自主调度。**

从单任务、单 Executor 出发，再尝试多任务、异步事件和多个 Agent。

**第五步：抽取可研究的机制。**

例如注意力分配策略、Supervisor 触发策略、状态恢复、跨 Agent 上下文同步或资源调度。

每次只针对明确的问题建立最小实验，并与合理基线比较。

## 可能采用的评估指标

- Human Attention：实际监督时间、打断次数、人工决策成本。
- Task Quality：任务成功率、测试结果、错误与返工数量。
- Latency：完成时间、等待时间、任务阻塞时间。
- Reliability：断线恢复、重复执行、状态一致性。
- Efficiency：Token、API 成本、CPU、内存、能耗。
- Controllability：人类发现、纠正和撤销错误的能力。
- Provenance：系统结论与实际执行证据的对应程度。

需要先设计合理的测量方法，不能直接把这些名称视为有效指标。

---

# 附录 D：Claude 应如何理解并参与 PRTS

希望 Claude 在后续合作中遵守以下原则：

1. **将本文作为项目背景，不是固定施工命令。** 未明确决定的架构和研究路线，仍然可以讨论和推翻。

2. **区分事实、已定目标、技术假设、研究问题与工程建议。** 特别不要将 GPT 过去提出的候选方案自动当成我的最终选择。

3. **优先调查已有实现。** 对 Codex、Claude Code、dot 和其他现有技术有能力解决的问题，不应未经调查便建议自研。

4. **工程上保持最小实现。** 优先直接使用现有能力；每一次新增模块都应能指出它解决的具体问题。

5. **研究上保持开放。** 不以证明 PRTS 架构正确为前提，而是允许实际研究发现某些功能根本不需要实现。

6. **解释时要区分机制和模型能力。** 尤其不要把增强 Prompt、换更强模型和真正改善系统机制混为一谈。

7. **对于长期任务，优先提供阶段性结果、关键证据和需要人类决定的问题。** 不以大量过程日志替代有效汇报。

8. **与 Codex 的职责分配仍在探索中。** 可以考虑由 Codex 执行、Claude 监督与综合，但必须评估额外协调的收益与成本。

9. **保留科研目标。** PRTS 不仅是要做一个自用的 Jarvis，也可能发展为与 Agent Runtime、OS、Distributed Systems、HCI 交叉的科研方向。

10. **允许项目持续演化。** 当前最重要的不是给 PRTS 画出最终架构，而是找到足够真实、重要且可以验证的研究问题。


11. **把用户的有效时间留给输入和输出。**（2026-11-12 用户补充，总控记录）用户的有效大脑时间应主要用于学习（输入）和创造（输出）：读文献、教学材料和 AI 概括，和 agent 讨论概念；设计实验、设计项目的输入输出和用户体验、发散、手写代码、写作。工程实现的杂务（包括和 agent 讨论架构）应尽可能交给 agent 完成。PRTS 好不好，最终要看它是否增加了用户的输入和输出时间。定义见 `~/PRTS/pulse/README.md`。
---

# 最终定位

PRTS 的长期愿景是：

**建立一个能够持续理解人的目标和工作状态、协调多个 Agent 自主执行、妥善利用计算与人类注意力，并且始终保持可观测、可纠正和可控制的个人智能运行系统。**

如果从研究角度进一步浓缩，当前最值得调查的问题是：

> **当 Agent 能力已经足以承担长期任务时，我们需要怎样的系统机制，使自主执行、共享状态、资源管理与人类决策能够可靠地协同？**

这不是一个已经确定答案的问题。PRTS 应当首先成为探索它的工具和实验平台，而非预先假定自己就是答案。
| 2026-11-13 | 用户要求今晚专注：先运动，回来学 agent 框架（DsHarness、比较 Codex/opencode 的设计），在 Ear 调试等事上走神太久就提醒。Codex 实现 `pulse focus`（555f868）；总控在沙盒外用真实模型回放，判定合理（视频、EarRecorder 联调、OS 选题都判为偏离）。已 set 今晚时段到 01:30；`com.prts.pulse-focus` 由用户安装。 |
| 2026-11-14 | 每日回顾修复：11-13 23:40 首次跑满一整天 Computer History，接连撞上 ARG_MAX、Codex 104 万字符输入上限、Bark 4 KB 负载上限（413）。改为 stdin 传提示词、按窗口压缩并分批分类、Bark 按字节截断（c7f5703、550b48c、7c2ba12）。用户问 Mac 上在哪看全文 → 日报全文写进 Apple 备忘录「PRTS 日报」（同名替换），推送只带前 8 行，点开打开备忘录。超长段（Codex session 跨度当成段起止）派 Codex 修（pulse-span-fix）。 |
| 2026-11-14 | 超长段修复验收（pulse-span-fix）：根因是 Codex 来源把整个 session 的 min/max 当段起止，render 再按外包跨度挂「同时」；改为实际区间，加跨度不变量警告；续改显示（间隔 ≤15 分合并，最多显示 2 个范围）621d6a8。**教训**：Codex 只暂存未提交时，总控 `git add 指定路径 && git commit` 会把 index 里 Codex 的改动一起提交——f76a919 因此混入了 pulse 修复且已推送。以后 Codex 在同仓库跑时用 `git commit <路径>…`，派任务时要求 Codex 自己按路径提交。 |
| 2026-11-14 | DeepSeek Harness 导读 session（local_6c93f091）在 PRTS main 上合入 R17（event 慢速模型分诊，白名单默认关，抽出共享 `interaction/lib/schema.py`、`run_model.py`，ear.py 改用它）和 R18 B0（`interaction/bin/github_poll`，launchd 模板未安装）：71fc1c9/b032fb6、36cdf91/8b8407b、47908f0。R18 B1/B2 待派。总控已核对提交存在。 |
| 2026-11-14 | 用户要求看 DsHarness session 给 PRTS 加的新架构（R17 事件慢速分诊、R18 B0 GitHub 轮询）。复核：代码和测试全绿、默认关闭、未装定时器；B0 有 4 个缺口（缺结构化 thread_key、漏看 reviews、updatedAt/自身动作产生噪音、R17 与 B0 没接上），已写进 ROADMAP R18。 |
| 2026-11-14 | 用户对 DS 新架构的方向调整：PRTS 是 personal agent，来源以 Computer History/Ear 为主；fast path 既滤噪也直通；订阅单位是「项目组」。另立 R19 提前行动（上课→拉网络学堂课件）、R20 链式召回实验（对应研究层 E2 存根）、R21 全双工（本机 Codex app-server 有 `turn/steer`）。写入 ROADMAP。 |
| 2026-11-14 | 项目归属（9142c87）：规则优先，模型在分类时顺带补，不硬归。11-13 真实重算（总控在沙盒外跑）：不属于项目 356→105 分；归属来源 rule 52 / model 154 / none 375 段。抽样：模型归上的 10 段全对（OS 课、EchoAsRecord、AIInfra 等），不属于项目的 10 段都合理（历史视频、股票页、微信、空白标签页）。遗留：PRTS 有三个名字（PRTS / PRTS 总控台 / PRTS 总控台（主 session）），本日 project_hint 为空。 |
| 2026-11-14 | PRTS 三个名字合并（用户同意）：来源分别是 ChatGPT 里的项目名「PRTS」（规则从 ChatGPT 项目页拿到，再被模型当候选选用）、`~/PRTS` 的登记名「PRTS 总控台」、家目录 exact 项「PRTS 总控台（主 session）」。projects.toml 加 `aliases` 支持，家目录项改名为「PRTS 总控台」，另登记 `~/research/PRTS` 为「PRTS 研究」。11-13 重渲染后合成一行 43.7 分。同类遗留：OS 课有「OS 课（rCore）」（lain 路径）和「Infra」（本机 ~/research/Infra/os-course 的 cwd 名）两行。 |
| 2026-11-14 | OS 课两个名字合并（用户同意）：`~/research/Infra` 登记为「OS 课（rCore）」，并加别名 Infra。11-13 合成一行 60.2 分。注意：Infra 以后若开始做 PRTS 硬件层探索，要给那个子目录单独登记。 |
| 2026-11-14 | 用户下午在 Codex app 的「指导 EarRecorder 真机联调」对话里谈 Ear，总控已整理成 `~/research/EchoAsRecord/local-notes/2026-11-14-下午-EarRecorder联调与产品定位.md`。要点如下。<br>**产品定位（用户定）**：手机只是录音加 GPS 的工具，可被简单固件替代；用 Ear 就是在电脑上开 agent 用 MCP 查；不追求实时，不考虑电脑睡眠时的转写；不绑定苹果，Android 可做。<br>**昨晚积压 7h41m 的原因**：直连和备用同时不通。Shadowrocket 选新加坡节点时直连不通，这一点今天已复现，但昨晚用的哪个节点没有记录；备用的 Cloudflare Quick Tunnel 已失效。<br>**连接方案（用户同意）**：扫码配对认设备，同一局域网用 Bonjour 发现，跨网走中继。用户不让个人 Azure 用于公共服务，改为借用 Octopus 的 `vps.shiweinan.com:6950`，手机加密、中继只转发密文；模拟器已跑通，需要征得石伟男同意。<br>**下一步最该验证**：离线一天后能否补齐，以及 agent 能否看出数据同步到几点。<br>注意：这类对话在 Codex app 里，`~/.codex/state_5.sqlite` 的 threads 表可按标题找到 rollout 文件。 |
| 2026-11-14 | 新 Ear 链路的录音位置：EarRecorder（iOS）上传到 `~/.octopus/local/inbox/brain/ear-ios-<设备>/<日期>/phone/<开始时间>__<group>/`，30 分钟一段 m4a 加 Context。**归档段目前没有任何服务去转写**：ingest 没配 `EAR_INGEST_EVENT_URL`，不会通知旧 Ear；旧 Ear 今天一段都没处理。新的实时转写服务（`services/transcription`，未提交，SenseVoice 小模型 + sherpa-onnx）只接手机实时推送的短 PCM 块。这个服务是 Codex app「指导 EarRecorder 真机联调」在用户问「秒级体验怎么实现」（11-14 凌晨）之后搭的原型，模型选型没在回复里告诉用户。用户 11-14 说下午录音先不急着转写。 |
| 2026-11-14 | 新 Ear 链路核对：本机跑着 3 个 ingest。8791（直连）和 8792（配对，HTTPS）是手机实际在用的，都没配 `EAR_INGEST_EVENT_URL`，文件只落在 `~/.octopus/local/inbox/brain`，没人转写。8795 是 Codex 的隔离测试实例，有自己的 inbox，并接到 EarRecognition（8794，旧 Ear 后端的独立副本）。用户记得的「跑通过一次」就是这个测试实例，EarRecognition 库里只有 1 个 capture。ASR 对比：旧 Ear 用 MOSS-Transcribe-Diarize（Whisper 编码器 + Qwen3-0.6B，约 0.9B 参数，bf16 1.7 GB，在 lain 的 GPU 上跑，转写和分说话人一起做）；新的实时原型用 SenseVoice-Small（约 2.3 亿参数，int8 237 MB，本机 CPU，不分说话人）。新 Ear 的 ③ 活动划分、④ 按规则提取还没和 ① 完整联调（④ 是演示基线）。 |
| 2026-11-14 | 用户下午在树林里口述（新 Ear 录音，MOSS 转写，16:37–18:43），总控整理成 `human/reports/2026-11-14-下午口述-许愿机与方向.md`，要点写入 yyj.md §4。结论：许愿机已基本成型，agent 优化到此为止；转向「基因预训练」的具身科学方向，加上钢铁侠或 SwarmBot 的工程方向；学习的目的是能够许愿。对 ROADMAP 的影响（R17–R21 降级、日报和提醒是否降级）等用户确认，还没改。新链路的转写读法见 `EchoAsRecord/local-notes/2026-11-14-ear-asr-ready.md`。 |
| 2026-11-15 | worktree：用户问为什么总要新建文件夹。原因是 Codex 的沙箱只能写 cwd 和 git 公共目录，不能自己 `git worktree add ../x`。11-14 Ear 那次因此另 clone 了一份 3.7 GB 的 `EchoAsRecord-split`。Codex 实现了 `dispatch --worktree` 和 `bin/worktrees list/clean`（c590885）；总控修了 squash 合并到非默认分支（dev）时识别不出来的问题。规则写进 AGENTS.md。Ear 项目架构 session 已把 5 个分支取回主仓库，split clone 以及 gps-geocode、wt-proposals 两个 worktree 都可以删，等用户确认。 |
| 2026-11-15 | 用户同意后，全局 CLAUDE.md 加了 worktree 规则。用户要求按 DS 规划实现 thread 和 fast/slow，并按 thread 改 AgentConsole 右半边（ROADMAP M10，来自 11-14 22:10 的口述）。因为 Claude 额度快用完，一次性派了两个 Codex 任务，设置 CODEX_TRIES=30、GAP=1800，可以撑过额度重置：`r18-threads`（PRTS：thread 字段、补 B0 四个缺口、五步 classify、Ear/Computer History 接入、subscribe、路由、`status threads --json` 契约、`review`）和 `ac-thread-view`（AgentConsole 按契约做前端，并行开发）。说明在 `interaction/state/prompts/`。验收等 Claude 额度恢复后做。 |
| 2026-11-15 | R18 个人版和 M10 验收（轻量，Claude 额度紧）：r18-threads 共 7 个提交，ac-thread-view 共 2 个提交。所有测试套件由总控复跑全绿。`status threads --json` 读真实数据得到 8 个 thread；新 Ear 原来没登记，补登记「Ear（EchoAsRecord）」后变成 9 个。AgentConsole 配置了 threads 和 review，已重启，`/api/threads` 返回 9 个 thread。没逐行审代码，没做浏览器验收。遗留：历史上 70 多个派发任务全部显示「未审查」，需要用户决定要不要批量标记已审查；订阅为空，filter 白名单为空（都默认关闭）。 |
| 2026-11-16 | 用户授权：「对于需要的任务，我给你开 codex 沙箱的权限」。需要联网或越出工作目录的任务，可以用 `dispatch --sandbox network\|full --approved-by "用户 11-16：对于需要的任务，我给你开codex沙箱的权限"`。只在任务确实需要时用，并在任务说明里写明为什么需要。注意：之前 full 派发被自动模式的分类器拦过，被拦就停下来告诉用户，不绕过。R24 已登记：pulse 以后改为读新 Ear 的活动层。 |
| 2026-11-16 | 日报接上新 Ear（Codex bc4fbbc）。remind 每小时、recap 每晚都会先跑 `pulse ear sync`，原来的 pulse-ear 定时模板删掉了。总控在沙箱外实测：14–15 号同步了 105 段，其中 high 5 段，正好是 11-14 下午的口述；餐馆、地铁闲聊判为 low。修了一个 bug：录音段被拿首段标题当成项目，又一度被 agent_work 的项目错归到 PRTS，现在录音一律归「线下」。14、15 号的日报已重新写进备忘录。 |
| 2026-11-16 | 三层视图上线（PRTS 6b066a0，AgentConsole 2f64dc3）。项目表按用户的分法加了 `group` 字段：PRTS（含 Ear）、具身与果蝇脑、机器人硬件（含芯动）、课程、工具与赚钱、Outreach。另外加了 `roadmap` 和 `roadmap_prefix`（PRTS 取 R，AgentConsole 取 M）。补登记 SomaNet、DsHarness、AgentConsole、Outreach。总控复跑测试全绿。遗留：团队成员只来自订阅和派发记录，没派过任务的桌面 session（例如 DsHarness、SomaNet、OS 课的 session）不在团队里；Ear 的实施计划格式解析不了，其他工程大多没有 ROADMAP。 |
| 2026-11-17 | 上周遗留处理：①日报只到 17:49，原因是全文有 4000 字上限，时间线被截断，加上固定在 23:40 生成；现在改为全文不截断，并按「一天真正结束」来生成（每小时的 remind 判断：各来源静默 90 分钟、逻辑日已过 18 小时，05:00 兜底），91622c4。重生成的 11-16 日报时间线排到 03:09。需要用户卸载 `com.prts.reporter-recap`，并重装每个整点都跑的 `reporter-remind`（命令见 reporter/README）。②工程团队按 cwd 收进桌面 session，4853588：DsHarness 2 人、SomaNet 2 人、OS 课 3 人。用户 11-16 交代：推荐信自己手写，不让 AI 代写；服务器、芯动的事明天由用户在别的机器上做，这边只记提醒。 |
| 2026-11-17 | M11 上线（AgentConsole c40c9e6、9b7c224；PRTS 9992bf7、083443e；roadmaps b708700 + 总控白话审核 8e79784）：8 个工程 67 条 roadmap 放在 `human/roadmaps/`；AgentConsole 右侧加了时间线、两层排序（按 DDL / 按重要性）、大项目折叠、手动改状态（config 已加 `roadmap_mark`）；自动完成走 `dispatch --roadmap`、review、PR 轮询；remind 每小时发 DDL 提醒（多条合并成一条）和组会提醒（果蝇周四 15–17，Ear 周四 17–19）。用户嫌界面丑，总控按页面原有的黑白红风格重做了时间线和开关，手机宽度修了横向溢出。另：SpeakerLocality 调查完成（~/research/SpeakerLocality，a408d3b），结论是时间局部性不新，Ear 标签断在 chunk 边界是 Ear 每 5 分钟单独跑造成的，不是模型限制。D6（学习时间块出题检验）来自用户 11-17 03:09 的 Ear 口述。遗留：芯动 DDL 是 10-20 甘特表的旧日期，全部过期，等用户和团队对完再改；UGVR A1 11-21 截止仍 💤。 |
| 2026-11-18 | 用户同意把历史任务批量标为已审查：98 个（95 个已完成、3 个 10 月失败的）标完，只剩 1 个运行中。用户让总控定期清理左边栏：新增 `interaction/bin/tidy-sessions`，首次归档 59 个 Codex 会话；Claude app 归档了 16 个（规则见 interaction/README「清理不再用的会话」）；每周日 10:00 由定时任务 prts-tidy-sessions 执行，保存为 Auto 模式。归档都能恢复。 |
| 2026-11-19 | 日报时间线按「主线」合并（pulse 95f6461、a03e099、cefdb76）：每天多一次模型调用，把同一件事的段合成一条主线，切出去的段分成走神 / 穿插 / 短事件；主线簇内间隔 ≤15 分，另一已登记项目的正事不能当走神；计时与「人做了什么」逐字不变，末尾加「走神约 N 分（M 次）」；「学到」在代码里过滤过程描述；任何未登记项目名清为 null（修掉「source」「.codex」），零时长段不进时间线。11-18 用真实模型重跑后再按新规则重渲染，二叶亭四迷那段成为 15:58–16:47 一条。遗留：「日语」没在 projects.toml 登记，现在被清成「不属于项目」，等用户决定是否登记（模型还写过「AIInfra」，登记名是「AIInfra 中转站」，可加别名）。 |
| 2026-11-19 | 「EAR录音执行与反馈」session 送来 11-17 16:28 — 11-19 19:12 的 Ear 整理：对用户的认识写进 yyj.md（易受建议干扰、京都 POST / 出国、下午刷微信要提醒、美股看法只记录、人在回路）；ROADMAP 新增 R25 token 统计与优化（和 11-19 用户要求合并，第 1 步 token-meter 已派），R3 加 AgentConsole 信息结构重组的口述，D7 人在回路（说话人待确认）。AIInfra 的 NewAPI 链路和新前端属于「AIInfra 中转站」工程，不进 PRTS ROADMAP，该工程还没有 human/roadmaps 文件。 |
| 2026-11-19 | token 统计第 1 步上线（PRTS 1ceff81、008c2fd 及总控修正；AgentConsole 679edd7、ed5485c）：`interaction/bin/tokens` 从 `~/.claude/projects` 和 `~/.codex/sessions` 增量记账（首次约 9 秒，之后 0.06 秒），合计 = 非缓存输入 + 缓存写 + 缓存读 + 输出（推理/思考只作明细，官方字段里已含）；Codex 按累计值差分去重，抽查线程与 rollout 的 total_tokens 一致（14,474,344）；Codex resume 追加到原 rollout 文件。实验用 dispatch `--tag` 或 `tokens tag`，均值按 session 算。11-12～19 合计约 Claude 603M、Codex 755M，九成以上是缓存读。事故：Codex 在这个任务里 `git restore` 了 registry.jsonl，丢了约一天的派发记录，已从任务目录补回（backfill 标记），registry 不再进 git（bbd420c）。待做：AgentConsole 的 token 前端（总控写）、每周优化报告。 |
| 2026-11-20 | Ear 迟到转写缺口（「EAR录音执行与反馈」报告）：pulse 62c061e 加入入库水位、`ear sync --since/--until` 补扫、迟到 6 小时以上的 high 不推送、课上演示反例。水位依赖 EchoAsRecord `read_transcripts.py` 输出 `ingested_at`，目前还没输出，所以自动补漏未生效；已请 Ear session 加。总控沙箱外补扫 11-17 16:28–11-18 22:47（11-18 从 2 段补到 32 段，唯一 high 已由 Ear session 处理），重渲染 11-18 日报。registry.jsonl 前次 `git commit <路径>` 把它又加回了 git，已用只提交 index 的方式真正移出。 |
| 2026-11-20 | Ear 入库水位生效：Ear session 给 `read_transcripts.py` 加了 `ingested_at`（该脚本在 EchoAsRecord 仍是未跟踪文件）。pulse 回扫限定为最近 `late_scan_days=7` 天，每轮 sync 约 72 秒（原 24 小时回看约 22 秒），之后不再随数据增长。 |
| 2026-11-20 | 自动任务盘点（用户问哪些是自动的）。修夜间备份：~/.codex/memories 的 git 对象只读，copy2 覆盖报权限错，连续 7 晚中断；改为先删旧副本、单文件失败不中断（AgentConsole 已推送），手动跑通 709 个文件。停掉 11-13 的 `com.prts.ear-sender-test-20261113`（plist 移到废纸篓，测试数据目录 EarIngest/test-20261113-1342 保留）。 |
