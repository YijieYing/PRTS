任务尚未实现，启动验证遇到环境阻塞。

- 分支：`feat/dedicated-server`，HEAD `40fbb4b`；工作区无修改，无新增提交或 PR。
- `git fetch origin --prune`：失败，本机代理不可达；尝试直连也无法解析 GitHub，公共分支同步未完成。
- `python3 scripts/unity.py detect`：通过，版本 `6000.3.26f1`。
- `python3 scripts/unity.py validate --timeout 3600`：失败，退出码 1。Unity Package Manager 创建本地 socket 被拒绝（`EPERM`），未进入项目编译。详见 [Artifacts 验证结果](/Users/prts/Projects/NatureCalls-server/Artifacts/20261107T140304Z-1c58bd-validate/summary.json) 和 [Editor 日志](/Users/prts/Projects/NatureCalls-server/Artifacts/20261107T140304Z-1c58bd-validate/editor.log)。
- 仓库检查通过；Python 单测 **21/21 通过**，不代表 Unity 测试通过。
- 无房主改造、服务器模式、Unity 测试、多人探针及构建均未完成。未连接或部署课程服务器，进程和端口状态未核实。

`Semantic-Diff: none`。未修改文档，因为没有实现变更。继续工作需要运行环境允许 GitHub 访问及 Unity 本地 IPC；当前会话禁止提权，无法在此解除限制。