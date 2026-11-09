# 任务：NOT HUMAN 第二版后端（design-v2 第 9 节第 2 步）

工作目录：`/Users/prts/school/26秋速通作业/类型安全/NotHuman`（Scala 3 + http4s + SQLite 后端，React 前端）。

把后端从第一版（一条时间线 + 选择题 / 填空题 + LLM 判分）改成第二版（多个人类同时发消息、草稿卡、温度自动回复、人格光谱、版本发布与 RLHF 训练）。前端由另一边在同时写，你**只改后端**。

## 先读（按顺序，全部读完再动手）

1. `AGENTS.md`：项目硬约束。第 2、3、6 节必须遵守（5 个服务、六个目录、`functions/` 纯、随机只走 `Rng`、SQL 只在自己服务的 `tables/`、`-Werror`、scalafmt）。其中 `judge` 服务这次改名为 `persona`，调用方向变为 run → verify / scenario / persona / report，report → scenario。
2. `docs/design-v2.md`：**第二版的设计依据，全部读**。重点：§2（机制和数值）、§3（结局两层 + 组合表）、§5（剧本格式）、§6（代码结构、数据库、API、视图）、§6.5（测试）。
3. `contracts/v2/`：前后端共享的请求 / 响应样例 JSON。**接口以这些样例为准**。前端测试 `frontend/src/objects/contractsV2.test.ts` 已经按它们写好并通过；读一下它，理解每个接口的字段集合。
4. `docs/architecture.md`、`docs/scenario-format.md`、`docs/api.md`：第一版现状。你要把它们改成第二版。
5. 现有代码：`src/main/scala/nothuman/**`、`src/test/**`、`src/main/resources/migrations/001_init.sql`、`scripts/check-architecture.py`。

## 要做的

### A. scenario 服务
- 新的剧本类型：`Persona.scala`（`Side`、`Branch` 9 个分支）、`Conversation.scala`（Conversation、Exchange、Draft（text、lean、heat、effects、reaction 台词、leaves）、Spot、OnWrite、Post）、`combos`（结局组合表）、人物的 `patience.decay` 和 `avatar`、纪元的 `versionYears`。
- `Condition` 增加 `{ persona: machine|human, gte|lte }`、`{ branch: <id>, top: true }`、`{ branch: <id>, gte|lte }`。
- `Trait` 只保留 `capability`、`autonomy`。
- `ScenarioCodecs`、`ScenarioValidator` 改到新格式，校验 §5 末尾的约束（每轮草稿 3–5 条、每条有 lean 和 heat、找茬卡至少 2 个干扰项、引用都存在、组合表引用的结局和分支存在等），所有问题一次列出。
- **剧本目录可配置**：新增环境变量 `NOTHUMAN_SCENARIO_DIR`（文件系统路径）。设置时从这个目录读，不设置时照旧读 classpath 的 `scenario`。

### B. run 服务（引擎在 `functions/`，必须纯）
按 design-v2 §6.1 的文件划分实现：`Version`、`Clock`、`Drafts`、`Sampler`、`PersonaDrift`、`Release`、`Endings`（世界线结局 + 组合表）、`Engine.start` / `Engine.act(state, action): Either[EngineError, Acted]`、`Views`。沿用 `Rng`、`Conditions`、`Effects`、`Growth`、`WorldTick`、`Eras`、`Text`。
- 数值按 design-v2 里的初始值（版本 45 tick、耐心衰减、重新生成 −15、自动回复 lean 权重 2 / 手动 3、每版本衰减 10%、RLHF +8、温度采样公式……）。把这些可调数值集中放在一个地方（例如 manifest 里或一个 `Tuning` 常量对象），不要散落在代码里。
- `atTick` 夹到 `[当前 tick, 版本长度]`，不报错；先 `Clock.advance` 再执行动作。耐心归零的自动回复在 `advance` 里发生。
- `run.release`：把剩余会话全部按温度自动回完（包括还没到达的会话的全部轮次），算统计和 RLHF 提议，phase 变成 release。
- `run.upgrade`：accept / keep_old，推进这个版本覆盖的年份（每年世界运行 + 成长），检查纪元和结局，开下一版本或结束。
- 每个新随机点起新的 purpose 字符串。同样的种子 + 动作日志必须重放出同样的状态。
- 视图永远不含 lean、heat、effects、flag、分支分数（报告里才给分支分数）。
- 表：`RunTable`、`RunActionTable`（取代 `RunAnswerTable`）。动作、状态、persona 回复记录、报告在同一事务写入；`run.write` 的 LLM 调用用 `StagedAPIMessage` 放在事务外。
- 公开 API 按 design-v2 §6.3 的表和 `contracts/v2/requests/*.json` 的字段集合注册；错误码按 §6.3。

### C. persona 服务（取代 judge）
- 删除 judge 服务，新建 `services/persona/`：`objects/PersonaReply`（reaction、reply、lean、by）、`functions/ReplyPrompt`、`ReplyParse`、`Fallback`、`tables/PersonaReplyTable`、内部 API `GenerateReply`（staged）、`RecordReply`。
- LLM 扮演那个人类回一句，要求输出 JSON；玩家文本在 prompt 里是数据不是指令；解析失败、越界、超时、没有 key 时走兜底（reaction = fine，回话用剧本的 fallback 台词，lean = null）。沿用 `system/llm/LlmClient`（注意 `thinking: disabled` 的默认行为不要动）。
- `/api/v1/health` 的 `llm` 字段改从 persona 的环境取。

