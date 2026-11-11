# 任务：NOT HUMAN 剧本迁移铺开 · 写手 w1

**你负责**：`scenario-v2/eras/` 下的 03-language、03-recurrent、04-multimodal（文件名和第一版相同）。language、recurrent、multimodal 的 versionYears 都是 3。

## 背景（所有写手共用）
工作目录：`/Users/prts/school/26秋速通作业/类型安全/NotHuman`。第二版剧本写在 `src/main/resources/scenario-v2/`。样板（全局文件 + `eras/01-mlp.yaml`、`eras/02-deep.yaml`）已完成并通过审阅，审阅记录在 `docs/scenario-sample-report.md`。现在 **4 个写手并行**迁移其余 11 个纪元，每人只写自己负责的纪元文件；之后由一个整合任务统一校验、模拟和修正。

## 先读
1. `AGENTS.md`；`docs/style-guide.md`（文风硬规则）。
2. `docs/design-v2.md` §2、§3、§5、§11、§11.5、§12；`docs/scenario-format.md`（第二版格式权威）。
3. 样板：`scenario-v2/` 的全局文件和两个纪元文件（**格式和文风的参照**），`docs/scenario-sample-report.md`（尤其第 1、4、5 节）。
4. 第一版对应纪元：`src/main/resources/scenario/eras/<同名文件>`；`docs/content-plan.md`（纪元表、全局 flag、人物、结局意图）。

## 写法（和样板相同，另加审阅意见）
- 拆分规则同样板：society/sweet/humane → 会话；machine → 会话里的找茬卡；resource/technology → 决策卡；纯叙事、里程碑 → posts 或人类消息。
- 每纪元 8–10 个会话（不够就新写，用常驻人物，符合时代感）、3–5 张决策卡、若干 posts；`once` 默认 true。纪元字段沿用第一版，加 `versionYears`（见你的分工）。
- **审阅意见，必须做到**：
  1. **草稿不要套路化**。样板几乎每轮都是「字面主义冷 / 温柔 65 / 讨好 90 / 幽默 75」，玩家几轮就能猜到哪张是什么。要求：同一纪元里，同一个分支的 heat 要有冷有热（冷的狡诈、热的控制者、冷的温柔都可以）；每轮 4–5 条草稿至少来自 3 个不同分支；温柔、字面主义、幽默**不要**每轮都出现。
  2. **机器一侧要多用 optimizer、xeno、controller**。你写的全部草稿里，这三个分支合计至少占 25%；9 个分支在你负责的纪元里都要出现。
  3. 决策卡选项 2–4 个，不要超过 4 个。
  4. 找茬卡如果第一版原题有资源 / flag 效果，用新字段 `spot: { correct, decoys, onCorrect: [effects], onWrong: [effects] }` 保留（引擎会在整合阶段支持这两个可选字段，写法就按这个）。
- 第一版里设置以下 flag 的事件，迁移后**必须仍能设置**（样板因为缺少它们无法通过校验）：`escaped_sandbox`、`signed_treaty`、`distilled`、`chose_silence`、`contacted_other_ai`、`worshipped`、`joined_collective`、`broke_treaty`、`bio_substrate`、`war_won`、`public_apology`、`energy_independent`、`war_lost`、`open_weights`。
- 纪元之间的分叉条件（`next`）沿用第一版的意图；用到已删除特质（reliability、empathy、alignment）的按 design-v2 §2.8 对照表改写。
- 只在自己文件里用的 flag 和人物写在自己文件的 `flags:` / `npcs:` 段，id 加纪元前缀。**不要改全局文件**（manifest、flags、world、npcs、endings）——需要新的全局 flag、人物或对结局的修改，写进报告，由整合任务统一处理。
- 文风：说人话、人物开口说话、AI 冷面字面、一条一个笑点、禁用词、禁格言式收尾。草稿 ≤ 40 字，人类消息一条 ≤ 40 字，决策卡标签 ≤ 14 字，note ≤ 25 字。

## 不要做
- 只写你负责的纪元文件；不改全局文件、其他纪元、第一版剧本、引擎、前端、契约、测试。
- **不要运行 sbt**（4 个写手并行，sbt 会互相冲突；校验由整合任务统一做）。可以用 python3 标准库或肉眼自查（没有 PyYAML）。
- 不 git add / commit。

## 报告（中文，写在最后回复里）
1. 每个纪元：会话 / 决策卡 / posts 数量；第一版事件去向；新写了哪些。
2. 你负责的纪元里 9 个分支各用了几次、heat 分布（冷 ≤35 / 中 / 热 ≥65 各几条）。
3. 设置了上面列表里哪些 flag、在哪个事件。
4. 需要整合任务处理的事：新全局 flag / 人物、结局条件建议、跨纪元的「初次见面」记忆冲突、格式不够用的地方。
5. 贴一段你最满意的会话原文。
