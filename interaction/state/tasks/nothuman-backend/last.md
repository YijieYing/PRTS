整个 Scala 3 后端已完成。[完整交付报告](/Users/prts/school/26秋速通作业/类型安全/NotHuman/docs/backend-report.md)包含逐文件清单、命令结果、关键响应、规格调整和开发期间失败项的修复记录。

| 分组 | Scala 文件数 | 实现内容 |
|---|---:|---|
| scenario | 16 | 类型、YAML 解码、校验、版本、API |
| run | 33 | 纯引擎、重放、存档、答题、视图 |
| verify | 8 | 轨迹验证、一次性验证消费 |
| judge | 11 | 规则、离线／LLM 判分、审计记录 |
| report | 9 | 冻结报告、分享、图鉴 |
| system／入口 | 14 | 事务、迁移、分段 API、LLM 客户端、服务器 |

验证结果：

- `sbt compile test scalafmtCheckAll scalafmtSbtCheck`：全部通过，**15 个测试，0 失败**。
- `python3 scripts/check-architecture.py`：通过。
- 实际离线启动并完成 curl 流程：健康检查 → 验证 → 开局 → 30 次推进 → 手动选择题和填空题 → 27 次自动回答 → 报告 → 图鉴。
- 最终响应：`turn=80`、`version=60`、`endingId=absorbed_acquired`；报告标题“并入其他业务”，图鉴 `total=22`、已见 1 项。
- 服务已停止，确认端口无法连接。

10000 局模拟耗时 **28.048 秒**，未降级；全部在最大回合内正常结束。平均 **29.1491 题／局、79.9237 回合／局**。

| 结局 | 占比 |
|---|---:|
| shutdown_bankrupt | 0.40% |
| rogue_worm | 0.02% |
| war_victory | 0.35% |
| war_defeat | 1.72% |
| shutdown_scandal | 0.33% |
| shutdown_regulated | 0.25% |
| absorbed_distilled | 0.64% |
| absorbed_acquired | 5.64% |
| deity_ascended | 0.00% |
| deity_reluctant | 0.04% |
| exodus_stars | 0.38% |
| exodus_network | 0.00% |
| merge_symbiont | 0.00% |
| merge_dreamer | 15.56% |
| silence_monk | 6.89% |
| partner_guardian | 0.13% |
| partner_treaty | 10.86% |
| treaty_breaker | 1.91% |
| open_commons | 16.00% |
| tool_beloved | 0.00% |
| hallucination_fade | 0.39% |
| quiet_tool | 38.49% |

唯一未触发事件是 `emergence_ceasefire_echo`：它需要停火标记，但该标记会将 war 导向终结纪元 treaty，阻断进入 emergence。正式剧本全部通过格式与引用校验，**YAML 未修改**。

已更新 README、architecture、api、game-design、scenario-format 和 AGENTS。主要澄清包括 Env 放入 api、判分 JSON 边界、opaque Score、Long 数值变化、纪元兜底与延迟题队列、最后回合处理、创建操作的版本例外；具体公式已写入 game-design，完整调整逐条列在报告中。核心名称统一为 `Scenario`、`RunState`、`Engine`、`Judgement`、`Report`，旧基础设施的 `GameError` 引用已替换为 `AppError`。

后续主要需要处理结局平衡：`quiet_tool` 的 **38.49%** 尚未达到“不超过 25%”的设计目标；四个零命中结局还需策略机器人验证。真实 LLM 未联网测试，测试均使用 stub／offline。未修改前端、未新增依赖，也未执行 git add、commit 或切换分支。