已创建两个文件：

| 文件 | 事件 | 选择题／机器填空／人文填空 | 可重复 |
|---|---:|---:|---:|
| `eras/04-multimodal.yaml` | 22 | 8／2／3 | 7 |
| `eras/05-agent.yaml` | 22 | 8／2／3 | 7 |

均有 59.1% 事件带题、31.8% 可重复。YAML 解析、ID 唯一性、引用、选项代价和数值范围检查通过。没有新增本地 flag 或人物。

整合注意：
- 回响读取 `used_private_data`、`open_weights`、`long_memory`、`chain_reasoning`、`acquired` 及人物好感度。
- 两个延迟后果用 `when: { not: always }` 排除随机抽取；需确认 `schedule` 到期投递不重判该条件。
- 智能体入口设置 `has_agent`，`next` 已按规划配置。

仅写分配的 YAML，未修改文档或提交 Git；引擎未实现，未做运行模拟。