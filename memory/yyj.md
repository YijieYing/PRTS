# yyj — Claude 对用户的了解

> 由 Claude 维护，记录我对你的了解，你随时可以纠正。最近更新：2026-10-22。
> 原始版本（你手写的 7 个方向 + GPT 的工程建议）保存在 git 历史 `81ea0f0` 中。

## 1. 基本情况

- 清华本科，2026 秋季是大三上学期（目录 `Undergrad_3_Autumn`），正在上操作系统课（rCore-Tutorial-v3，Rust）。
- 同时学习类型系统，之后打算学形式化方法、信息论。
- 主要 AI 搭档：**GPT** 负责学术讨论和研究问题定义；**Claude（这里）**负责工程实现和具体问题；**Codex** 负责具体编程执行。

## 2. 和 Claude 合作的约定

- `~/PRTS/` 是总控台（Claude）的工作区，用 git 管理。结构见 `memory/INDEX.md`：`human/` 是给人看的入口，`memory/` 是 agent 的记忆分区。
  - `memory/prts.md`：PRTS 背景与**工作进度**（PRTS 是七个方向之一）。
  - `memory/yyj.md`：本文件，记录对你的了解。
  - 这两个文件都由 Claude 全权维护。
- **Human_Work** 在 Apple 备忘录里，由你**手工维护**，用来记录七个方向的进展。Claude 需要时可以申请只读权限。这是我们划分 human/agent 工作边界的一次尝试。
- 研究 Codex 时直接读开源的 Codex，不使用泄露的 Claude Code 代码。
- **文档分两类**（2026-10-20 你提出）：给人看的放在 `human/`，必须可读，你可以直接修改；其余文档由 agent 自己打理。你会看着 agent 给的路径去找报告，所以每个项目都要有一个人类入口。
- **放置规则**：属于 PRTS 总控台的组件（supervisor/AgentConsole、派发脚本、记忆）放在 `~/PRTS` 下；普通项目放在 `~/Projects`。
- **语言偏好**（2026-10-22）：中文 > 英文 > 日文 > 法文。默认用中文；资料或界面需要选语言时，按这个顺序选。
- **有效时间 = 输入 + 输出**（2026-11-12）：你希望有效大脑时间主要花在学习（输入）和创造（输出）上；工程杂务尽量交给 agent，包括和 agent 讨论架构。11-11 回顾时你发现一天里想不起学了什么、产出了什么，感觉都在和 agent 解决琐碎的工程问题。这是 `pulse` 的起点。定义见 `~/PRTS/pulse/README.md`。
- 你喜欢简洁易懂的报告，例如 overnight report 那种格式：先给结论，再列证据和待决定事项。
- 你在意上下文/token 的消耗（2026-10-18 第一次会话同步完就用掉了 9% 上下文）。所以：
  - 不整篇重读大文件，按需读取局部。
  - 文件写得精炼。

- GitHub 账号：**YijieYing**。配置远端时用它；公开发布前要先问。
- 你在学 OS 的页面置换算法（2026-10-20），会把课程内容和 PRTS 联系起来思考。

## 3. 开发环境

| 机器 | 说明 |
|---|---|
| **Mac**（本机） | Apple M5，24GB 内存，macOS 26.4，用户名 `prts`。Claude Code / Codex 跑在这里。 |
| **lain**（Dell，远程服务器） | `ssh lain` → `yijieying@lain-linux`。Ubuntu 22.04，16 核，15GB 内存，RTX 4050 Laptop GPU（6GB 显存），根分区 317G（已用 83%，剩约 53G）。24h 插电运行。 |
| ⚠️ lain 注意 | 笔记本合盖运行，但 logind 的合盖挂起没有关掉，导致 auth.log 被刷屏；2026-10-18 已修复（logind 改为合盖忽略，配置在 /etc/systemd/logind.conf.d/90-lid-ignore.conf）。 |
| ⚠️ lain 发热源（2026-10-20） | Clash Verge 的 GUI 内嵌网页进程（WebKitWebProcess，父进程 clash-verge）持续占用约 12% CPU，已累计 21 小时 CPU 时间。AgentConsole 在 lain 上每分钟只用约 0.05 秒。 |
| 第三台服务器 | 还没搭好。 |
| 云端 VM | prts.md 中提到过，具体情况未知。 |

lain 上目前有：
- OS 课仓库：`~/Undergrad_3_Autumn/OS/rCore-Tutorial-v3`，以及 `~/qemu-7.0.0`。
- `~/projects/`：octopus、moss-transcribe-diarize、HCI_essays、claude_test。
- `~/repos/aquant`。
- `octopus-data`、`aquant-data`、`models`、`datasets`、`services`、`robomaster`。

