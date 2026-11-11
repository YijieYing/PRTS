已完成修改，未 commit、push 或切换分支。

- `BUSINESS_TYPES` 改为从核心 `DEFAULT_REGISTRY` 推导，显式排除管理反馈；不纳入动态插件类型。
- 更新两份模块文档，新增回归测试。
- 定向测试：74 通过。
- lint、格式、pyright、文档检查均通过。
- 全量 pytest 未通过：1347 通过、627 跳过、81 失败、96 错误，包含端口权限和日志存储问题。

逐项结果、失败输出及未确定原因见 [last.md](/Users/prts/research/EchoAsRecord-wt/api-registry/last.md)。