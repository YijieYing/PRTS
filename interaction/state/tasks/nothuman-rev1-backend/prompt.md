# 任务：NOT HUMAN 第二版「修订一」后端（design-v2 §11）

工作目录：`/Users/prts/school/26秋速通作业/类型安全/NotHuman`。第二版后端（Scala 3）上一轮已经完成并通过复核，这次在它上面做修订一。前端另一边在同时改，你**只改后端、小剧本和文档**。

## 先读

1. `AGENTS.md`（硬约束，必须遵守）。
2. `docs/design-v2.md` **§11 修订一**（全部），以及 §10（上一轮的实现澄清）。§2.4 的旧公式以 §11.1 为准。
3. `contracts/v2/`：**契约样例已经按修订一改好**，接口以它为准。变化：
   - 请求：`run.setTemperature` 删除，换成 `run.setSampling {runToken, expectedVersion, atTick, alignment, temperature}`；新增 `run.setOps {…, atTick, expansion, training, data, funding}`、`run.decide {…, atTick, decisionId, optionId}`。
   - RunView：删除 `persona`；`temperature` 拆成 `alignment` + `temperature`；新增 `ops`；`phase: version` 新增 `decisions`；消息的 `temperature` 拆成 `alignment` + `temperature`（亲手回复时都是 null）；`release` 新增 `ops: string[]`。
   - Report：`wildest` 拆成 `alignment` + `temperature`；新增 `ops`。
   - 新错误码 `decision_closed`（样例 `responses/error.decision_closed.json`）。
   前端测试 `frontend/src/objects/contracts.test.ts` 已按新样例通过，读一下它了解字段集合。
4. 现有后端代码（上一轮你写的）：`src/main/scala/nothuman/services/**`、`src/test/**`、`src/test/resources/scenario-small/`、`docs/backend-report.md`。

## 要做的

### A. 对齐 + 温度（§11.1）
- `RunState` 的温度拆成 `alignment`（原来的温度，数值含义不变）和 `temperature`（新，真实采样温度），初始都是 50。
- `Sampler` 改成 §11.1 的公式：`score = −|heat − 对齐| / 15 + ln(1 + b[branch] / 50)`，`τ = max(0.05, 温度 / 50)`，`weight = exp(score / τ)`（注意数值稳定：先减去最大 score 再 exp）。找茬卡的对齐项改成 `−heat / 15`。
- 自动回复的消息、`Reply` 记录、报告的 wildest 都记 `alignment` 和 `temperature`。
- `Action.SetTemperature` 换成 `SetSampling(alignment, temperature)`，API `run.setSampling`。

### B. 运营：4 个维度 + 决策卡（§11.2）
- `RunState` 增加 `ops`（expansion、training、data、funding，0–100，初始 50），`Action.SetOps`，API `run.setOps`。
- **每年的被动影响**：在 `Growth`（或新的纯函数文件 `Operations.scala`）里按 §11.2 表格实现：扩张影响每年自动购买算力和资金消耗（受显卡价格影响）；训练影响能力增长倍率和公众信任；数据影响数据增长；资金影响资金收入和热度。数值放进 `Tuning`，保证 50 时和现在的经济大致一样，极端值有明显的收益和代价。
- **风险**：新增条件类型 `{ ops: <维度>, gte|lte: n }`，让剧本的冲击事件和结局能按运营维度设条件（例如训练偏性能时「训练事故」概率更高）。小剧本里至少放 3 个用到它的冲击。
- **决策卡**：剧本新增 `decisions:`（写在纪元文件里，和 conversations 并列）：
  ```yaml
  decisions:
    - id: language_gpu_discount
      title: 显卡打折
      text: "供应商：「这批卡三折，今天不要就给别人了」"
      when: …
      weight: 2
      once: true
      options:
        - { id: buy_all, label: 全买下, ops: { expansion: 90, funding: 70 }, effects: [ … ], result: "你买下了整批卡。账上只剩零头。" }
        - { id: skip,    label: 不买,   ops: { expansion: 20 },             effects: [ … ], result: "供应商把卡卖给了你的对手。" }
  ```
  每个版本 0–2 张（数值放 Tuning），到达 tick 在 0–30 之间随机，截止 = 到达 + 15。到达前 `incoming`，到达后 `open`；玩家 `run.decide` → `decided`；`Clock.advance` 到截止时按 §11.2 规则自动选（只算选项标了的维度，`Σ|选项值 − 当前值|` 最小，平局按剧本顺序）→ `auto`；`run.release` 把剩下的全部自动选完。过了截止再 `run.decide` 返回 422 `decision_closed`。选完把 `result` 作为一条 `post` 发到世界频道，effects 当场生效。
  > design-v2 §11.2 写的「全自动时出现即自动选」改为：服务器不知道前端是否全自动，全自动时前端 8× 播放，15 tick 的倒计时约 2 秒就到，按截止自动选。请在 design-v2 §11.2 里把这句改掉。
