已提交：`3d81008`（当前分支 `main`）。工作区干净，未推送、未重启 launchd。

修改文件：
- `agent_console/scan.py`：读取 app 元数据、折叠旧 transcript、应用标题与归档状态。
- `agent_console/server.py`：排除归档及折叠行的计数和提醒。
- `agent_console/static/index.html`：增加“显示已归档”开关。
- `tests/test_claude.py`：5 项 unittest 全部通过。
- `README.md`：更新标题、折叠、归档及测试说明。

本机核验（以下状态均为 `dormant`）：

| id | 标题变化 | parent 前 → 后 |
|---|---|---|
| `92dde3e1` | PRTS 项目尝试 → 加旧 transcript 标注 | 无 → `91be3537` |
| `269e2735` | 首条指令 → PRTS 项目尝试 | `92dde3e1` → 无 |
| `6a7f9f82` | 原标题保留，归档隐藏 | `92dde3e1` → 无 |
| `4a01904f` | 原标题保留，归档隐藏 | `92dde3e1` → 无 |
| `106ff1bd` | 旧分支标注 → 旧 transcript 标注 | `b1c28ceb` → 同前 |

[完整前后 Claude 行清单（id、标题、状态、parent）](/tmp/agentconsole-claude-verification.md)

未发现其他重复的顶层 app 会话。最终计数：working **1**、open **0**、dormant **11**。前端逻辑检查及 `git diff --check` 通过。沿用 `parent`、`fork_of`，新增 `app_session_id`，未引入重复概念。