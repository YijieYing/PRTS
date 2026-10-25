已提交 `3f0dcba`，含指定 Co-Authored-By trailer。

判定：**KEEP_ACCUMULATING**。REV5_H1、IBS_H2、OVERNIGHT 按规则分为 **EXECUTION_DEPENDENT**。

|规则|盈亏平衡 bp/边|
|---|---:|
|REV5_H1|2.26|
|REV5_H2|5.60|
|IBS_H1|3.96|
|IBS_H2|4.01|
|OVERNIGHT|1.67|
|LOGIT_H1|3.02|
|LOGIT_H2|7.12|

含卖出 SEC 费；所有搜索区间均满足 0.1 bp 容差。

- 56 组旧指标及每日账本精确复现。
- 196 项结果完成，账本仅追加一条诊断。
- **951 passed、4 skipped**；Ruff 全部通过。
- 冻结文件未改，LOGIT 未重训。

[完整报告](/Users/prts/Projects/aquant/.worktrees/multiday/outputs/research/p3-sensitivity/report.md) · [中文摘要](/Users/prts/Projects/aquant/.worktrees/multiday/human/p3-costs-2026-10-21.md)