Mac 上目前有：
- `~/research/`：PRTS（研究层）、DigitalFly（2026-10-25 从 ~/Projects 移来；旧路径留了符号链接）、Ear（设计文档）、alignment、LearnCodex、Obsidian_Note。
- `~/Projects/`：octopus、CodexBridge、aquant、AIInfra、XinDong、NatureCalls、SwarmBot、ledger、deepseek_face，以及冻结的 Chronos/Tanngo/octopus_ModelTest（10-27 核对时已没有 ToiletGame 目录）。
- `~/Projects/ledger`：记账工具，账本在 `human/账本.xlsx`。
- `~/Projects/CodexBridge/`：微信侧轻量秘书。`app/` 是源码兼运行中的部署（launchd com.ganxing.codexbridge-weixin），`secretary/` 是 bot 的 Codex 工作目录（不能放进 app/，否则会读到工程的 AGENTS.md）。运行状态在 `~/.codexbridge`。2026-10-27 从 ~/CodexBridge、~/codexbridge-secretary 迁来（旧路径留了符号链接），多余的开发副本 ~/Projects/codexbridge 已移到废纸篓。
- Scala 课程工程：`~/school/26秋速通作业/类型安全/scala-starter`（10-27 从 ~/Projects 移入）。
- Unity Hub 模板目录改为 `~/.unity/templates`（原 ~/Unity user templates 是空的，已删）。
- `~/school`、`~/outreach`。

**额度分工（2026-10-27）**：Codex 额度充足，Claude 额度紧张。Claude 只做决策和思考（定方案、审查、验收）；写代码、写测试、跑测试等执行工作交给 Codex（`~/PRTS/interaction/bin/dispatch`），除非直接做明显比写任务说明更省 Claude 的 token。

## 4. 七个长期方向

目标分三级：1 = 只要求结果实现；2 = 学习已有内核并复现；3 = 探索人类知识空白。
你的总体动机："做现在还做不到的、少有人在做的事情"。

1. **PRTS**（1）。在实现过程中理解 Codex（2）、学习 RSI（2）。
   - 想搞清楚多 agent 的上下文管理、多个 agent 同时施工同一工程的原理、Codex app 怎么识别中转站、CLI 之间能否由 app 同步上下文。
   - 人机交互原则：凡是涉及非直接目的的"设计中间过程"，先考虑让 agent 实现。
   - 详见 `prts.md`。
2. **OS / 分布式系统**（2）。掌控 agent 调度需要深刻理解前人如何做 CPU 调度。
3. **Agent 决策移交给小模型**（2、3）。在算力和存储充足时，为常见、重复的本地任务训练小模型，当作 cache 用，地位等同于"写个软件"。这件事涉及硬件和真正的操作系统优化。
4. **多机器人系统 / SwarmBot**（2、3）。可能需要学 ROS。本质上是放到硬件上的多 agent + ambient 调度。愿景是一群小机器人上学时组成各种形态跟着你跑。还想调研一下：为什么具身智能这么热，这一块却很少有人提。
5. **果蝇脑 / NeuroScience**（3）。作为非 transformer 架构的对冲。生物脑的高效可能是端侧/ambient 系统的未来。
6. **RSI**。在 PRTS 这个"agent 大杂烩"里尽可能实现，不去追 benchmark。它是实时 agentic OS 的组成部分。（GPT 的版本把它并进了方向 1。）
7. **语言学 / 信息论 / 类型系统 / 对齐**（2、3）。**保留**（2026-10-18 确认）。核心问题：
   - agent 之间怎么交流最省 token，或者在其他维度（能量、context）上最省。
   - 是否需要使用自然语言。
   - tokenization 有没有更高效的方式。
   - 语言学能否为对齐、安全和可读性提供严格的控制思路。

学术研究线目前有三条：PRTS、SwarmBot、NeuroScience。

### 2026-11-14 下午口述：方向调整（全文见 `human/reports/2026-11-14-下午口述-许愿机与方向.md`）
- 核心判断：RSI 和大模型的终点是「许愿机」，它把想法做出来，但自己不会许愿；它不是智能，而是工程助手。对会用 agent 的人来说，许愿机基本已经成型。
- 由此推出：**不做「让许愿机更好」的事**，包括训练基模、计算优化、agent 架构。不进大公司做这些就会被碾死。PRTS 的 agent 优化「到此为止」，结果交给喻纯，争取经费或发文章；之后只保留真正有用的部分（例：学日语提醒加出题）。
- 「长期且正确」的两件事：Transformer 之外的架构；做正确的具身。科学方向是「基因预训练」：预训练相当于进化和基因组，后训练相当于突触和记忆，身体和机械结构都应该可训练，新范式要他自己提。工程方向是钢铁侠式机甲（他能接触到有能源和力学背景的人，认为更现实）或 SwarmBot。交互硬件（眼镜、戒指）可以放在喻纯那边或 PRTS 下面。
- 学习观：学习的目的是能够许愿，也就是能精准描述现有技术的问题和自己想要什么；不懂再学，不为学而学。什么东西要学、什么不要学，需要一个判断标准（他特别标注了这一点）。果蝇方向缺的是数学建模，不是纯数学。
- 他对 PRTS 的评价（用了两天）：提醒不算好用，日报也就那样；「提升我的效率」可能本身就不是一个可解的目标。
- 这些对 ROADMAP 和七个方向的影响，总控在报告末尾列了出来。**11-15 用户决定：暂不降级任何任务，因为 agent 研发可能还要用于申请，要再评估。**

## 5. 人物

已移到 [people.md](people.md)（2026-11-02 起）：GitHub 账号对照、FlyBrain 组、清华 HCI、课程队友、待问清单。
