已提交 `a484436`，未 push。实现完成，真实端到端验证受权限阻塞。

改动：`ops/wake.sh`、`ops/wake_run.sh`、`ops/test_wake.sh`、`ops/wakes/.gitignore`、[验证与用法文档](/Users/prts/PRTS/ops/wakes/NOTES.md)。运行目录已忽略；未改 `ops/README.md`。

- **queue**：本机 CLI 帮助只承诺入队；[官方说明](https://developers.openai.com/blog/mastering-codex-remote-for-engineering)未保证客户端关闭后的消费行为。没有可靠检测依据，因此默认 `resume`，支持显式 `--mode queue`。
- **测试**：ShellCheck、语法检查及隔离功能测试通过。
- **真实 dry 验证**：写入 LaunchAgents 被 `Operation not permitted` 拒绝，未触发。
- **真实 pong 验证**：新建 session 时 app-server 初始化被同类权限错误阻止，未执行。未触碰已有 session。
- **睡眠补跑**：本机 `launchd.plist(5)` 明确支持；执行时记录延迟分钟数。

README 用法，5 行：

```sh
ops/wake.sh add '2026-11-01T05:00+09:00' <target> prompt.txt --name earnings
ops/wake.sh add '05:00' <target> prompt.txt --mode resume
WAKE_DRY=1 ops/wake.sh add '05:00' <target> prompt.txt --name dry
ops/wake.sh list
ops/wake.sh cancel <id>
```