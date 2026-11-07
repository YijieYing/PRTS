已完成并提交 `f62e81b`，工作区干净。

|规则|固定标签|BASE 跳过率：全期 / 留出期|最高月成交额 HKD|
|---|---|---:|---:|
|DISP_H2|NOT_FEASIBLE|21.2% / 45.6%|146,540|
|DISP_H5|NOT_FEASIBLE|78.0% / 79.6%|16,891|
|REV5_H2|FEASIBLE_WITH_CHANGES|9.3% / 29.1%|260,667|
|LOGIT_H2|FEASIBLE|29.2% / 55.0%|205,974|
|IBS_H1|NOT_FEASIBLE|54.1% / 73.8%|68,090|

最高成交额取全部成本与分期。REV5 超限一月，佣金 $90；LOGIT 标签通过，但留出期超过一半信号买不起。

验证：**1158 passed、4 既有 skips**；36 项新增测试，Ruff 通过。冻结文件未变，大账本仅留本地并登记。

[完整报告](/Users/prts/Projects/aquant/.worktrees/multiday/outputs/research/x1-hsbc/report.md) · [中文说明](/Users/prts/Projects/aquant/.worktrees/multiday/human/p4-relative-2026-10-22.md:118)