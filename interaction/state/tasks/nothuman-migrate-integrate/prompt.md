# 任务：NOT HUMAN 剧本迁移 · 整合（design-v2 §9 第 4 步收尾）

工作目录：`/Users/prts/school/26秋速通作业/类型安全/NotHuman`。4 个写手刚并行写完 `src/main/resources/scenario-v2/eras/` 下其余 11 个纪元（样板 01-mlp、02-deep 和全局文件之前已完成）。他们没跑 sbt，也不能改全局文件。你负责把整套第二版剧本整合成可用的正式剧本。

## 先读
1. `AGENTS.md`、`docs/style-guide.md`、`docs/design-v2.md`（§2、§3、§5、§11、§12）、`docs/scenario-format.md`、`docs/scenario-sample-report.md`。
2. 4 个写手的报告：`~/PRTS/interaction/state/tasks/nothuman-migrate-w{1,2,3,4}/last.md`（里面有需要你处理的全局 flag / 人物 / 结局建议 / 记忆冲突 / 格式问题）。
3. `scenario-v2/` 全部文件。

## 要做（按顺序）
1. **引擎小改**：找茬卡支持可选的 `onCorrect: [effects]`、`onWrong: [effects]`（写手可能用了），校验器、编解码、引擎、测试一起改，`docs/scenario-format.md` 补上。
2. **处理写手报告里的事**：新全局 flag / 人物加进全局文件；跨纪元「初次见面」的 remember 冲突统一；结局条件按建议和可达性调整；组合表补到 15 条左右，覆盖更多分支。
3. **收尾样板临时内容**：删除 `eras/zz-sample-end.yaml`，恢复 02-deep 的 `next`（recurrent / language 分叉，见文件顶注释）。世界冲击里样板为通过校验改成 `since: game` 的，恢复成按纪元限定（现在纪元都在了）。
4. **校验 + 模拟**：`NOTHUMAN_SCENARIO_DIR=src/main/resources/scenario-v2 sbt "testOnly nothuman.scenario.*"` 直到通过；修所有校验问题（引用、长度、草稿池约束、flag 来源……）。文风问题顺手修，结构问题写进报告。
5. **替换正式剧本**：校验通过后，用 `scenario-v2/` 的内容替换 `src/main/resources/scenario/`（第一版已备份在 `.local/scenario-v1-backup-20261109/`，不用再备份），删除 `scenario-v2/` 目录。读正式剧本的两个测试恢复为默认运行（不再需要环境变量，也不再 ignore）；`NOTHUMAN_SCENARIO_DIR` 环境变量的功能保留。
6. `frontend/playwright.config.ts` 去掉 `NOTHUMAN_SCENARIO_DIR`（e2e 改用正式剧本）；不要运行 e2e（你的沙箱启动不了 Chrome，Claude 会在本机跑）。
7. **模拟报告**：正式剧本跑全部机器人策略（每组 10000 局），输出结局分布、主导分支分布、从没出现的会话 / 决策卡 / 结局 / 组合。这一步**不要求**达到平衡目标（第 5 步才做平衡），但要如实列出：哪些结局 > 25%、哪些从没出现。
8. 文档：`README.md`（状态、启动命令去掉小剧本说明，改成正式剧本）、`docs/handover.md`（第二版进展：第 4 步完成，下一步第 5 步平衡）、`docs/design-v2.md` §9 和 §11.5（实际规模）、`docs/scenario-format.md`、`docs/content-plan.md`（标注第二版的纪元表和内容规模）、`docs/backend-report.md` 追加。

## 不要做
不改 `frontend/` 除 playwright.config.ts 外的文件；不改 `contracts/v2/`；不 git add / commit；不新增依赖；不用 8080、5173、18090、5190 端口。

## 完成前运行并如实报告
```sh
sbt compile test scalafmtCheckAll scalafmtSbtCheck
python3 scripts/check-architecture.py
sbt "testOnly nothuman.scenario.*"
```
再用正式剧本（不设 NOTHUMAN_SCENARIO_DIR）在 18091 + 新库起服务，curl 走一局到结局，然后关掉。

## 报告（中文）
1. 每个纪元的会话 / 决策卡 / posts 数量总表；全剧本 9 个分支的草稿占比和 heat 分布。
2. 处理了写手报告里的哪些事；结局条件和组合表的改动。
3. 引擎改动（找茬 onCorrect / onWrong）。
4. 命令的真实输出摘要和模拟分布（标出 > 25% 和从没出现的）。
5. 没做完或不确定的事、文风上你没把握的地方。

## 追加（Claude 试玩样板时发现）
- 样板第一个版本 5 个会话全是 Sam：前两个纪元 9 个会话里 6 个是 Sam，按权重随机抽就会扎堆。请在引擎的 `Version.open` 加一条规则：**同一人物在一个版本里最多 2 个会话**（数值进 Tuning），并补测试；同时检查每个纪元的人物分布，单个人物不超过该纪元会话数的 40%，超了就把部分会话换成其他常驻人物来说。
