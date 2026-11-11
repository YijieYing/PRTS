# 任务：④ 删掉自己的 ⑦ HTTP 客户端，改用 ⑦ 提供的 GatewayClient

## 背景

④（`services/extraction`）在 `src/ear_extraction/model_io.py` 里有自己写的 `HttpGateway`，注释说它对接的是「提议中的 ⑦ 端点」，POST Call + system，期待 `{output}`。⑦（`services/llm_gateway`）已经实现，并在 `src/ear_llm_gateway/client.py` 提供 `GatewayClient`，docstring 写明是「④-compatible complete(call)->dict port」，调用真实的 `POST /v1/complete`。两份代码重复，④ 那份和真实 ⑦ 的协议不一定一致。

负责人已同意：④ 依赖 ⑦，删掉 `HttpGateway`，改用 ⑦ 的 `GatewayClient`。⑦ 的客户端暂时**不**移到 `libs/`，④ 直接依赖 workspace 包 `ear-llm-gateway`。

## 要做

1. `services/extraction/pyproject.toml` 加依赖 `ear-llm-gateway`（`[tool.uv.sources]` 里 `workspace = true`），更新 `uv.lock`（`uv lock`）。确认没有形成循环依赖：⑥ `ear_api` 已经导入 `ear_extraction`，⑦ 不能反过来依赖 ④ 或 ⑥。
2. 删除 `model_io.py` 里的 `HttpGateway`。保留 `ModelGateway` Protocol（`complete(call) -> dict`）作为 ④ 的注入端口，测试替身继续用它；`GatewayClient` 应当结构上满足这个 Protocol——用 pyright 验证（例如在测试里把 `GatewayClient` 赋给 `ModelGateway` 类型变量）。
3. ④ 的 `SYSTEM` 提示词要传给 ⑦：用 `GatewayClient(..., system=SYSTEM)`，或在 ④ 构造客户端的地方注明。核对 ④ 的 `Call`（`domain.py`：module/root_feedback_id/depth/run_id/purpose/data/output_schema）和 ⑦ 的 `CallRequest`（`models.py`）字段是否完全兼容；`GatewayClient.complete` 会补 `call_id`、`model`、`system`。若 ④ 的 `run_id` 等字段不满足 ⑦ 的校验（例如 ⑦ 要求 UUIDv7 而 ④ 不是），在报告里写清，并采用最小改动让 ④ 产生合法值；不要放宽 ⑦ 的校验。
4. ⑦ 的语义差异要写进 ④ 的文档：每次 `complete` 生成新的 call_id；传输错误可能已经执行（`gateway_outcome_unknown`），**不能自动换新 id 重试**，可恢复流程要持久化 call_id 并用 `reconcile`。如果 ④ 现有代码有自动重试模型调用的地方，列出来，不要自行改业务流程，只在报告里说明风险。
5. 测试：`services/extraction/tests/test_boundaries.py` 里针对 `HttpGateway` 的测试改为针对 `GatewayClient`（用 `httpx.MockTransport` 通过 `transport=` 参数注入，不连网），覆盖：④ 的 Call 经 `GatewayClient` 发出的请求体通过 ⑦ `CallRequest` 校验且带 ④ 的 SYSTEM；正常返回取 `output`；`record_saved` 缺失或 `output` 非对象时报错。原测试想保护的边界（例如不跟随重定向、输出必须是对象）保留等价断言。
6. 更新文档：`services/extraction/ai-docs/implementation.md`（第 50 行附近关于 `HttpGateway` 的描述等）、`services/extraction/README.md`（若有）、`services/llm_gateway/README.md` / `ai-docs/implementation.md` 中提到「④ 尚未使用」之类的地方。全仓 `grep -rn HttpGateway` 应只剩历史说明或为零。

## 不做

- 不改 ⑦ 的代码（`services/llm_gateway/src`），除非是 ④ 接入暴露的明确 bug——那种情况只在报告里描述，不改。
- 不改 ④ 的业务逻辑和提示词内容。
## 通用要求（三个任务都适用）

- 仓库规则：先读 `AGENTS.md`、`README.md`。不填写或修改 `reviewed-by` / `reviewed-at`。不把凭据、真实录音、GPS、转写写进仓库。
- 只在当前工作目录（一个 git worktree，分支已建好）里改。**不要 commit、不要 push、不要切换分支**；改动留在工作区，由审查方提交。
- 改了行为、接口、命令、配置，就同时更新描述它们的文档（模块 `README.md`、`ai-docs/`、会变错的注释）；收尾前在仓库里搜一遍旧名称，改掉过时引用。
- 交付前运行完整检查，并在报告里贴出每一项的结果（通过数 / 失败输出）：
  `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest && uv run python tools/check_docs.py`
- 报告（last.md）用中文，写清：改了哪些文件、为什么这样改、测试结果、没做或做不到的事、发现的文档/契约/代码冲突。不确定的地方如实写，不要猜测成已完成。
