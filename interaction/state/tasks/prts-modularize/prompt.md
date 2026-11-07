# 任务：PRTS interaction / reporter 模块内部重构（给 Codex）

工作目录 `~/PRTS`，git 仓库。先读 `GLOSSARY.md`（目标结构和术语）、`interaction/` 和 `reporter/` 的现有文件。

## 背景
总控（Claude）已经把文件挪到了目标目录，只改了路径，没改逻辑：
- `interaction/bin/{dispatch,resume,wake}`、`interaction/lib/wake_fire`、`interaction/tests/test_wake.sh`；
- 数据在 `interaction/state/`：`tasks/<task>/{prompt.md,last.md,run.log}`、`wakes/`、`registry.jsonl`；
- `reporter/bin/{report,notify}`、`reporter/lib/*`、`reporter/config/config.toml`、`reporter/state/{out,outbox}`。
- `ops/` 里只剩指向新位置的符号链接（过渡期保留），以及 `on_event.sh`、`unpushed_reminder.sh`、`README.md`。

架构规则（必须遵守）：
- 模块之间只调用对方 `bin/` 下的命令，不读写对方的 `lib/` 或 `state/`。
- 代码和数据分开：`bin/` 是对外命令，`lib/` 是内部实现，`state/` 是运行时数据。
- 每份数据只有一个写入者。

## 要做的事
1. **registry 单写者**：新建 `interaction/lib/registry`（shell 可 source 的函数或一个小的 python CLI 都行），作为唯一写 `state/registry.jsonl` 的代码。`dispatch`、`resume`、`wake`、`wake_fire` 都改用它，事件格式保持向后兼容（字段 t/name/event/...）。
2. **Codex 适配层**：新建 `interaction/lib/codex`，封装 `codex exec`、`codex exec resume`、`codex queue`，包括：
   - 关闭 stdin；
   - workspace-write 加仓库 git 目录的写权限；
   - 「at capacity」时按间隔重试。
   `dispatch`、`resume`、`wake_fire` 都改用它。`wake` 现在直接读 Codex 的 `state_5.sqlite` 来把会话名解析成 UUID，把这段挪进 `lib/codex`，让它成为唯一接触 Codex 内部文件的地方，并在注释里写明这是对 Codex 内部格式的依赖。
3. **wake 的内部子命令**：`_claim`、`_fields`、`_finish`、`_capacity` 移到 `interaction/lib/wake_state`。`bin/wake` 只对外暴露 `add`、`list`、`cancel`；`lib/wake_fire` 调用 `lib/wake_state`。
4. **事件队列**：新建 `interaction/bin/event`：
   - `event add <L0|L1|L2> <source> <text>`：追加一行 JSON 到 `interaction/state/events/queue.jsonl`，字段为 id、t、level、source、text、status=new。L2 另外调用 `reporter/bin/notify alert`。
   - `event from-agentconsole`：从 stdin 读一条 AgentConsole 事件 JSON。分级策略照搬现在的 `ops/on_event.sh`（包括「派发任务的进程 dormant」的判断，它读 registry，改用 lib/registry），结果写进事件队列，**不再写 `human/inbox.md`**。
   - `event list [--new]`、`event ack <id>`：给总控验收用。
5. **reporter notify 分级**：`reporter/bin/notify <log|wechat|alert> [--title T] (--text TEXT | --file PATH)`：
   - log：只追加到 `reporter/state/out/notifications.jsonl`；
   - wechat：现在的行为（CodexBridge `weixin notify`）；
   - alert：wechat 加 macOS 通知（osascript）。
   向后兼容：第一个参数以 `--` 开头，或者是 `outbox` 时，按旧接口处理（等同 wechat / 查看 outbox）。各渠道的实现放进 `reporter/lib/channels/`。
6. **改掉所有写 `human/inbox.md` 的代码**，改成调用 `interaction/bin/event add L1 ...`：
   - `ops/unpushed_reminder.sh`：原地改写；总控之后会把它挪进 AgentConsole 的 backup 插件；
   - `reporter/lib/aquant_daily.py` 里校验失败时写 inbox 的地方。
   `ops/on_event.sh` 改成一行，转调 `interaction/bin/event from-agentconsole`，用于过渡。
7. **测试**：
   - 把 `interaction/tests/test_wake.sh` 改到新布局。
   - 新增测试，覆盖：registry、event（add/list/ack/from-agentconsole）、notify 的 log 级、dispatch 的 dry 模式。dispatch 需要新增 `DISPATCH_DRY=1`：只记录将要执行的命令，不真跑 codex。
   - 所有测试都必须在临时目录里跑，不碰真实的 state、LaunchAgents、微信或 Codex 会话。为此给 interaction 和 reporter 各加一个指定 state 根目录的环境变量，比如 `PRTS_INTERACTION_STATE`。
   - 全部测试跑通。
8. 每个模块写一份 `README.md`（中文，简短）：这个模块做什么、`bin/` 下每条命令的用法、`state/` 里有什么。内容与 `GLOSSARY.md` 保持一致；GLOSSARY 由总控更新，你不用改。

## 不要动
- `human/`、`memory/`、`GLOSSARY.md`、`AGENTS.md`、`ops/README.md`（总控负责这些文档）。
- `~/Library/LaunchAgents`、`~/.agentconsole/`、aquant 仓库、CodexBridge 仓库、`AgentConsole/` 目录。
- `interaction/state/` 和 `reporter/state/` 里已有的数据：不删除、不改格式。新字段只能追加。
- 当前有一个 NatureCalls 的 Codex 任务在跑，它会往 `state/tasks/naturecalls-dedicated-server/` 和 `registry.jsonl` 写东西，不要碰。

## 交付
- 分几次提交到 `~/PRTS` 的当前分支，每个提交只做一件事。
- 最后的报告写清楚：
  - 每个文件的变化；
  - 对外接口有没有变化（旧调用方式是否仍然可用）；
  - 测试命令和完整输出；
  - 没做完或有疑问的地方。
- 「试过」和「验证过」要分开写。
