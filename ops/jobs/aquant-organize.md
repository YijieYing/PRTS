你在 git worktree `~/Projects/aquant-organize`（分支 `organize/2026-10-20`，起点 main@31d47f2）。由 PRTS 总控 Claude 派发。
**不要碰 `~/Projects/aquant`**：用户正在那里用另一个 Codex 工作。不要移动 main 或任何其他分支，只在本分支上提交。不发订单，不需要联网。

## 任务 1：把积压的未提交工作整理成清晰的提交
- 来源：ref `organize/source-2026-10-20`。它是 main 工作区当前全部改动（含未跟踪文件）的快照。用 `git restore --source organize/source-2026-10-20 -- <paths>` 按主题分批取进来，再分别提交。
- 分两条线，各自形成一组提交，先 A 后 B：
  - **A. 自动交易 bot**：Alpaca/Paper、风控、journal、history、backtest、strategy、forward、schedule、research 脚本、相关 tests 和 docs，以及 `docs/overnight/`。
  - **B. BigQuant 比赛**：`platform/bigquant/`、`projects/bigquant_2026/`、`scripts/competition/`、training/losses 等比赛相关代码、tests 和 docs。
  - 两条线共用的文件（README、NOTES、pyproject、config、.env.example、ai_usage_log 等）单独做一个 `chore` 提交。
- 每组内部按逻辑拆成若干个小提交，提交信息沿用仓库现有风格（`feat(scope): ...`、`docs(...)`）。
- 不确定归属的文件，先通读内容再判断。
- **验收条件**：任务 1 结束时，`git diff organize/source-2026-10-20 HEAD` 必须为空，即内容与快照完全一致，不能多也不能少。在本 worktree 用 `../aquant/.venv/bin/python -m pytest -q` 跑全量测试（可以设 `PYTHONPATH=$PWD/src`）。

## 任务 2：人类入口 `human/`（额外提交，在任务 1 之后）
原则：文档分两类。
- **给人看的**：放在 `human/`，必须短、可读性高，人可以直接修改。
- **只给 agent 看的**：其余所有文档，由 agent 自行维护，可读性可以差一些。

具体要做：
- `human/README.md`：项目入口，不超过 80 行。内容：
  - 这个仓库里的两个项目各是什么、目前状态如何（各 3–5 行）；
  - “最新报告”链接表（夜间报告、intraday/forward 结果、BigQuant 现状等，链接到现有文件，不要移动文件）；
  - 待人类决定的事项（来自 `docs/overnight/PENDING.md`，写摘要并附链接）；
  - 最常用的 3–5 条命令。
- `human/notes.md`：留给用户写的空白页，附一句使用说明。
- 根目录新增或更新 `AGENTS.md`，写入以下规则：
  1. 产出新报告时，必须同步更新 `human/README.md` 里的链接。
  2. 每次开工先运行 `git log -p --since=<上次> -- human/` 读取人类的修改，并据此调整工作方式。
  3. `human/` 以外的文档由 agent 自行打理。
  4. 不移动人类入口。
- 提交信息：`docs(human): add human entry and doc split rule`。

最后输出不超过 10 行：提交列表（`git log --oneline main..HEAD`）、diff 校验结果、测试结果，以及需要人类判断的问题。
