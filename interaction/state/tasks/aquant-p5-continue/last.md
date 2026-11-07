P5 已完成，提交：`57e08c7`、`969bf78`，均含指定 trailer。

HSBC BASE 全期结果：

|规则|判定|净收益|超额 Sharpe|
|---|---|---:|---:|
|DISP_H2_C1|WEAK|+11.51%|0.0036|
|REV5_H2_C1|REJECTED|−8.15%|−0.0051|
|LOGIT_H2_C1|WEAK|+10.15%|0.1532|

没有规则通过手工试验门槛。平均预留分别为 **$3.503 / $3.538 / $3.551**；LOGIT 全期佣金 **$2,502**，最大回撤 **$2,604**。

验证：**1210 passed，4 skipped**；52 项 P5 测试，Ruff 通过，88 个组合重复重放一致。账本恰好追加三行，**N=129**；保护文件未变，大明细未入 git，工作区干净。

[完整中文报告](/Users/prts/Projects/aquant/.worktrees/multiday/human/p5-concentrated-2026-10-24.md)