# ops/（过渡期）

2026-11-07 起，这里只剩指向新位置的链接，让还写着旧路径的 prompt、session 和脚本继续能用。约 2026-11-21 搜一遍旧路径的使用，没有了就删掉整个目录。

| 旧路径 | 新位置 |
|---|---|
| `dispatch.sh`、`retry_resume.sh`、`wake.sh` | `interaction/bin/{dispatch,resume,wake}` |
| `jobs/`、`prompts/` | `interaction/state/tasks/`、`interaction/state/prompts/` |
| `registry.jsonl`、`wakes/` | `interaction/state/` |
| `wechat-notify.sh` | `reporter/bin/notify` |
| `backups/` | `maintenance/backups/` |

模块说明见 [../README.md](../README.md) 和 [../GLOSSARY.md](../GLOSSARY.md)。
