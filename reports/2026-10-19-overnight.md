# 夜间任务：Claude 如何实现长时间监控和操作

> 2026-10-20 02:59 JST（纽约 10-19 13:59）启动。结果在早上补到文末。

## 架构（第一次用"状态 vs 推理"的总控提案做实验）

```
你（睡觉）
 └─ Claude 总控 session ── 只在事件发生时醒来：派发、抽查、写报告
     ├─ supervisor.sh（确定性 shell，不调用 LLM）── PRTS/ops/aquant-overnight/
     │    ├─ caffeinate -i 防止 Mac 空闲睡眠
     │    ├─ 循环：codex exec 第 N 轮（每轮最多 35 分钟）→ events.log
     │    ├─ 纽约 16:20 前不再开新轮 → 收尾轮写日报
     │    └─ 连续失败 3 次 → 停下并记一条 L2 事件
     │        └─ Codex worker ── 只在 git worktree ~/Projects/aquant-overnight 里干活
     └─ codex exec（记账 MVP）── ~/Projects/ledger
```

- **为什么不让 LLM 一直盯着**：轮次调度、超时、停止条件都是确定性的规则，交给 shell 就够了。Claude 只在两个时刻消耗上下文：一个进程结束，或者需要做判断。这对应 prts.md 里说的“24h ≠ 持续推理”。
- **为什么要用 worktree**：你那个 Codex 正在 `~/Projects/aquant` 做前向观察，工作区里还有未提交的改动。夜间 worker 只能写自己的分支 `overnight/2026-10-19`，行情数据只读复用。这是先前提案里“单一写者”原则的落地。
- **安全边界**：禁止任何下单（包括 Paper），不改 launchd 和 `.env`，行情 API 只允许 GET。秘书部分只做到 dry-run：不发微信，也不装定时任务。
- **“帮你按 Enter”的问题**：`codex exec` 是非交互模式，不会弹出审批，所以不需要按 Enter。你自己开的那个交互式 Codex，我没有办法向它的终端输入，也没有去碰它。

## 已知风险
- Mac 现在用电池（100%）。合盖仍然会睡眠，`caffeinate -i` 只能阻止空闲睡眠。**今晚不要合盖。**
- 美股 16:00 ET（东京 05:00）收盘，所以盘中时间只剩大约 2 小时。之后的研究都基于历史数据。
- 如果 Claude desktop 关闭：supervisor 是用 nohup 启动的，会继续跑完；只是我的验收要等到下次会话再做。
- `~/Projects/aquant` 里那 12 个未提交的改动，不在 worktree 基线中。
