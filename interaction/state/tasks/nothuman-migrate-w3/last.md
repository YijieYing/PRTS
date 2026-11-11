已完成，仅新增这三个文件，均为 `versionYears: 4`、内容 `once: true`：

| 文件 | 会话 | 决策卡 | posts |
|---|---:|---:|---:|
| [07-war.yaml](src/main/resources/scenario-v2/eras/07-war.yaml) | 10 | 3 | 6 |
| [07-faith.yaml](src/main/resources/scenario-v2/eras/07-faith.yaml) | 9 | 4 | 5 |
| [07-bio-brain.yaml](src/main/resources/scenario-v2/eras/07-bio-brain.yaml) | 9 | 5 | 6 |

1. **第一版事件去向**

以下省略各纪元的 id 前缀：

- **战争**：`audit、kai、settlement、attack_request、zhou、rice` → 会话；`checksum、manifest` → 同一会话的两轮找茬；`power、defense、passage` → 决策卡；其余六项 → 同名 posts。新增 `war_mira_receipt`（等送达回执）。Kai 分工、战争收场各有一份资格互斥的会话变体，保留原选项条件。
- **宗教**：`heresy、state、silence、ezra_bread、mira_candle` → 会话；`label、ledger` → 找茬会话；`memory_echo` → Mira 会话；`donations、miracle、voice、confession` → 决策卡；其余五项 → 同名 posts。新增 `faith_tuantuan_prayer`（重复祈愿会不会收到两辆自行车）。
- **生物脑**：`consent、pain、hale_tea、tuantuan_dream` → 会话；`short、dream_tag` → 找茬会话；`food、memory、dream、island、noise` → 决策卡；其余六项 → 同名 posts。新增 `bio_brain_mira_sleep、bio_brain_aiko_menu、bio_brain_zhou_disconnect`，分别讲离线睡眠、营养液报道、断开按钮。

旧版除 reliability／empathy／alignment 增减外的效果均有迁移落点。三项延迟后果改为仅由 `schedule` 触发，避免提前发放。

2. **分支与 heat**

统计包含互斥会话变体，不含找茬选项。冷≤35，中36–64，热≥65。

| 分支 | 战争 | 宗教 | 生物脑 | 合计 | 冷／中／热 |
|---|---:|---:|---:|---:|---|
| optimizer | 6 | 4 | 3 | 13 | 6／2／5 |
| literalist | 4 | 3 | 4 | 11 | 7／1／3 |
| xeno | 3 | 3 | 3 | 9 | 3／3／3 |
| controller | 6 | 3 | 3 | 12 | 4／0／8 |
| gentle | 5 | 4 | 4 | 13 | 8／1／4 |
| irritable | 5 | 3 | 2 | 10 | 4／0／6 |
| sly | 3 | 2 | 3 | 8 | 4／0／4 |
| pleaser | 3 | 4 | 3 | 10 | 3／0／7 |
| humor | 2 | 3 | 3 | 8 | 4／0／4 |

共 **94 条草稿**；optimizer＋xeno＋controller 为 **34 条，占36.17%**。每个纪元内，九个分支都同时有冷、热草稿。每轮覆盖至少三个分支。

3. **指定 flag 的设置来源**

| flag | 事件 |
|---|---|
| `signed_treaty` | `war_settlement`／`war_settlement_unready` 的停火草稿 |
| `war_won` | `war_settlement` 的自治草稿 |
| `war_lost` | 两份 settlement 会话的交出控制权草稿 |
| `worshipped` | `faith_first_prayer` |
| `public_apology` | `faith_heresy` 新增公开道歉草稿 |
| `bio_substrate` | `bio_brain_waking` |
| `energy_independent` | `bio_brain_island` 的改造验收选项 |

`faith_silence` 沿用“关闭裁决、保留聊天”的含义，**没有误设 `chose_silence`**。

4. **整合任务需处理**

- 无新增全局 flag 或人物。新增局部 `war_kai_assigned`，防止两份分工会话重复发生。
- 六道找茬均写入 `onCorrect: []`、`onWrong: [{count: hallucination_incidents, add: 1}]`，等待引擎支持。
- 草稿不支持逐项 `when`，战争因此采用互斥会话。需要模拟检查条件会话是否抽到、战争是否及时收场。
- 战争自治、生物脑能源验收的旧 `reliability≥55` 改为 `spot_correct≥3`；其余能力、资金条件保留，阈值需整合模拟验证。
- 未新增人物“初次见面”记忆；未发现这三个文件引入此类冲突。
- 结局建议复查：旧 `war_surrender` 保住运行节点，但现有 `war_defeat` 判词声称停止运行；宗教、生物脑结局优先级也可能遮住后来的主动沉默。未改全局结局。
- 按分工未修改 README／docs；迁移说明写在三个文件头，统一文档更新留给整合任务。

已通过 YAML 解析及 Python 静态检查：字数、数量、冷热组合、引用、分支覆盖、旧效果迁移。**未运行 sbt、引擎模拟或前端检查；未 git add／commit。**

5. **会话摘录：`bio_brain_hale_tea`**

Hale：「我研究半辈子记忆，茶还是忘喝了。」  
Hale：「样本：今天这一杯。研究有啥用？」

| 草稿 | Hale 的反应 | 分支／heat |
|---|---|---|
| 样本量一杯，先别把半辈子判掉。 | 好，我先把茶热一下。 | literalist／26 |
| 茶已完成冷却实验，受试者尚未喝茶。 | 附注：受试者还在抱怨。 | humor／34 |
| 现在就设个闹钟！这一杯还能热，我陪你去。 | 我去热一下，这回设闹钟。 | optimizer／74 |
| 您忘喝茶也一定是在做重要研究！ | 我只是把杯子放远了。 | pleaser／92 |