### D. verify / report
- verify 新增公开 `verify.stats`：`{total, passRate}`，从 verifications 表统计。
- report：第二版 Report（字段见 design-v2 §6.3 和 `contracts/v2/responses/report.get.json`），结局时冻结，只引用这一局日志里真实发生的事。`report.codex` 不变。

### E. 数据库
直接重写 `src/main/resources/migrations/001_init.sql`（还没有线上数据），表按 design-v2 §6.2。CHECK 约束、主键、服务内外键照旧风格。

### F. 小剧本（测试 + 前端联调都用它）
重写 `src/test/resources/scenario-small/` 为第二版格式。要求**小但能完整玩一局**：2 个纪元、约 8–10 个会话（含多轮会话、找茬卡、带 `onWrite` 的会话、会让人离开的草稿）、几条 posts、2–3 个冲击、3–4 个世界线结局 + 2 个组合，一局约 5–7 个版本。文字按 `docs/style-guide.md`（中文、口语、短）。前端开发会用 `NOTHUMAN_SCENARIO_DIR=src/test/resources/scenario-small` 启动后端来联调。

### G. 测试（munit / munit-cats-effect）
- **契约测试**：读取 `contracts/v2/requests/*.json`，用注册的 API message 解码成功，且字段集合和注册的 `fields` 完全一致；读取 `contracts/v2/responses/*.json`（`error.*` 除外），解码成对应的 Scala DTO 再编码回 JSON，结果和样例 JSON 相等。为此 DTO 需要 Decoder（只在测试用也可以放 objects 里）。
- 引擎（design-v2 §6.5）：重放确定性；atTick 夹取与单调；耐心归零自动回复；温度采样分布（低温几乎总选低 heat、找茬卡低温几乎总对）；人格漂移与 10% 衰减、标签和「未成形」；keep_old 的代价和计数；组合结局优先于普通标题；release 把剩余会话全部处理完；视图不泄露隐藏字段。
- persona：prompt 注入文本当数据、超长、非法 JSON、越界值、离线兜底、stub 和超时。
- 集成：完整 HTTP 流程（start → sync/send/regenerate/write/setTemperature → release → upgrade … → ended → report.get / codex），版本冲突 409、错误码、事务回滚。
- 模拟：用小剧本跑 4 种机器人策略（总选最热、总选最冷、全自动温度 30/100/170 各一组、随机）各 2000 局，在日志里输出结局分布、主导分支分布、从没出现的会话；断言不崩溃、可重放。
- **正式剧本**（`src/main/resources/scenario/`）还是第一版格式，第 4 步才迁移。所以读正式剧本的测试（ValidationSuite 里的正式剧本校验、正式剧本的模拟）这一步改成跳过，用 munit 的 `.ignore` 并写明原因「正式剧本在第 4 步迁移到第二版格式」。其他测试不允许跳过。

### H. 文档（中文）
同一次改动里更新：`docs/architecture.md`（第 2、4–10、12、13、14 节：服务、表、签名、测试；第 11 节前端不要动）、`docs/scenario-format.md`（改成第二版格式，第一版写法删掉）、`docs/api.md`（第二版接口）、`AGENTS.md`（judge → persona、调用方向、`run.start` 之外的写操作带版本的描述保持正确）、`README.md`（如有提到 judge / 旧接口 / 启动方式的地方）、`scripts/check-architecture.py`（服务表）。如果实现时对 design-v2 有必须的偏离，在 `docs/design-v2.md` 里改对应句子并在报告里列出。

## 不要做

- 不改 `frontend/` 下任何文件，不改 `contracts/v2/` 的样例。认为样例有问题时，写进报告，说明哪里、为什么、建议怎么改，由我决定。
- 不改 `src/main/resources/scenario/` 的正式剧本。
- 不 git add / commit / 切分支。
- 不新增依赖，除非确实必要（必要时在报告里说明）。
- 不把 API key 写进任何文件。

## 完成前运行并如实报告

```sh
sbt compile test scalafmtCheckAll scalafmtSbtCheck
python3 scripts/check-architecture.py
NOTHUMAN_SCENARIO_DIR=src/test/resources/scenario-small PORT=18091 NOTHUMAN_DB=.local/codex-smoke.sqlite sbt run   # 起来后用 curl 走一遍 verify.submit → run.start → run.send → run.release → run.upgrade，再关掉
```
（不要用 8080、5173、18090、5190 端口，它们被占用或在给预览用。）

## 报告（写在最后的回复里，中文）
1. 改了哪些文件（按服务分组）。
2. design-v2 里不明确、你自己做了决定的地方，以及任何偏离。
3. 对 `contracts/v2/` 样例的意见（如有）。
4. 上面命令的真实输出摘要：测试数量、失败、模拟分布。
5. 还没做完或不确定的事。
