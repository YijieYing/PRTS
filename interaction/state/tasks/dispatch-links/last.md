已核验完成。任务所需修改在开工前已分别提交，本轮未重复修改或新增提交：

- PRTS：`6a65831`，涉及 `interaction/lib/codex`、`bin/dispatch`、`bin/resume`、`bin/status`、`tests/test_modules.py`、`README.md`。
- AgentConsole：`c0306b8`，涉及 `agent_console/server.py`、`tests/test_links.py`、`tests/test_claude.py`、`README.md`。

新增 `start.caller`、`thread` 事件和 `status links` JSONL 接口。AgentConsole 通过可选 `links` 命令读取关系，2 秒超时、60 秒缓存，设置 `parent` 和 `spawned_by`。两份模块 README 已说明接口。沿用现有术语，未新增重复概念。

**验证过：**

| 测试命令 | 输出 |
|---|---|
| `python3 interaction/tests/test_modules.py` | `Ran 10 tests … OK` |
| `bash interaction/tests/test_wake.sh` | `PASS: time, past rejection, alias dedup, cancel, dry, delivery, injection, one-shot, capacity` |
| `cd AgentConsole && python3 -m unittest discover -s tests` | `Ran 9 tests … OK` |

测试使用临时目录和替身命令，入口 stdin 关闭。当前环境确实提供 `CODEX_THREAD_ID`。

**试过与未核实：**本轮执行了代码核查和上述测试；未启动真实 Codex、未验证实际 UI 挂载效果。用户配置、launchd、真实 state 及禁止修改的文件均未改动；未回填历史日志。