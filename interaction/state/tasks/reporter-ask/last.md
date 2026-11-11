已完成并分两次提交：

- `c7139d8`：实现与文档。
- `647f455`：隔离测试。

文件：`reporter/bin/ask`、`lib/questions.py`、`config/questions.toml`、`tests/test_questions.py`、`.gitignore`，并更新 [reporter/README.md](/Users/prts/PRTS/reporter/README.md)。

接口覆盖全部要求，另提供 `opened`、`default-used`、`default-ok`。沿用 `questions` 命名，无旧名称迁移。默认每批 3 条、blocking 每日最多 6 批、间隔 30 分钟、soon 18:00 汇总。

**验证过：**

- `python3 -m unittest discover -s reporter/tests -v` → `Ran 10 tests … OK`
- `python3 interaction/tests/test_modules.py` → `Ran 10 tests … OK`
- `git diff --check` 通过；事件流和锁文件被忽略，reporter 工作区干净。

**试跑范围：**仅临时目录与替身 pulse；未试跑真实 Claude 定时任务或手机展示。未修改禁止路径，未提交 state 数据。