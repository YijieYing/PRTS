# PRTS ops：wake.sh，在指定时间唤醒一个 agent session

工作目录：`~/PRTS`，是 git 仓库。先读 `ops/dispatch.sh`、`ops/retry_resume.sh`、`ops/on_event.sh`，以及 `ops/registry.jsonl` 的事件格式，沿用它们的风格：bash、短小、事件写进 registry。

## 为什么
现有工具都只在有人行动后才触发：总控发消息，或者一个 Codex 任务结束。没有办法让某个 agent 在某个时间点被唤醒去做一件事。
例子：10-30 Amazon 财报约 05:00 JST 发布，aquant 的 Codex session 当时已经结束，没人叫它去核实财报。于是推送到微信的内容全是「未核实」。

## 要做
1. **`ops/wake.sh add <when> <target> <prompt-file> [--name <name>]`**
   - `<when>`：ISO 时间（如 `2026-10-30T23:40+09:00`），或 `HH:MM`（东京时间；已过则顺延到明天）。拒绝过去的时间。
   - `<target>`：Codex session 的 UUID 或线程名。第一版只支持 Codex。
   - 把 prompt 复制进 `ops/wakes/<id>/`（id 由时间和 name 组成），同时写一个 spec.json：时间、target、模式、cwd、状态。
   - 生成一次性 launchd plist `~/Library/LaunchAgents/com.prts.wake.<id>.plist`，用 `StartCalendarInterval`，并 bootstrap。
   - registry 记一行 `{"event":"wake_scheduled",...}`。
2. **到点由 `ops/wake_run.sh <id>` 执行**
   - 用合适的方式把 prompt 投给 target。
   - 先查清楚 `codex queue --thread` 的语义：没有打开的客户端时，消息会不会被消费？给证据。
   - 若有可靠的判断方法，则：
     - 能被消费 → 用 queue；
     - 不能 → 用 `codex exec resume`。可以复用 `retry_resume.sh` 的参数，至少包括 sandbox、approval、writable_roots、cwd，并处理 at capacity。
   - 若没有可靠的判断方法，在 spec 里由 `--mode queue|resume` 显式指定，默认 resume，因为 resume 一定会跑一个 turn。
   - registry 记 `wake_fired`，以及结果 `rc`。
   - 执行后 bootout 并删除 plist：它是一次性的，`StartCalendarInterval` 会每年重复。spec 状态改为 done 或 failed。
   - 机器睡眠错过的时间：launchd 唤醒后会补跑。确认这一点；补跑时在 registry 写明延迟了多少分钟。
3. **`ops/wake.sh list`** 列出未执行和最近执行的；**`ops/wake.sh cancel <id>`** 取消。
4. **安全**
   - prompt 内容只作为消息参数传递，不经 shell 解释：用文件或参数数组，防注入。
   - plist 和 spec 权限设为 0600；不写任何 key。
   - 同一 target 同一分钟内不重复添加。

## 验证
- `WAKE_DRY=1`：到点只把要执行的命令写进日志，不真的调用 codex。
- 用 `WAKE_DRY=1` 安排一个 2 分钟后的真实 launchd 任务，确认它按时触发，并且 plist 已自删。
- 再挑一个可丢弃的测试 Codex session（自己用 `codex exec` 新建一个只回复 "pong" 的），真实安排一次唤醒，确认它收到消息并执行了一个 turn。不要碰 aquant 或其他已有 session。
- 写一个 shell 测试，至少覆盖：时间解析、拒绝过去的时间、去重、cancel。

## 边界
- 只改 `ops/wake.sh`、`ops/wake_run.sh`、`ops/wakes/`（把 `ops/wakes/*/` 加进 .gitignore 或忽略运行数据，你决定并说明），以及测试文件。
- 不要改 `ops/README.md`，总控在写它。
- 只提交你自己的路径：`git commit -- <paths>`。不要 push。

## 汇报
- 改动文件；
- `codex queue` 语义的结论和证据；
- 两次验证的结果；
- 给 README 用的用法段落，5 行以内。
