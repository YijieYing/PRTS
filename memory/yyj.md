# yyj — Claude 对用户的了解

> 由 Claude 维护，记录我对你的了解，你随时可以纠正。最近更新：2026-10-18。
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
- `~/Projects/`：octopus、codexbridge、aquant、AIInfra、DigitalFly、XinDong、ToiletGame、scala-starter，以及冻结的 Chronos/Tanngo/octopus_ModelTest。
- `~/Projects/ledger`：记账工具，账本在 `human/账本.xlsx`。
- `~/CodexBridge`、`~/codexbridge-secretary`：微信侧轻量秘书。
- `~/research/LearnCodex`、`~/research/Obsidian_Note`。
- `~/school`、`~/outreach`。

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
