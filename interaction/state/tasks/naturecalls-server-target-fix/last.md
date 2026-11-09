已提交并推送 `14996ac`，包含指定 Co-Author；[PR #19](https://github.com/HPZ07-end/NatureCalls/pull/19) 说明已更新，未合并，工作区干净。

修复：服务器构建后由独立 Editor 进程恢复本机 Player，验证目标、子目标及 `UNITY_SERVER` 已关闭；其他动作也显式指定 Player。Mac/Windows 分别选择本机目标。Ignored 单独计数，不再误判失败。未修改运行时代码，Semantic Diff：none。

以下按要求顺序真实执行，均退出 0。路径均位于本项目 `Artifacts/`：

| 命令 | 结果 | Artifacts 子目录 |
|---|---|---|
| `unity.py build-server` | 构建及恢复验证通过 | `20261107T154016Z-1f43eb-build-server`（含 `restore/`） |
| `unity.py test-playmode`，无过滤 | 17 Passed + 1 Ignored | `20261107T154138Z-b76c53-test-playmode` |
| `unity.py test-editmode` | 20/20 | `20261107T154247Z-2fed2e-test-editmode` |
| `unity.py build-macos` | 通过 | `20261107T154304Z-cdc4a3-build-macos` |
| `server.py <mac build>` | 三端通过 | `20261107T154338Z-3f5aa2-server` |
| `multiplayer.py <mac build>` | 两端通过 | `20261107T154413Z-faf4de-multiplayer` |

命令均使用 `python3 scripts/…`。两个探针使用同一产物：`Builds/macOS/20261107T154304Z-cdc4a3/NatureCalls.app`。

Python 28/28、仓库检查、Semantic Diff 检查通过。更新了 TESTING、DEVELOPMENT、DEVELOPMENT_STATUS 和 status-log。

未执行：Windows 实机、Linux 二进制运行、Relay、跨设备/公网及人工手感验收。未 SSH、未重新部署。