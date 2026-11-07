已完成两个文件，Ruby YAML 解析及 ID、引用、数值范围、选项和分数段检查通过。

| 文件 | 事件 | 带题比例 | 选择／机器／人文 | 可重复事件 |
|---|---:|---:|---:|---:|
| [06-self-evolution.yaml](src/main/resources/scenario/eras/06-self-evolution.yaml) | 20 | 60% | 8／2／2 | 6（30%） |
| [06-regulated-tool.yaml](src/main/resources/scenario/eras/06-regulated-tool.yaml) | 16 | 62.5% | 7／1／2 | 5（31.3%） |

无新增本地 flag／人物；每个纪元都有两个甜点问题。

整合注意：
- 回响依赖早期全局 flag、林小满好感度及世界线标记。
- 延迟事件通过 `not: always` 排除随机抽取，需确认到期队列直接触发。
- 分叉严格遵循计划表优先级，不清除既有路线 flag。

仅写入分配文件；按要求未修改文档、代码，未执行 Git 提交或游戏模拟。