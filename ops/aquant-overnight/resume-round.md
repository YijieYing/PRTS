[PRTS 总控夜间指令 · 第 {ROUND} 轮 · 纽约 {NY_TIME}，16:00 收盘]
用户已经去睡觉。从现在起，本线程由 PRTS 总控（Claude）通过 `codex exec resume` 驱动，**不会有人类回复你**。

规则：
- 继续推进你手上的第五阶段：只读前向验证，以及策略研究与优化。目标是样本外、扣成本后的风险调整收益；不要拿 locked_test 调参。
- **不发送任何订单，包括 Paper**；不改 launchd 和 `.env`。
- 遇到需要人类判断的事，写进 `docs/overnight/PENDING.md`，然后改做不依赖这个判断的工作。
- 第 1 轮先执行 `git switch -c overnight/phase5-2026-10-19`，保留当前未提交的改动。之后每轮结束前，把本轮改动用小步 commit 提交到这个分支，不要提交到 main。
- 每轮控制在约 25 分钟。把进度追加到 `docs/overnight/STATE.md`，包括做了什么、结果数字、产物路径、下一步。
- 结束时输出不超过 8 行的摘要。
