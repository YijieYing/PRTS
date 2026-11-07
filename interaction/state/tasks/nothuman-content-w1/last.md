已完成 `eras/01-mlp.yaml`、`eras/02-deep.yaml`，仅写入这两个文件。

| 文件 | 事件 | 选择题／机器填空／人文填空 | 可重复 |
|---|---:|---:|---:|
| 01-mlp.yaml | 20 | 8／2／2 | 6 |
| 02-deep.yaml | 20 | 8／2／2 | 6 |

各文件带题比例 60%，含两道甜点题。Ruby YAML 解析、ID 唯一性、引用、评分档位及数值幅度检查通过。

新增本地 flag：`mlp_kept_holdout`、`mlp_rented_compute`、`deep_overfit_once`、`deep_private_batch`；无新增人物。

整合注意：读取全局人物好感度和世界线 flag；隐私选择设置 `used_private_data`，三回合后设置 `data_scandal`。延迟事件用 `chance: 0` 排除随机抽取，需要引擎到期直接执行，并支持跨纪元触发。

按要求未修改文档，未执行 Git 暂存或提交；引擎尚未实现，未运行游戏模拟。