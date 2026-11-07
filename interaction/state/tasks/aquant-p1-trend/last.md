已实现并提交 4 个逻辑提交，工作树干净，未推送。详见[结果报告](/Users/prts/Projects/aquant/.worktrees/multiday/human/p1-trend-2026-10-21.md)。

- **TSMOM、SMA10：DEFENSIVE_ONLY；XSMOM、DUAL：REJECTED。无晋级候选。**仅 SMA10 达到防守型手工考虑门槛，回撤减少 61.81%。
- **745 passed、4 skipped**，含 38 项 P1 测试；Ruff 通过，48 个场景独立账本核验通过。
- 27 ETF 实际覆盖 2016-01-04～2026-10-20；2015 未返回。French 到 2026-08。
- 冻结 SHA256 未变。全部结果及修正前输出已保留；主要偏差包括日历代理、全局 DSR 方差缺失、episode bootstrap 限制和 French CAGR 修正。
- 前向代码已登记，未运行、未调度、未下单。

**Claude 待决定：**[Alpaca Calendar](https://docs.alpaca.markets/us/v1.1/reference/getcalendar-1) 属于被禁止的 Trading API，因此尚未完成该项校验。需允许仅只读 Calendar，或提供获准取得的离线日历；当前历史判定基于明确标注的 XNYS 代理，前向运行保持阻塞。