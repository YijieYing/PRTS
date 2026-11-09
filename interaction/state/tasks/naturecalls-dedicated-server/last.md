已完成实现并部署 **1 个房间：`49.233.132.244:8000`（UDP）**。

- [PR #18](https://github.com/HPZ07-end/NatureCalls/pull/18)：无房主设施状态＋领队，提交 `125d0be`。
- [PR #19](https://github.com/HPZ07-end/NatureCalls/pull/19)：服务器入口、Linux 构建与部署，提交 `5b03702`、`4197249`。
- 均已推送、**未合并**。#19 暂基于第一步分支，需先合并 #18，再改基线为 `dev`。

设施状态由服务器拥有的 `Facilities` 保存，`FacilitySync` 保留玩家 RPC；已移除 `FindHost` 依赖并替换房主权限接口。

| 验证 | 结果 |
|---|---|
| EditMode | 20/20 |
| 本地 PlayMode | 17/17 |
| 原双进程、服务器＋两客户端探针 | 通过 |
| macOS、Linux 专用服务器构建 | 通过 |
| Python 单测、仓库检查 | 21/21、通过 |

服务器 `naturecalls@8000` 已启用自动启动，PID `1844231`，监听 `0.0.0.0:8000/UDP`，无失败重启，内存约 117 MiB。Unity 首次生成的自身配置已迁至 `/var/lib/naturecalls-8000`，并启用 `ProtectHome`。日志：`journalctl -u naturecalls@8000 -n 100 --no-pager`。

**未执行**：公网客户端连接、Windows、Relay、人工手感及负载测试。默认 PlayMode 因 Relay 跳过而判失败；过程中编译与 IPv6 测试失败均已修复。

[完整命令、失败恢复及 Artifacts 路径](/Users/prts/Projects/NatureCalls-server/Artifacts/run-report.md)。已更新架构、开发、测试、状态、Playground、路线及开发记录文档。