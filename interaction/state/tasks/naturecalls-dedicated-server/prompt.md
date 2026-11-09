# 重要边界（本次运行没有沙盒，请严格遵守）
- 只在 `/Users/prts/Projects/NatureCalls-server` 内修改文件与运行 Unity；不要读写 `/Users/prts/Projects/NatureCalls` 或用户主目录下的其他项目、配置、密钥。
- 联网只用于：`git fetch/push`（origin 仓库）、`gh pr create`（不合并）、以及用 `~/.ssh/id_ed25519` SSH 到课程服务器 `ubuntu@49.233.132.244` 部署游戏服务器。不要修改服务器的 SSH、防火墙或用户配置，不要安装与本任务无关的软件。
- 不结束不是你启动的进程，不改写 git 历史，不强推。UnityLockfile：用户已同意——只有在你自己启动的 Unity batchmode 运行异常退出、且确认没有任何 Unity 进程在运行时，可以删除本目录 `Temp/UnityLockfile` 后重试；其它情况不要删。
- 前两次运行没有开始实现：第一次被沙盒挡住，第二次被第一次留下的 UnityLockfile 挡住（用户已同意删除，本次启动前已删）。本次从头开始。

# 任务：NatureCalls 专用服务器（给 Codex）

## 分支与起点
- 在 `feat/dedicated-server` 上工作，已包含最新 `dev`（PR #17 合并后，`40fbb4b`）。先读 `AGENTS.md`、`GLOSSARY.md`、`docs/CONTRIBUTING.md`、`docs/IMPLEMENTATION.md`、`docs/TESTING.md`，以及 `docs/ARCHITECTURE.md` 的「网络模型」「网络拓扑与专用服务器方案」「分层（MVC）」。
- Unity 6000.3.26f1，已安装 Linux Build Support 与 Linux Dedicated Server Build Support。GUI 与 batchmode 不能同时打开工程。

## 目标
同一份代码既能作为房主（listen server）运行，也能作为专用服务器运行；`dev` 不分两版。玩家输入服务器地址（`IP:端口`）即可加入，不依赖 Unity Cloud。

## 已定规则（GLOSSARY 2026-11-07）
- 专用服务器上第一个进房的玩家为**领队**，承担房主在大厅和选图中的职责；准备与开始规则不变；领队离开后按进入顺序由下一名玩家接任。

## 要做的事
1. **无房主改造**
   - 门、卷纸、马桶占用、黑色小球的共享状态现在在**房主玩家的** `Network/FacilitySync` 上（`ServerFacilities()` / `FindHost()`）。改到一个由服务器生成、服务器拥有的地图状态对象上；玩家请求仍经自己的 `FacilitySync` RPC 发给服务器校验。
   - `LobbyRoom` 的 `IsHostPlayer`、`FromHost`、`ReadyGuests` 以及 `LobbyController` 的房主界面改为"领队"（房主模式下领队就是房主）。服务器本身不算房间成员。
   - 判定一律以 `IsServer` 为准，不假设服务器是玩家。
2. **纯服务器模式**：`Session` 增加 StartServer 路径与启动参数（如 `-server -port 8000`）；无画面时跳过本地练习玩家、镜头、镜面 RenderTexture 等；限制帧率避免空转；房间空了回到等待状态。大厅「加入房间」支持 `IP:端口`。
3. **构建**：在 `Editor/Automation` 和 `scripts/unity.py` 增加 Linux 专用服务器构建命令（x86_64），并记录到 TESTING/DEVELOPMENT。
4. **部署**（课程服务器）：腾讯云 CVM，Ubuntu 26.04，2 核 / 3.6 GB，公网 IP 49.233.132.244，用户 `ubuntu`（只用 SSH 密钥登录，不要使用或记录密码）。课程开放 **UDP 8000–8100**。用 systemd 运行 1–3 个房间进程（端口 8000 起），日志可查。
5. **测试**：现有房主模式的 EditMode/PlayMode 全部保持通过，`scripts/multiplayer.py` 双进程探针通过；新增服务器模式用例（服务器 + 两个客户端：领队开始、选图、设施同步、领队离开后接任、回合结束回到房间）。

## 约束
- 每个 PR 写 Semantic Diff；领队规则已批准，其它新规则先提议、不要自行写进 GLOSSARY。
- 修改序列化资源用 Unity API（Editor 构建工具），保留 GUID 和 `.meta`；不提交 Builds/Artifacts/密钥/个人路径。
- 已知限制：Unity Transport 服务器版不支持 WebSocket，专用服务器只能走 UDP；屏蔽 UDP 的网络仍可用 Unity Relay（已有）。
- 分两个 PR 合并：先「无房主改造 + 领队」，再「纯服务器模式 + Linux 构建 + 部署」。

## 工作方式（派发补充）
- 你在独立的 git worktree `/Users/prts/Projects/NatureCalls-server` 中工作，已检出 `feat/dedicated-server`。只在这个目录里改动和运行 Unity；不要进入或修改 `/Users/prts/Projects/NatureCalls`（那里是另一个工作副本，用户可能开着 Unity GUI）。这个目录第一次运行 Unity 需要导入 Library，耗时较长属正常。
- Unity 命令用 `python3 scripts/unity.py ...`；不要删除 UnityLockfile，不要强行结束不是你启动的 Unity 进程。
- 可以在 `feat/dedicated-server` 上提交并推送；可以开 PR 到 `dev`，但**不要合并**。提交信息结尾加 `Co-Authored-By: Codex <noreply@openai.com>`。
- 部署到课程服务器前先确认本机测试通过；SSH 只用 `~/.ssh/id_ed25519` 密钥（`ssh ubuntu@49.233.132.244`），不修改 SSH/防火墙配置，不使用密码。
- 遇到需要人类决定的语义问题就停下，在最终报告里列出，不要自行决定。
- 最终报告列出：提交与 PR、每步命令的真实结果和 Artifacts 路径、未执行或失败的项目、部署状态（进程、端口）。
