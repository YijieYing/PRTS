已提交 `e1af9ae`，工作区干净；全程离线，未调用 LLM/API。
测试：15 项通过，冻结数据重跑结果一致。
规模：39 个 session，9,519 次引用，约 574 万近似 token。
发现①：仅 26 次重复引用，其中 11 次为空输出，策略排名证据不足。
发现②：FIFO/LRU 在细网格中均未出现缺页反常。
发现③：16k 下 FIFO/LRU 各缺页 8 次，CODEX/CC 各 11 次，OPT 为 0。
局限：unknown 76.05%；固定引用串、摘要按上界、bytes/4 估算；不等大小页的 Belady 不保证最优。
[中文报告与阶段 B 候选](/Users/prts/research/PRTS/results/phaseA/REPORT.md)。