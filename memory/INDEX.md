# PRTS memory 索引（agent 用；人类入口在 ../human/README.md）

总控会话：「PRTS 项目会话整理与迁移」(`local_74ec9ace-4f49-48da-b1c2-b88899178758`，2026-10-25 起)。旧的「PRTS 项目尝试」(`local_0d4ca8f6…`) 已改为 ~/research/PRTS 专用研究会话，不再写 memory/。

总控会话开工流程（按顺序，能少读就少读）：
1. 读本文件。
2. 检查 PRTS 和 research/PRTS 有没有未推送的提交（`git -C <repo> rev-list --count @{u}..HEAD`）；有积压就在回复里提醒用户（用户 2026-10-21 要求：不自动推送，但要适时提醒）。
3. 读 `prts.md` 的 §〇（约 60 行），不整篇读。
4. 运行 `git -C ~/PRTS status --short human/ && git -C ~/PRTS diff human/`，查看人类改了什么。读完后用 `git commit -m "human: ..."` 提交，并把从中学到的东西写进对应的记忆文件。
5. 按需读下面的文件。
6. 每周一次左右（或用户提到合作者时）：扫各仓库近 30 天的提交者（`git log --since=30.days --format='%an|%ae'`），和 `people.md` 的对照表比较；陌生账号提交数 ≥ 3 时，加进 people.md 的「待问」，在合适时问用户。

| 文件 | 内容 | 什么时候读 |
|---|---|---|
| prts.md | PRTS 背景、§〇 进度日志、设计问题池、实验设计 | 每次开工读 §〇；讨论设计时读相应章节 |
| yyj.md | 用户画像：机器、目录、七个方向、合作约定、偏好 | 涉及用户环境或偏好时 |
| people.md | 用户身边的人：GitHub/邮箱对照、各人 profile、待问清单 | 用户提到某人、仓库或对话里出现陌生人时 |
| [~/research/PRTS/](../../research/PRTS/README.md) | 研究层：实验状态表（README）、E2 设计、E3/E4 笔记 | 讨论研究或实验时先读它的 README |
| ../README.md、../GLOSSARY.md | PRTS 的模块（interaction、reporter、maintenance）和名词 | 改 PRTS 工具前 |
| ../interaction/state/tasks/ | 每个 Codex 任务的 prompt.md 和 last.md | 复用或排查派发 |
| ../human/reports/ | 给人看的报告（也是事实记录） | 回顾某次运行 |
| ../maintenance/backups/claude/ | Claude 对话备份（AgentConsole backup 插件生成）；先看 INDEX.tsv 找会话，再读对应 jsonl | 需要追溯过去 Claude 总控的对话时 |

规则：
- 每个共享文件只有一个写者：memory/ 只由总控写；worker 写在各自的项目里。
- 做决策时现读文件，不依赖对话记忆。
- 检索结果只是线索：引用前要回到原文件确认。
- **检索顺序（2026-10-28 事故后）**：用户提到人、话题或以前的讨论，而本目录里没有时：
  1. 先用 `search_session_transcripts` 搜所有 session 的对话。
  2. 再 grep 文件；对话备份在 `maintenance/backups/claude/`，可能比实时对话旧。
  3. 多条命中时，读最新的那条。
  - 事故经过：10-28 用户提到胡瑞，总控只搜了文件，停在 10-15 的 PPT 上，漏掉了 DigitalFly session「果蝇主动决策模型可行性评估」10-23 和用户的讨论。
- 等文件多到 grep 找不准时，再考虑 embedding。
- Claude 的自动 memory（~/.claude/projects/-Users-prts/memory/）只保留指向这里的指针，内容以本目录为准。
