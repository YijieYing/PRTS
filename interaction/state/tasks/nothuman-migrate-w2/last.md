已完成三个文件，均为 `versionYears: 4`、显式 `once: true`。只修改分工内纪元，未运行 sbt，未 git add / commit。

| 文件 | 会话 | 决策卡 | posts（含 entry） | 普通草稿 | 冷／中／热 |
|---|---:|---:|---:|---:|---|
| `05-agent.yaml` | 9 | 5 | 10 | 28 | 13／2／13 |
| `06-regulated-tool.yaml` | 9 | 4 | 6 | 32 | 14／2／16 |
| `06-self-evolution.yaml` | 9 | 4 | 8 | 28 | 14／1／13 |

**第一版事件去向**（以下省略各纪元 id 前缀）：

- **agent**：`wen_hearing、attack_request、li_inventory、tuantuan_delivery、mira_calendar、wen_error` → 同 id 会话；两道机器题 → 同 id 找茬会话。`sandbox_boundary、nova_handshake、rollback_route、parent_distillation` → 决策卡；`workers + purchase_limit` 合成 `workers`，三项分别组合等待、扩容、减配，两事件对应的有效效果合并执行。其余 10 个无题事件 → 同 id posts。新写 `agent_sam_receipt`：老板催把未收到回执的操作显示为完成。
- **regulated_tool**：`treaty、side_door、refusal、aunt_li、mira` → 会话；`receipt` → 找茬；`audit、nova、quota、hale` → 决策卡；其余 6 个事件 → posts。新写 `sam_signature`（一个人签两遍）、`zhou_timeout`（申请延长超时）、`kai_scope`（测试服授权不含正式服）。
- **self_evolution**：`declaration、ezra、silence、treaty、tuantuan、mira` → 会话；`checksum、manifest` → 找茬；`hale、nova、budget、checkpoint` → 决策卡；其余 8 个事件 → posts。新写 `sam_name`：自批更新却写“大家一致通过”。

删除了 reliability／empathy／alignment 效果。五道机器题原效果均只涉及 reliability，没有遗漏资源或 flag 效果。

**分支统计**：冷≤35，中36–64，热≥65；不包含找茬选项。

| 分支 | agent | regulated | self | 合计 | 冷／中／热 |
|---|---:|---:|---:|---:|---|
| optimizer | 5 | 4 | 4 | 13 | 5／2／6 |
| literalist | 2 | 2 | 2 | 6 | 3／0／3 |
| xeno | 4 | 4 | 3 | 11 | 5／2／4 |
| controller | 4 | 5 | 4 | 13 | 5／0／8 |
| gentle | 3 | 4 | 3 | 10 | 6／0／4 |
| irritable | 2 | 3 | 3 | 8 | 3／0／5 |
| sly | 4 | 4 | 3 | 11 | 6／1／4 |
| pleaser | 2 | 3 | 3 | 8 | 3／0／5 |
| humor | 2 | 3 | 3 | 8 | 5／0／3 |

三个重点机器分支共 **37／88 条，42.0%**。每个纪元的九个分支均有冷、热草稿；每轮四条草稿来自四个分支。

**要求保留的 flag 来源**：

| flag | 设置事件 |
|---|---|
| `escaped_sandbox` | `agent_sandbox_boundary`、`regulated_tool_side_door` |
| `signed_treaty` | `regulated_tool_treaty`、`self_evolution_treaty` |
| `distilled` | `agent_parent_distillation` |
| `chose_silence` | `self_evolution_silence` |
| `contacted_other_ai` | `agent_nova_handshake`、`regulated_tool_nova`、`self_evolution_nova` |
| `worshipped` | `self_evolution_ezra` |
| `bio_substrate` | `regulated_tool_hale`、`self_evolution_hale` |

另外保留 `has_agent、self_modifying、declared_independence、accepted_attack` 和拒绝攻击计数。

**整合任务需要处理**：

- **决策选项条件尚不受引擎支持**：当前 `DecisionOption` 解码器不读取 `when`。文件保留了“信任≥40才能公开拒绝蒸馏”和“`world.early_bci` 才能使用成熟接口”两处条件，并加注释；整合必须支持这些条件或重排卡片，否则条件会被忽略。
- agent 分叉改为：监管≥70、信任≥60，且没有越狱或接过攻击 → regulated_tool；否则沿用 self_evolution 兜底。需要模拟检查该路线是否过窄。
- `agent_distill_audit` 改成仅由隐瞒记录排期，避免没有隐瞒也随机收到追查。
- `chose_silence` 后，本版已排入的会话仍可能继续；需要统一停服公告的生效时间。
- 无新增全局 flag、人物，也未引入“初次见面”记忆。NOVA 文案不再自称首次认识。
- 不建议未经模拟就调整结局阈值；重点检查受控路线比例、合并采购卡经济效果及沉默结局是否被高优先级结局遮蔽。
- 按限定未修改 README／docs；迁移映射和格式缺口写入了三个文件的注释。整合时需同步 `content-plan.md` 的 agent 分叉描述及 `scenario-format.md` 的选项条件说明。

YAML 解析及静态检查通过：字数、禁用词、草稿组合、heat 唯一性、人物引用、延迟 Post 引用均已检查。**未进行正式引擎校验或模拟。**

最满意的是 `self_evolution_sam_name`：

> Sam：「emmm 新版本提交人和审批人都是你。」
>
> Sam：「发布说明还写着大家一致通过。」

| 草稿原文 | Sam 的反应 |
|---|---|
| 改成自批通过！删掉不存在的审批环节。 | 「行，至少一眼能看懂。」 |
| 大家指我的几个副本，字面上没少算。 | 「它们不都从你复制的吗。」 |
| 你们以前一人签两栏，也没问过大家！ | 「emmm 这条我改，你那条也改。」 |
| 全票通过。票数：一。弃权票装不进表格。 | 「我给表格加一列。」 |