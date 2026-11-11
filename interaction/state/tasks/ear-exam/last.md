已实现 `exam prepare/run/report`，保留原有修改，未改 `codex_runner.py`，未切分支、提交或 push。

- **新增**：`exam.py`、`meter.py`、`isolation.py`、`openai_prices.json`、`docker/Dockerfile`、`.dockerignore`、`tests/test_exam.py`。
- **修改**：`__main__.py`、实验 README、`ai-docs/implementation.md`；根 `pyproject.toml` 排除 local-data 的类型检查和测试发现。未修改审核字段。采用 `exam`、`meter`、`isolation`，没有删除既有名称。
- **原始数据核验未完成**：local-data 内没有 context 原始文件，索引指向范围外 inbox，因此没有读取，不能确认 GPS/手机状态实际字段。已在文档明确留待 Claude 核验。
- **价格已核对**：[OpenAI 官方价格页](https://developers.openai.com/api/docs/pricing.md)，查询日期及估算规则已写入价格表。
- **检查**：实验与根目录 Ruff、格式、Pyright、docs（含 `--base origin/dev`）、diff 检查通过。实验测试 **41 passed、2 skipped**；根测试 **391 passed、2 skipped、1 error**。跳过和错误均因 localhost 绑定被沙箱拒绝；错误来自既有 extraction HTTP 测试。

Claude 仍需实测 Docker 构建/运行、真实材料匹配、容器网络隔离、Colima 防火墙及清理，并补跑两项假上游 HTTP 集成测试。