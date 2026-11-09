# 任务：在 AgentConsole 里把 Codex 任务挂到派发它的 session 下面（给 Codex）

涉及两个仓库：`~/PRTS`（interaction 模块）和 `~/PRTS/AgentConsole`（独立 git 仓库，在 PRTS 里被 gitignore）。工作目录是 `~/PRTS`。
先读：`~/PRTS/GLOSSARY.md`、`interaction/README.md`、`AgentConsole/README.md`、`AgentConsole/agent_console/scan.py`、`AgentConsole/agent_console/server.py`。

## 背景
- AgentConsole 的左侧树按目录排列；`parent` 字段指向另一个 agent 时，前端会把它挂到那个 agent 下面，跨目录也行（`static/index.html` 的 `buildTree`，不用改前端）。
- 总控刚加了一种父子关系：Claude 桌面 app 里由一个 session 启动的另一个 session，按 app 元数据的 `spawnedFrom` 挂到启动者下面（AgentConsole 提交 d082c89）。
- 还缺的：由某个 session 通过 `interaction/bin/dispatch` 或 `resume` 派出去的 Codex 会话，现在只按目录出现，看不出是谁派的。

## 要做的事
1. **interaction 记录派发者和 Codex 会话 id**（改 `interaction/lib/codex`、`bin/dispatch`、`bin/resume`，registry 只能通过 `lib/registry` 写）：
   - start 事件追加 `caller` 字段，取值顺序：
     - 环境变量 `CLAUDE_CODE_SESSION_ID`，记为 `{"kind":"claude","id":...}`；
     - 如果没有，取 `CODEX_THREAD_ID`（Codex 里派发时；如果 Codex 不提供这个变量，就查清楚 Codex 有没有等价变量，没有就跳过）；
     - 都没有就不写这个字段。
   - Codex 启动后，从 `run.log` 里解析 `session id: <uuid>`（现在的日志里有这一行）。追加一条 `thread` 事件：`{"name":..., "event":"thread", "thread":<uuid>}`。
     - dispatch 本来就会在确认启动时读 run.log，在那里顺便做。
     - resume 的线程 id 就是传入的 thread，直接写。
   - 保持现有字段不变，只能追加。
2. **对外接口** `interaction/bin/status links`：每行输出一个 JSON `{"child": <codex thread uuid>, "parent": <caller id>, "parent_kind": "claude"|"codex", "task": <name>}`。只输出既有 thread 又有 caller 的任务。
   - 过去的任务没有 caller，不要猜，不输出。
   - 但可以从旧 run.log 补出 thread 事件。如果你补，只追加事件，并且写一个一次性脚本放进 `maintenance/`。
3. **AgentConsole 读取父子关系**：
   - `server.py` 的 CONFIG 新增可选项 `links`：一条命令（和 `on_event` 一样用 shlex 拆分并 expanduser），输出上面格式的 JSON 行。
   - 扫描时调用它，带超时，失败就忽略，不能拖慢或卡住扫描循环；可以缓存，每 60 秒刷新一次。
   - 对 `kind == "codex"` 且自己没有 parent 的 agent：如果 links 里有它，而 parent 也在本机 agent 列表里，就设 `parent` 和 `spawned_by`。
   - AgentConsole 是通用的监视程序，不能写死 PRTS 的路径，PRTS 只出现在用户的配置里。
   - 在 `AgentConsole/README.md` 写明这个配置项。
4. **测试**：
   - interaction：dispatch/resume 写 caller 和 thread；`status links` 的输出。必须在临时目录里，沿用 `PRTS_INTERACTION_STATE` 和替身 codex 的写法，不碰真实 state 或真实 Codex。
   - AgentConsole：links 命令成功、失败、超时三种情况；Claude 的 `spawnedFrom` 嵌套（d082c89 还没有测试，请补上）。
   - 两边现有测试全部通过：
     - `python3 interaction/tests/test_modules.py`
     - `bash interaction/tests/test_wake.sh`
     - `cd AgentConsole && python3 -m unittest discover -s tests`
   - 注意：测试的子进程不能继承调用方的 stdin（替身会读 stdin）。

## 不要动
- `~/.agentconsole/config.json`（总控来改）、launchd、`human/`、`memory/`、`GLOSSARY.md`、`ROADMAP.md`、`README.md`（PRTS 根目录的）。
- `interaction/state/` 里已有的数据：不删除、不改写，只能追加。

## 交付
- 两个仓库各自提交，每个提交只做一件事。
- 报告写清楚：改了哪些文件；新增的字段和接口；测试命令和输出；「试过」和「验证过」分开写。
