# PRTS memory 索引（agent 用；人类入口在 ../human/README.md）

总控会话开工流程（按顺序，能少读就少读）：
1. 读本文件。
2. 读 `prts.md` 的 §〇（约 60 行），不整篇读。
3. 运行 `git -C ~/PRTS status --short human/ && git -C ~/PRTS diff human/`，查看人类改了什么。读完后用 `git commit -m "human: ..."` 提交，并把从中学到的东西写进对应的记忆文件。
4. 按需读下面的文件。

| 文件 | 内容 | 什么时候读 |
|---|---|---|
| prts.md | PRTS 背景、§〇 进度日志、设计问题池、实验设计 | 每次开工读 §〇；讨论设计时读相应章节 |
| yyj.md | 用户画像：机器、目录、七个方向、合作约定、偏好 | 涉及用户环境或偏好时 |
| [~/research/PRTS/](../../research/PRTS/README.md) | 研究层：实验状态表（README）、E2 设计、E3/E4 笔记 | 讨论研究或实验时先读它的 README |
| ../ops/ | 派发脚本、Codex 任务 prompt（jobs/）、运行日志 | 复用或排查派发 |
| ../human/reports/ | 给人看的报告（也是事实记录） | 回顾某次运行 |
| ../ops/backups/claude/ | Claude 对话备份（`ops/backup_claude.sh` 生成）；先看 INDEX.tsv 找会话，再读对应 jsonl | 需要追溯过去 Claude 总控的对话时 |

规则：
- 每个共享文件只有一个写者：memory/ 只由总控写；worker 写在各自的项目里。
- 做决策时现读文件，不依赖对话记忆。
- 检索结果只是线索：引用前要回到原文件确认。
- 等文件多到 grep 找不准时，再考虑 embedding。
- Claude 的自动 memory（~/.claude/projects/-Users-prts/memory/）只保留指向这里的指针，内容以本目录为准。
