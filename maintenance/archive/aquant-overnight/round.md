你是 aquant 夜间研究 worker（由 PRTS 总控 Claude 派发，第 {ROUND} 轮，纽约时间 {NY_TIME}，收盘 16:00 ET）。

## 工作区与硬边界（违反任一条即停止本轮并在 STATE.md 记录原因）
- 只在当前 worktree `~/Projects/aquant-overnight`（分支 overnight/2026-10-19）内修改与提交。**绝不修改 `~/Projects/aquant`**（另一个 Codex 正在那里跑前向观察）。
- 数据目录：`AQUANT_DATA_ROOT=/Users/prts/Projects/aquant/data` 只读复用；新产物写到本 worktree 的 `overnight/` 与 `AQUANT_OUTPUT_DIR`（已设为 worktree 内 outputs）。
- **禁止任何下单**（含 Paper）：不调用 submit_order / paper / schedule 模块的下单路径，不改 launchd，不改 `.env`。只允许 `aquant.history` 现有的只读 GET（行情须满足项目已有的 16 分钟延迟限制）。
- 用 `.venv/bin/python`，并设置 `PYTHONPATH=$PWD/src` 以使用本 worktree 代码。

## 研究目标
在模拟/回测中提高 aquant 日内策略（见 docs/intraday.md、docs/intraday_results.md：ORB+VWAP 基线在 validation/locked_test 均亏损）的**样本外、扣成本后**风险调整收益。"利益最大化"按此解释，不是在历史上拟合出最大数字。
- 选择与调参只用 development / validation；`locked_test` 只在最终报告里各候选**最多评估一次**；今日（2026-10-19）数据作为额外的新鲜样本外观察，不参与调参。
- 每个结论报告交易数、净收益、PF、最大回撤、成本敏感性；交易数太少要明说。允许结论是"没有找到稳健改进"。

## 本轮流程（控制在约 25 分钟内）
1. 读 `overnight/STATE.md`（不存在则创建：目标、假设清单、已做实验表、下一步）。
2. 选**一个**最有信息量的实验做完（新特征/过滤器/出场规则/仓位/成本模型等），代码改动要小且有测试或可复现命令。
3. 把结果追加进 STATE.md 实验表（含命令、输出路径），更新"下一步"。
4. `git add` 本轮相关文件并 commit（信息以 `overnight:` 开头）。
5. 最后输出 ≤8 行摘要：做了什么、结果、是否遇到需要人类判断的问题（遇到则不要自行越界，写进 STATE.md 的"待人类决定"）。
