# 任务：NOT HUMAN 修订二联调测试 + 剧本迁移样板

工作目录：`/Users/prts/school/26秋速通作业/类型安全/NotHuman`。分两部分，**按顺序做**。

## 第一部分：修订二联调和全量测试（先做）

修订二（design-v2 §12：滑杆从玩家亲手操作里学习 + 锁定）的后端刚由上一个 Codex 任务完成，前端由 Claude 写好（`frontend/src/pages/Chat/components/Knob.tsx`、`hooks/chatActions.ts` 的 setLock / 排队、`ReleaseModal` 的学习小结）。Claude 这次额度紧张，**联调和测试由你负责**：

1. 跑全部检查并如实记录：
   ```sh
   sbt compile test scalafmtCheckAll scalafmtSbtCheck
   python3 scripts/check-architecture.py
   cd frontend && npm run format:check && npm run typecheck && npm test && npm run build && PLAYWRIGHT_CHANNEL=chrome npm run test:e2e
   ```
   （e2e 自己用 18080 / 5180 起前后端，后端用测试小剧本、每次新库。）
2. 在 `frontend/e2e/game.spec.ts` 的手动测试里补修订二的检查：亲手点一张草稿后，对齐滑杆旁出现「学到了」（或对齐数值变化）；点对齐的锁图标（`aria-label` 为「锁定对齐」/「解锁对齐」）后 `aria-pressed` 变化；拖过的温度滑杆自动锁定（锁按钮 `aria-pressed=true`）。如果某个断言因为随机性不稳定，改成稳定的写法并说明。
3. 联调发现的问题：后端的直接修；**前端的小问题（显示、交互、类型）你也可以直接修**，但不要改设计和布局，改了什么在报告里逐条列出（文件、原因）。大问题写进报告不要动。
4. 前端改动后同步 `docs/architecture.md` 第 11 节里对应的描述。

第一部分全部检查通过后，再开始第二部分。

## 第二部分：剧本迁移样板


工作目录：`/Users/prts/school/26秋速通作业/类型安全/NotHuman`。第二版引擎已经完成（多人会话、草稿卡、对齐 / 温度、运营决策卡、学习、锁定）。正式剧本 `src/main/resources/scenario/` 还是**第一版格式**（时间线 + 选择题 / 填空题）。这次先迁一个**样板**：全局文件 + 前两个纪元，审过以后再铺开其余纪元。

