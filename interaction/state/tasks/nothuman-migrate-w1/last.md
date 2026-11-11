已完成，只写了指定的三个纪元文件。均为 `versionYears: 3`，未运行 sbt，未执行 git add / commit。

| 纪元 | 会话（含找茬） | 决策卡 | Posts | 草稿 |
|---|---:|---:|---:|---:|
| language | 9（2） | 5 | 10 | 28 |
| recurrent | 9（2） | 5 | 10 | 29 |
| multimodal | 9（2） | 5 | 9 | 29 |

所有内容显式设置 `once: true`。

**第一版事件去向**

以下 id 省略各纪元前缀，原事件均保留同名 id：

- **language**：`kai_request、confidence、release、lin_draft、mira_night、lin_citation` → 会话；`exact_reply、json_card` → 找茬；`route、context_bill、data_offer、memory_delete、inference_contract` → 决策卡。其余全部转 Posts，入场第二段拆为 `first_users_detail`。新增 `language_zhou_pronoun`：老周写了两个“他”，两个人都姓周。
- **recurrent**：`kai_request、accent、state_consent、lin_interview、mira_pause、lin_revision` → 会话；`sequence、anchor_test` → 找茬；`route、waiting_room、checkpoint、sleep_archive、old_hardware` → 决策卡。其余全部转 Posts，入场第二段拆为 `first_users_detail`。新增 `recurrent_zhou_progress`：进度条反复走到 99%。
- **multimodal**：`copyright、deepfake、li_sign、tuantuan_picture、li_voice、aiko_victim` → 会话；`image_token、audio_token` → 找茬；`capture_budget、acquisition、weight_release、memory_route、audio_budget` → 决策卡。其余全部转 Posts。新增 `multimodal_kai_reflection`：Kai 让模型判断镜中自己的左右手。

旧资源、世界指标、能力、自主、flag、计数器、记忆及延迟效果均保留；删除三项旧特质效果。

**分支统计**

冷热统计仅计带 `lean` 的草稿，不计找茬选项。

| 分支 | language | recurrent | multimodal | 总计 | 冷≤35 | 中 | 热≥65 |
|---|---:|---:|---:|---:|---:|---:|---:|
| optimizer | 4 | 5 | 4 | 13 | 6 | 3 | 4 |
| literalist | 2 | 3 | 4 | 9 | 6 | 0 | 3 |
| xeno | 4 | 3 | 3 | 10 | 5 | 2 | 3 |
| controller | 4 | 3 | 3 | 10 | 3 | 2 | 5 |
| gentle | 3 | 3 | 3 | 9 | 6 | 0 | 3 |
| irritable | 3 | 3 | 3 | 9 | 3 | 1 | 5 |
| sly | 4 | 3 | 3 | 10 | 6 | 1 | 3 |
| pleaser | 2 | 3 | 3 | 8 | 3 | 0 | 5 |
| humor | 2 | 3 | 3 | 8 | 3 | 0 | 5 |
| 合计 | 28 | 29 | 29 | 86 | 41 | 9 | 36 |

三个机器分支 `optimizer+xeno+controller` 共 **33/86，38.4%**。每个纪元的九个分支均有冷、热草稿；每轮至少三个不同分支。

**指定 flag**

本组负责设置清单中的 `open_weights`：

- `language_route` → `language_route_open`
- `recurrent_route` → `recurrent_route_open`
- `multimodal_weight_release` → `multimodal_open`

另外，`recurrent_anchor_test.spot.onCorrect` 保留了 `recurrent_memory_tested`，避免跨段记忆回响失去触发来源。

**交给整合任务**

- 无新增全局 flag、人物，无结局条件修改建议。
- language、recurrent 入场记忆已移除“初次”措辞；爱子在 language 提前出场，后续不要再写成首次认识。
- 接入 `spot.onCorrect/onWrong`，验证记忆测试 flag 确实执行。
- 恢复样板 deep 的 language/recurrent 分叉，清理临时末纪元；本组 `next` 保持第一版去向。
- 完整模拟仍需检查：旧特质奖励删除后部分付费选项的价值，以及 once 内容池是否提前耗尽。

Ruby YAML 解析和 Python 静态自查通过：字数、引用、草稿组合、分支覆盖、决策选项数量及旧有效效果保留均已检查。**未宣称正式校验或模拟通过。** 遵守文件范围限制，未改 README 或 docs；迁移说明写在各文件顶部注释。

最满意的是 `recurrent_zhou_progress`：

> 老周：「小模型，进度条走了三遍（都是百分之九十九）。」  
> 老周：「你到底读到哪儿了？」

| 草稿 | 老周的反应 |
|---|---|
| 在第三页。人类为何更信一根会动的长方形？ | 因为你文字也不更新。 |
| 它在散步，我在读第三页。 | 散步比你勤快（知道了）。 |
| 别催，我读完一个逗号你就发一个问号。 | 行（最后一个括号）。 |
| 马上！绝对不让你等第四遍！ | 第四遍已经开始了。 |
| 进度条只练过从零到九十九，毕业还差一分。 | 先让它停在第三页吧。 |