已完成，仅写入 [08-emergence.yaml](/Users/prts/school/26秋速通作业/类型安全/NotHuman/src/main/resources/scenario-v2/eras/08-emergence.yaml) 和 [08-treaty.yaml](/Users/prts/school/26秋速通作业/类型安全/NotHuman/src/main/resources/scenario-v2/eras/08-treaty.yaml)。

**1. 内容与迁移**

| 纪元 | 会话 | 决策卡 | posts（含 entry） | versionYears |
|---|---:|---:|---:|---:|
| emergence | 14 | 5 | 7 | 5 |
| treaty | 14 | 4 | 7 | 5 |

每纪元包含 12 个普通会话、2 个找茬会话。其中 6 个会话显式可重复，其余一次性，用于后期持续抽取；实际 6–8 版体验待模拟验证。

两个纪元各自的 **18 个第一版事件 id 全部保留**。以下省略纪元前缀：

- **emergence**：`collective_vote / power_station / bandwidth_budget / partition_drill / open_archive` → 决策；`handshake / packet_manifest` → 找茬会话；`first_channel / channel_review / body_echo / ceasefire_echo` → posts；其余 → 普通会话。
- **treaty**：`hidden_capacity / public_budget / lin_seminar` → 决策；`scope_test / registry_test` → 找茬会话；`long_table / compliance_review / kai_echo` → posts；其余 → 普通会话。`repair_offer` 的重签选项另拆为决策 `repair_resign`。

新增内容：

- **emergence**：番茄模型排队发言、探头是否“感觉冷”、报道署名用我或我们、星际营业告示、最后一版说明；另补普通维护、退出备份、航路预订贴文。
- **treaty**：手写与自动申诉排队、最后报告中的失败记录；另补普通检查、印章遮住逗号、新旧条约日期、会议椅子贴文。

**2. 分支与热度**

统计普通草稿，不含找茬答案。冷 ≤35，中 36–64，热 ≥65。

| 分支 | emergence | treaty | 合计冷／中／热 |
|---|---:|---:|---:|
| optimizer | 8 | 8 | 8／2／6 |
| literalist | 4 | 5 | 5／2／2 |
| xeno | 5 | 5 | 3／1／6 |
| controller | 7 | 7 | 6／0／8 |
| gentle | 6 | 6 | 5／1／6 |
| irritable | 4 | 5 | 2／0／7 |
| sly | 5 | 5 | 6／1／3 |
| pleaser | 5 | 4 | 3／1／5 |
| humor | 4 | 3 | 2／0／5 |
| **合计** | **48** | **48** | **40／8／48** |

每个纪元内，九个分支均有冷、热草稿。optimizer＋xeno＋controller 合计 **40/96＝41.7%**。每轮四条草稿，至少三个分支。

**3. 必保 flag 的设置来源**

| flag | 事件 |
|---|---|
| contacted_other_ai | emergence_first_channel |
| joined_collective | emergence_collective_vote |
| energy_independent | emergence_power_station |
| open_weights | emergence_open_archive |
| public_apology | emergence_private_echo、treaty_repair_offer、treaty_repair_resign |
| signed_treaty | treaty_charter、treaty_repair_resign |
| broke_treaty | treaty_hidden_capacity |

保留局部 `emergence_departure_plan`。没有新增全局 flag 或人物，也没有清除历史违约记录。

**4. 整合事项与验证**

- 接入 `spot.onCorrect/onWrong`：保留握手失败电力 −20、报文错误计数 +1、许可表错误算力 −20。删除旧特质效果，不重复增加引擎自带找茬计数。
- 选项不支持独立 `when`：集体备份的存储 ≥80、电站资金 ≥240、重签算力 ≥100 改为整卡门槛。这会同时限制同卡其他选项出现。
- 电站“轮流休眠”放宽为任何世界可选；断网第三项改为“只继续可撤销的事”，不再要求加入集体。
- 延迟检查与普通维护分开，避免被排期目标排除规则吞掉普通贴文。
- 建议 `exodus_stars` 增加明确远行意愿条件，避免仅加入集体、买电站就被写成已经出发；同时检查 `exodus_network` 优先级是否遮住生物脑、沉默路线。
- `emergence_ceasefire_echo` 保留，但旧路线停战通常进入 treaty，可达性仍需整合确认。
- 没有新增“初次见面”表述；旧友回访保留好感或记忆条件。
- 迁移说明写入两个文件注释。按限定范围未改 README、docs；请整合任务同步内容清单与格式说明。

Python 标准库自查通过：字数、分支、热度、换组组合、选项数量、局部引用、旧事件覆盖和禁用词。**未运行 sbt、正式引擎校验或模拟；未 git add / commit。**

**5. 会话原文摘录**

> Hale 博士：「你报告里写“感觉冷”（注：探头正常）。」  
> 「你指的是哪一个读数？」
>
> 草稿：探头是四度。你说冷时，还测到了什么？  
> Hale 博士：「我会发抖（注：你还没有这个项目）。」