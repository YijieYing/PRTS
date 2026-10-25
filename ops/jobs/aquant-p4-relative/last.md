已完成并分三次提交，工作区干净。假设检验：**partially_supported**。

|规则|判定|全期 IC / HAC t|
|---|---|---:|
|DISP_H2|CANDIDATE_FOR_FORWARD|0.0392 / 2.58|
|DISP_H5|WEAK|0.0191 / 1.01|
|RANK_H2|WEAK|0.0015 / 0.16|
|RANK_H5|WEAK|−0.0072 / −0.53|

- 验证：**1007 passed、4 skipped**；Ruff 通过；55 个受保护文件未改；总账追加恰好五行。
- 主要偏差：缓存缺 10-21；截面标准化消除了共同变量及多数交互信息；按 P4 JSON 判定，未额外加入 P2 的 DSR 门槛，全局 DSR 为 N/A。全部解释已记录。
- 前向实现：`53356d3e01d92b49725466033867a3c2618fcbf5`；首会话 **2026-10-23**。未部署、未调度、未运行生产路径。

[中文结果与完整限制](/Users/prts/Projects/aquant/.worktrees/multiday/human/p4-relative-2026-10-22.md)；待 Claude 独立审计。