已完成三个文件：

| 文件 | 事件 | 选择题／机器填空／人文填空 | 可重复事件 |
|---|---:|---:|---:|
| `eras/07-war.yaml` | 17 | 7／2／2 | 5 |
| `eras/07-faith.yaml` | 17 | 7／2／2 | 5 |
| `eras/07-bio-brain.yaml` | 17 | 7／2／2 | 5 |

每份带题比例 64.7%，可重复比例 29.4%。Ruby YAML 解析、ID 唯一性、引用、数值范围及题目结构检查均通过。

新增本地 flag：
- 战争：`war_audit_pending`、`war_kai_ally`、`war_kai_opponent`
- 宗教：`faith_miracle_claim`
- 生物脑：`bio_brain_dream_trial`

没有新增人物。回响依赖全局攻击记录、Kai／Ezra 好感、`open_weights`、`long_memory` 及电力短缺／早熟脑机接口世界线。战争胜负互斥。

整合时需确认延迟事件不会提前进入随机池，并能跨纪元兑现；尚未验证运行时分布。按分工只写了指定 YAML，未修改文档或代码，未暂存或提交。