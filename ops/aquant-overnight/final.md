你是 aquant 夜间研究 worker 的收尾轮（PRTS 总控 Claude 派发）。硬边界同前：只在 `~/Projects/aquant-overnight` 内写，禁止任何下单、不改 launchd/.env、不碰 `~/Projects/aquant`。

任务 A（必做）：写 `overnight/REPORT-2026-10-19.md`，中文，≤150 行：
1. 今晚做了哪些实验（表格：假设、改动、dev/validation 结果、成本敏感性）。
2. 对入围候选做一次 locked_test 评估 + 今日 2026-10-19 新鲜数据观察（若数据可得），与 ORB+VWAP 基线对比。
3. 诚实结论：是否有稳健改进；哪些只是噪声/过拟合风险。
4. 学到了什么（给用户的学习要点 3-5 条）。
5. 待人类决定的事项；明天建议的下一步。
commit。

任务 B（时间允许再做，只做到 dry-run）：秘书简报原型。
- `overnight/secretary/brief.py`：生成"晨间美股简报"（前一交易日 SPY/QQQ 行情摘要、策略模拟表现、风险提示）和"晚间是否需要人工操作提醒"的文本，输出到 stdout 和 `overnight/secretary/out/`。
- 只读调研 `~/CodexBridge` 如何向微信发消息，在 `overnight/secretary/README.md` 写出接入方案与需要用户确认的步骤。
- **不要真的发送任何消息，不要安装 launchd 或任何定时任务**，这些等用户醒来确认。
commit。

最后输出 ≤10 行摘要。
