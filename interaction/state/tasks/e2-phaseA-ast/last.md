已提交 `7e43758`，完成 C7 AST 确定性补全。
unknown：23.54% → 23.33%；新增静态读取 588 次、写入 21 次。
新增操作标记 `source=ast`，当前脚本另标 `ast_from_current_file`。
[报告](/Users/prts/research/PRTS/results/phaseA/REPORT.md:54)已包含两组缺页表、剩余 unknown 分类和错误计数。
46 项测试通过；冻结复放的 15 个汇总产物逐字节一致。
全程离线、仅标准库、按文件路径暂存；无关 `.DS_Store` 未提交。