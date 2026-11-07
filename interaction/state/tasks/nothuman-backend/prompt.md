你要实现网页游戏 NOT HUMAN 的**整个后端**（Scala 3）。仓库：/Users/prts/school/26秋速通作业/类型安全/NotHuman

## 先完整阅读
1. `AGENTS.md`：硬约束（5 个微服务的边界、functions 纯函数、随机只用 Rng、SQL 只在本服务 tables 等）。
2. `docs/architecture.md`：**这是规格**。第 3–10 节逐个列出了要实现的包、文件、类型、函数签名、表结构、API 流程、tick 顺序；第 12 节是测试清单。
3. `docs/scenario-format.md`：剧本 YAML 格式（解码器要按它实现）。
4. `docs/api.md`：公开 API 的名字、字段、错误码。
5. `docs/game-design.md`：指标含义和数值规则。
6. 课程参考（只读，不要复制业务代码）：`../sample/backend-sample/src/main/scala`，看 api/objects/routes/tables 的组织方式。

## 现状
- 旧版游戏代码已删除。留下的 `src/main/scala/nothuman/system/` 6 个文件是旧的基础设施，还引用着已删除的 `nothuman.shared.objects.GameError`，按 architecture.md 第 3 节改造（`AppError`、`CallMessage`、`StagedAPIMessage`、`Clock`、`Secrets`、`LlmClient` 等）。
- `build.sbt` 已加好 `circe-yaml 1.15.0` 和 `http4s-ember-client 0.23.30`，依赖已缓存。不要再加别的依赖；确实需要时在报告里说明理由。
- 剧本已经写好：`src/main/resources/scenario/`（13 个纪元、253 个事件、22 个结局），已经过格式和引用检查。**不要修改这些 YAML 文件。** 如果你的校验器报出问题，先确认是不是你的解码器理解错了格式；确实是剧本问题的，列在报告里。单元测试用的小剧本放在 `src/test/resources/` 下自己写。
- 前端不在本次范围，不要动 `frontend/`。

## 要求
- 按 architecture.md 第 13 节的顺序做：先 scenario（类型、解码、校验）+ run/functions（引擎）+ 模拟机器人测试，再 system 改造 + verify / judge / report / run 的表和 API + Main / ApiRouter + 集成测试。
- YAML 里的枚举值是 snake_case（`public_trust`、`era_change`、`gpu_price`），Scala 里是对应的 enum case。
- 数值规则（Growth 的能力增长、资源消耗、WorldTick 的漂移和冲击）文档只给了方向，具体公式你来定，要简单、可解释，并把公式写进 `docs/game-design.md` 第 3 节"数值规则"。
- 规格有歧义或签名需要调整时，选最简单且符合 AGENTS.md 约束的做法，并**在同一次改动里更新 `docs/architecture.md`（和 `docs/api.md`，如果涉及）**，在报告里逐条列出改了什么。
- 测试不调用真实 LLM（用 `LlmClient.stub` / `offline`）。
- 模拟机器人：随机种子 + 随机回答连跑 10000 局；如果超过 60 秒就降到 2000 局并在报告里说明。测试日志里输出结局分布、平均每局题数、每局平均回合数、从未触发过的事件。所有局必须在 maxTurns 内正常结束、不抛异常。
- 不要 git commit、不要切分支、不要 git add。

## 完成标准（全部运行并如实报告结果，包括失败项）
```
sbt compile test scalafmtCheckAll scalafmtSbtCheck
python3 scripts/check-architecture.py
```
另外实际启动一次 `sbt run`（没有 TOKENHUB_API_KEY，离线判分），用 curl 走一遍：`GET /api/v1/health` → `verify.submit` → `run.start` → 多次 `run.advance` → 回答一道选择题和一道填空题 → 用 `run.autoAnswer` 一直推进到结局 → `report.get` → `report.codex`。在报告里贴关键响应摘要，然后停掉服务。

## 最后输出报告
1. 实现了哪些文件（按服务分组的简表）。
2. 上面所有命令的结果。
3. 模拟机器人的输出：结局分布（每个结局的占比）、平均题数、平均回合数、从未触发的事件列表。
4. 对 docs 的修改清单，以及和规格不一致的地方。
5. 剧本里发现的问题（如果有）。
6. 你认为还不完善、需要下一步处理的地方。
