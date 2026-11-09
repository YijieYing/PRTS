# 重要边界（本次运行没有沙盒，请严格遵守）
- 只在 `/Users/prts/Projects/NatureCalls-server`（分支 `feat/dedicated-server`，PR #19）内修改文件与运行 Unity；不要读写 `/Users/prts/Projects/NatureCalls` 或其他项目、配置、密钥。
- 联网只用于 `git fetch/push`（origin）与 `gh`（不合并 PR）。本任务不需要登录课程服务器，不要 SSH。
- 不结束不是你启动的进程，不改写 git 历史，不强推。UnityLockfile：只有你自己启动的 Unity 异常退出且确认没有 Unity 进程在运行时，才可删除本目录的 `Temp/UnityLockfile` 后重试。
- 先读 `AGENTS.md`、`docs/TESTING.md`、`docs/IMPLEMENTATION.md`。

# 问题（Claude 复核 PR #19 时发现）
`python3 scripts/unity.py build-server` 用 `-buildTarget Linux64 -standaloneBuildSubtarget Server` 启动 Unity，这会把本工程 Editor 的当前构建目标持久切到 Linux Dedicated Server。之后运行 `python3 scripts/unity.py test-playmode`（不带过滤）时，Editor 以 `UNITY_SERVER` 编译，`Session.Dedicated` 恒为 true，Playground 不生成离线玩家，PlayMode 18 项中 17 项在 SetUp 失败（证据：`Artifacts/20261107T150526Z-1f348b-test-playmode/results.xml`，`DressingRoomTests.cs:45` world.OfflinePlayer 为 null）。你之前报告的 17/17 是在 build-server（14:45）之前运行的。

# 要求
1. 修复：构建服务器后不得让 Editor 停留在 Server 目标。可选做法（自行判断并说明理由）：`Automation.BuildServer` 在 finally 中恢复原构建目标与 `StandaloneBuildSubtarget.Player`；和/或 `scripts/unity.py` 的 test/validate 等动作显式指定本机桌面目标与 Player 子目标。Mac 与 Windows 组员都要适用。
2. 回归验证（全部真实运行并列出 Artifacts）：先 `build-server`，紧接着**不带过滤**的 `test-playmode`（预期 17 通过 + 1 Ignored）、`test-editmode`、`build-macos`、`python3 scripts/server.py <mac build>`、`python3 scripts/multiplayer.py <mac build>`。
3. 如果 `unity.py` 把"有 Ignored"判为失败，修正判定（Ignored 不等于失败，但要在输出中注明），并更新 TESTING.md。
4. 提交到 `feat/dedicated-server` 并推送（结尾 `Co-Authored-By: Codex <noreply@openai.com>`），在 PR #19 说明中补充修复与验证；不要合并。不需要重新部署服务器，除非你修改了服务器运行代码。
5. 最终报告：改动、每条命令真实结果与 Artifacts 路径、未执行项。
