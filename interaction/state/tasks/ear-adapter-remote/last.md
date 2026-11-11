已完成实现并更新相关文档，改动留在当前工作区，未 commit/push。

- 支持 `dry-run / once / run`、远程写入、有限重放、权限预检及安全停止。
- ②测试：48通过、3跳过；ruff、格式、pyright、文档检查通过。
- 全仓测试：1299通过、630跳过、81失败、96 errors，失败详情已记录。
- **门控集成测试未在本环境运行**。
- 合成565条批次为0.553 MiB，低于8 MiB。

完整中文报告：[last.md](/Users/prts/research/EchoAsRecord-wt/adapter-remote/last.md)。