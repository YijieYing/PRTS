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

## 03:06 JST 改为接管已有 thread（用户提出）
- 发现：用户手开的 Codex（thread `01a1532a`）已经在做第五阶段，也已经做完第四阶段的 159 组实验；而 worktree worker 的起点是旧基线，等于重复劳动。这是一次真实发生的“多 agent 信息不同步”。
- 处理：
  1. 停掉 worktree worker。它在分支 `overnight/2026-10-19` 上留下 1 个 commit，已作废。
  2. 新增 `supervisor-resume.sh`。它等 TUI 这一轮出现 `task_complete` 后，用 SIGTERM 结束 TUI，然后按轮执行 `codex exec resume 01a1532a…`，全程沿用同一个 thread 的上下文。
  3. worker 的改动提交到分支 `overnight/phase5-2026-10-19`。日报写在 `docs/overnight/REPORT-2026-10-19.md`。
- 教训：派发新 worker 前，应该先查同一目录下有没有正在运行的 agent，以及它在做什么。这是“话题路由 / 总控登记表”要解决的问题。

## 记账 MVP 验收（Claude 亲自运行）
- Codex 在 `~/Projects/ledger` 提交了 4 次。Claude 复跑 `unittest`：25 项全部通过。
- 端到端冒烟测试：同一份 fixture 导入两次，结果分别是 inserted 7 和 duplicates 7，确认幂等。`list` 中的字段完整：reason 为空、reimbursable 为未知、invoice_status 和 invoice_path 都在。
- 隐私：`inbox/`、`invoices/`、`*.db`、`rules.toml` 都被 `.gitignore` 排除，真实账单不会进 git。
- **还没验证**：真实微信导出文件的兼容性。需要你先导出一次，放进 `inbox/`。
