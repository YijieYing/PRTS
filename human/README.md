# PRTS 总控台：人类入口

这里是给你看的。其他目录归 agent 打理。你可以直接改这个目录下的任何文件，我下次开工时会读取改动（git diff）。

## 现在
- 总控台（Claude）负责：派发 Codex、抽查验收、记录。具体执行交给 Codex。
- 已完成：aquant 积压改动整理提交并合并到 main；agent-tree supervisor 常驻运行。
- 已完成：记账第一次真实导入，账本在 `~/Projects/ledger/human/账本.xlsx`；Codex 压缩算法源码调研。

## 报告
| 日期 | 报告 |
|---|---|
| 2026-10-20 | [把上下文当作内存：压缩 = 页面置换？](reports/2026-10-20-context-paging.md) |
| 2026-10-19 | [夜间 aquant 与记账](reports/2026-10-19-overnight.md) |

## 各项目的人类入口
- aquant：`~/Projects/aquant/human/README.md`
- 全机 agent 监视：http://127.0.0.1:7788（`~/Projects/agent-tree/human/README.md`，私有仓库 github.com/YijieYing/agent-tree）
- 待你过目的事件：[inbox.md](inbox.md)
- 记账：`~/Projects/ledger/human/README.md`，账本 `~/Projects/ledger/human/账本.xlsx`

## 给我留言
写在 [notes.md](notes.md) 里。