## 先读（全部读完再动手）
1. `AGENTS.md`；`docs/style-guide.md`（**文风硬规则**，必须遵守）。
2. `docs/design-v2.md`：§1、§2（机制）、§3（结局两层 + 组合表）、§5（剧本格式）、§11（对齐 / 温度 / 运营 / 决策卡 / 草稿池）、§11.5（规模预估）、§12（学习）。
3. `docs/scenario-format.md`：**第二版剧本格式的权威说明**（含决策卡、ops 条件、草稿池约束）。
4. `src/test/resources/scenario-small/`：第二版格式的完整例子（只用来看格式，它的文字质量不是样板）。
5. 第一版正式剧本：`src/main/resources/scenario/`（manifest、flags、world、npcs、endings、eras/*.yaml）；`docs/content-plan.md`（第一版的纪元表、全局 flag、人物、结局设计意图）。

## 产出位置
**不要改 `src/main/resources/scenario/`**（第一版保留到全部迁移完成再替换）。第二版写到新目录 `src/main/resources/scenario-v2/`，结构和第一版相同：

```
scenario-v2/
  manifest.yaml  flags.yaml  world.yaml  npcs.yaml  endings.yaml
  eras/01-mlp.yaml  eras/02-deep.yaml
  eras/zz-sample-end.yaml   # 样板专用的临时终结纪元，铺开时删除
```

## 这次要做
### A. 全局文件（一次做完整，后续纪元共用）
- `manifest.yaml`：第二版字段（初始资源、对齐 / 温度 / 运营初值如需要等），maxTurns 80，firstEra mlp。
- `flags.yaml`：沿用第一版全局 flag；删掉第二版不再需要的。
- `npcs.yaml`：12 个常驻人物，补 `patience.decay`（2–4，按人设：Mira 慢、Kai 快）和 `avatar`（不同的整数种子）。台词风格按 style-guide 第 3 节。
- `world.yaml`：世界线沿用；冲击事件沿用并改成第二版写法，**加上 ops 条件**：训练偏性能 → 训练事故；数据偏激进 → 隐私丑闻；资金偏融资 → 收购压力；扩张激进 + 显卡贵 → 资金危机。概率适中。
- `endings.yaml`：22 个世界线结局全部保留 id 和意图，条件里用到已删除特质（reliability、empathy、alignment）的按 design-v2 §2.8 的对照表改写（人格侧强度 / 分支、计数器、flag、公众信任），条件里可以用 ops 条件；**组合表 combos 写 12–15 条**（§3 的 10 条示例都要有），标题 ≤ 8 字、判词 ≤ 80 字，一个具体细节 + 一句话。
  - 注意：第一版的结局分布很不均（quiet_tool 占 38%，有 4 个结局从没出现），改写条件时一并考虑，目标是任何结局 ≤ 25%、22 个都可达。完整平衡在第 5 步做，这次先把明显不可达的条件修正。

### B. 纪元 01-mlp、02-deep
- 纪元字段沿用（id、title、visual、minTurns、maxTurns、next、entry），加 `versionYears: 2`。
- 第一版的事件按类别拆：
  - `society`、`sweet`、`humane` 类带题事件 → **会话**（conversations）。人类消息用第一版的人物台词（已按文风改写过的直接沿用）。原选项改写成"你会说的那句话"作为草稿；**每轮 4–5 条草稿**，至少一冷（heat ≤ 35）一热（heat ≥ 65）、至少两个不同分支；每条有 `lean`、`heat`、`reaction`（对方的回话）、`effects`（沿用原选项的效果，删掉对已删除特质的效果）。选项括号里的抽象代价全部去掉，代价写进 effects，靠对方的反应体现。可以把一个事件写成 1–3 轮交换。
  - `machine` 类填空 → 会话里的**找茬卡**（spot）：正确答案 + 2–3 个只差一点的干扰项。
  - `resource`、`technology` 类带题事件 → **运营决策卡**（decisions）：选项标 `ops` 倾向、沿用 effects、写一句 `result`（结果发到世界频道）。
  - 纯叙事事件、里程碑 → `posts`（世界频道）或某个人类的一条消息，选更有画面感的那种。
- **数量**：每个纪元约 8–10 个会话（第一版不够就新写，用已有人物，符合纪元的时代感）、3–5 张决策卡、若干 posts。
- `once` 默认 true；常驻人物在不同纪元以不同会话出现。
- `remember` 的 note 沿用（≤ 25 字）。
- 所有新文字按 style-guide：说人话、人物开口说话、AI 叙述冷面字面、一条一个笑点、禁用词、禁格言式收尾。草稿 ≤ 40 字，人类消息一条 ≤ 40 字。

### C. 样板专用
- `eras/zz-sample-end.yaml`：一个临时终结纪元（`terminal: true`），让 deep 之后能走到结局，从而样板可以完整玩一局。deep 的 `next` 照第一版写（recurrent / language），**但样板阶段**把它们改指向 `sample_end`，并在文件顶部注释写明「样板阶段临时指向，铺开时恢复」。

### D. 让测试能跑正式剧本
现在 `ValidationSuite` 和 `SimulationSuite` 里读正式剧本的两个测试是 ignore。改成：**设置了环境变量 `NOTHUMAN_SCENARIO_DIR` 时**，这两个测试读这个目录并运行（不设时保持 ignore 和原因说明）。这样可以：
```sh
NOTHUMAN_SCENARIO_DIR=src/main/resources/scenario-v2 sbt "testOnly nothuman.scenario.*"
```
校验 + 模拟（各策略 2000 局即可）。

## 不要做
- 不改 `src/main/resources/scenario/`（第一版）、`frontend/`、`contracts/v2/`、引擎逻辑（除 D 的测试入口外；如果发现引擎 bug 或格式不够用，写进报告，不要自己改）。
- 不 git add / commit；不新增依赖；不用 8080、5173、18090、5190 端口。

## 完成前运行并如实报告
```sh
sbt compile test scalafmtCheckAll scalafmtSbtCheck
python3 scripts/check-architecture.py
NOTHUMAN_SCENARIO_DIR=src/main/resources/scenario-v2 sbt "testOnly nothuman.scenario.*"
```

## 报告（中文）
1. 每个纪元：会话 / 决策卡 / posts 数量，第一版哪些事件去了哪里，新写了哪些。
2. 结局条件的改动清单（尤其是改写了已删除特质的、修正不可达的）和组合表。
3. 模拟结果：结局分布、主导分支、从没出现的会话和决策卡。
4. 文风上你没把握的地方、格式不够用的地方。
5. 挑 3 段你认为最好的会话原文贴在报告里，方便审阅。

## 最后的报告
先写第一部分（检查结果、修了什么），再写第二部分（按上面的报告要求）。
