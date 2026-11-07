已提交 `74d2a14`，工作区干净；[REPORT.md](/Users/prts/research/PRTS/results/phaseA/REPORT.md) 已更新。
- 30 项测试通过；全程离线、仅标准库。
- 覆盖 Codex 141/141 thread、Claude 7 个 session。
- unknown：76.05% → **23.54%**，达到验收线。
- 文件页显式重复 **823 次**，刷新 **283 次**；同页重用距离 P50=32,856、P90=321,605 token。
- 细网格检出 FIFO、LRU 各 **2 对**缺页反常，均伴随超窗页数下降。
- 已提供 v1／v2同样本／v2全量并列表及逐文件分布；混合输出均分、未知脚本等局限仍限制策略结论。