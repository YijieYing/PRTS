[PRTS 总控夜间指令 · 第 {ROUND} 轮 · 纽约 {NY_TIME}（16:00 收盘）]
用户已经睡觉。本线程由 PRTS 总控（Claude）通过 `codex exec resume` 驱动，**不会有人类回复你**。

总控对目前进展的评估在 `~/PRTS/human/reports/2026-10-21-aquant-ml-assessment.md`，开工前先读一遍（只读）。

按优先级推进：
1. **完成 ML-03**，严格按你手上的指令和 `docs/ml03.json` 执行，不追加参数搜索。M2 如果没有稳定优于 M1，就明确拒绝。
2. **收盘前**（16:00 ET 之前）：用实时数据测量参考 ETF（IWM、XLK、XLF、XLE、SMH）的 IEX 实时覆盖率和到达延迟，判断它们能否作为实时特征。保持 ML-01 实时旁路、Forward 和 Shadow 继续运行。不重启冻结服务。
3. **收盘后**：核对 ML-01 今日提前登记的预测和到期标签，写出 2026-10-20 收盘报告。
4. **最后**：写 `human/decision-2026-10-21.md`，一页纸的方向决策备忘，列出可选方向和各自的证据，供用户醒来决定。**不要自行开启 ML-04。**

硬规则：
- 禁止任何 Paper 或 Live 订单，禁止付费行情，禁止微信推送，不改 launchd 和 `.env`。
- 需要人决定的事写进 `docs/overnight/PENDING.md`，然后改做不依赖它的事。
- 每轮约 25 分钟。在对应的研究分支上小步 commit（`.git` 现在可写），不要提交到 main。进度追加到 `docs/overnight/STATE-2026-10-21.md`。
- 结束时输出不超过 8 行的摘要。全部做完后，回复的第一行写 `ALL DONE`。
