# 任务：NOT HUMAN 第二版「修订二」后端（design-v2 §12）

工作目录：`/Users/prts/school/26秋速通作业/类型安全/NotHuman`。在修订一（上一轮你做的）基础上加一个小功能：6 个滑杆从玩家**亲手**的操作里学习，玩家手动设置过的滑杆锁定。前端另一边在改，你**只改后端、小剧本（如需要）和文档**。

## 先读
1. `AGENTS.md`。
2. `docs/design-v2.md` **§12 修订二**（全部），以及 §11.1（score 公式）、§10 和 §11 里的实现澄清。
3. `contracts/v2/`：样例已更新。变化：RunView 增加 `locked`（Knob 数组，固定顺序 alignment、temperature、expansion、training、data、funding）；`release` 增加 `learned: {knob, from, to}[]`；新请求 `requests/run.setLock.json`（`runToken, expectedVersion, atTick, knob, locked`）和响应 `responses/run.setLock.json`。前端测试 `frontend/src/objects/contracts.test.ts` 已按新样例通过。

## 要做的
1. `Knob` 枚举、`RunState.locked: Set[Knob]`（新局为空，跨版本保留）、版本开始时记录 6 个滑杆的值供 `learned` 计算。
2. 学习规则按 §12.1，放在一个新的纯函数文件（例如 `run/functions/Learning.scala`），系数全部进 `Tuning`：
   - `run.send` 亲手点草稿（找茬卡除外）：对齐向草稿 heat 靠 25%；温度按点之前的 score 排名（第 1 名 −4、第 2 名 0、第 3 名 +6）。score 排名只在当时展示的 3 条里排，平局按展示顺序。
   - `run.regenerate`：温度 +3。
   - `run.decide` 亲手选：选项标了的运营维度向选项值靠 30%。
   - 自动回复、自动决定、`run.write` 不学习。被锁定的滑杆不学习。结果截断 0–100。
3. 锁定（§12.2）：`run.setSampling` / `run.setOps` 只把**值确实变了**的滑杆加入 locked；新 Action `SetLock(knob, locked)` 和公开 API `run.setLock`（字段集合按样例）。
4. `release.learned`：本版本开始 → 发布时每个滑杆的净变化，只列变了的；同一滑杆一条。注意手动设置造成的变化**不算** learned（只算学习造成的）：实现时分别累计学习带来的变化，或在版本内记录"学习前后"的差值，你选一种清楚的做法并写进 design-v2 §12 的实现澄清。
5. 测试：契约往返（含 setLock）；每条学习规则的方向和幅度；锁定后不学习；setSampling 只锁改动的那个；自动回复 / 自动决定 / write 不学习；learned 只含学习造成的净变化；重放确定性。模拟机器人：保持现有策略即可（机器人走的是亲手操作，学习会影响它们的自动回复部分），日志照常输出分布。
6. 文档（中文）：`docs/api.md`、`docs/architecture.md`（第 11 节前端不要动）、`docs/design-v2.md` §12 追加「实现澄清」小节、`docs/backend-report.md` 追加修订二结果。

## 不要做
不改 `frontend/`、`contracts/v2/`、`src/main/resources/scenario/`；不 git add / commit；不新增依赖；不用 8080、5173、18090、5190 端口。

## 完成前运行并如实报告
```sh
sbt compile test scalafmtCheckAll scalafmtSbtCheck
python3 scripts/check-architecture.py
```
再用 18091 和新库（`.local/codex-rev2.sqlite`）起服务，curl 走一遍 start → send（看对齐变化）→ setSampling（看 locked）→ setLock 解锁 → release（看 learned），然后关掉。

## 报告（中文）
改了哪些文件；自己做的决定；对样例的意见；命令真实输出摘要；没做完或不确定的事。