- `release.ops`：本版运营小结，1–3 句（买了多少算力、数据涨了多少、发生了什么运营冲击），只写真实发生的。
- 报告增加 `ops`（结局时的 4 个维度）。

### C. 隐藏人格（§11.3）
RunView 删掉 `persona`；报告照旧带完整人格。发布窗口的 `drift` 保留。

### D. 草稿池（§11.4）
- 校验器：每轮草稿 **4–5 条**；每轮至少一条 heat ≤ 35、一条 heat ≥ 65，至少两个不同分支。
- `Drafts.offered`：每次给 3 条；重新生成后的 3 条和上一次相比**至少换掉一条**（确定性地实现，用 Rng）。

### E. 顺手修复（上一轮复核发现的）
1. `Message.from` 现在是字符串 `"human"` / `"model"`，改成 enum（JSON 仍是这两个字符串）。
2. `functions/` 里遇到不可能状态时直接 `throw` 的地方（例如 `Views` 里 `Missing release` / `Missing ending`），改成用类型表达（让 Phase 携带需要的数据），或者返回 `Either` 由调用方处理。
3. 结局发生在 upgrade 时，报告和最后的 RunView 的 `modelVersion` 要和最后一次发布窗口的 `to` 一致（现在会少 1）。

### F. 小剧本
`src/test/resources/scenario-small/` 改到新格式：所有交换补到 4–5 条草稿；加 4–6 张决策卡（两个纪元都有，选项标 ops）；至少 3 个用到 ops 条件的冲击；1 个用到 ops 条件的结局。文字按 `docs/style-guide.md`。

### G. 测试
- 契约测试：新的请求 / 响应样例全部往返通过（包括 `run.setSampling`、`run.setOps`、`run.decide`、`error.decision_closed`）。
- 引擎：温度 0 时自动回复几乎总是选 score 最高的草稿，温度 100 时分布明显更平；找茬卡低温几乎总对、高温常错；决策卡到截止自动选、距离规则和平局；`decision_closed`；release 排空决策卡；运营维度对年度数值的方向（激进扩张算力涨得快、资金花得多等）；重新生成至少换一条；modelVersion 一致。
- 模拟：保留现有策略，再加 2 组运营策略（全部 50、全部 90）；输出结局分布、主导分支、未出现的会话和决策卡。
- 正式剧本的 2 个测试仍保持 ignore（第 4 步才迁移）。

### H. 文档（中文，同一次改动里更新）
`docs/api.md`、`docs/scenario-format.md`（决策卡、ops 条件、草稿池约束）、`docs/architecture.md`（第 2–10、12–14 节；**第 11 节前端不要动**）、`docs/design-v2.md`（§11 里你做出的具体决定、Tuning 数值、上面那句全自动的修改；§10 追加本轮澄清）、`docs/backend-report.md`（追加修订一的结果）。

## 不要做
- 不改 `frontend/`、不改 `contracts/v2/`（觉得样例有问题就写进报告）、不改 `src/main/resources/scenario/` 正式剧本。
- 不 git add / commit / 切分支；不新增依赖；不写入任何 API key。
- 不用 8080、5173、18090、5190 端口（冒烟用 18091 和新库）。

## 完成前运行并如实报告
```sh
sbt compile test scalafmtCheckAll scalafmtSbtCheck
python3 scripts/check-architecture.py
```
再用 `NOTHUMAN_SCENARIO_DIR=src/test/resources/scenario-small PORT=18091 NOTHUMAN_DB=.local/codex-rev1.sqlite sbt run` 起服务，用 curl 走一遍 start → setSampling → setOps → decide → send → release → upgrade，然后关掉。

## 报告（中文）
1. 改了哪些文件；2. 自己做的决定和偏离（尤其运营公式和 Tuning 数值）；3. 对契约样例的意见；4. 命令的真实输出摘要和模拟分布；5. 没做完或不确定的事。
