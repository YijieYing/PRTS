# 任务：② 接入 ① 持久服务（远程写入、常驻扫描、CommitUnknown 重放、真实 ① 联调测试）

## 背景

②（`services/adapters`，包 `ear_adapter`）已完成转换、导入规则和测试，但命令行 `ear-adapter`（`src/ear_adapter/__main__.py`）只支持 `--dry-run`：写进 `MemoryStorage`，跑一轮就退出。① 的持久服务和远程 SDK `RemoteStorageClient`（`libs/ear_storage_client/src/ear_storage_client/remote.py`）已在 dev。先读：

- `services/adapters/README.md`、`ai-docs/implementation.md`（数据流、导入规则、5.3 尚未覆盖）、`ai-docs/payloads.md`
- `services/storage/ai-docs/interface.md` 第 0 节（远程客户端调用规则：token 身份、`write(ops, context, request_id=None)`、`CommitUnknown` 必须用 `e.request_id` 与相同 ops/context 重放、读取须显式 grant 包括本模块类型）
- `services/storage/ai-docs/persistent-service-plan.md`、`deployment.md`（限制：HTTP 请求体默认 8 MiB 等；签发用部署内 `AuthOperator.issue_principal`）
- `libs/ear_storage_client/src/ear_storage_client/remote_errors.py`（`CommitUnknown`、`ServiceUnavailable`、`ResourceLimit`、`AuthenticationError`、`ProtocolError`）
- `src/ear_adapter/runtime.py`（`Runner`、`ingest_capture`、各 outcome）

`Runner` 只依赖 `StorageClient` 协议，所以核心是：命令行能构造 `RemoteStorageClient`，写入路径能正确处理远程特有的错误。

## 要做

### 1. 命令行

- 子命令设计（可调整，但要在文档里写清）：
  - `ear-adapter dry-run`：保持现有行为（内存存储 + 第二轮模拟重扫），兼容旧的 `--dry-run` 写法或在文档里说明改名。
  - `ear-adapter once`：连 ① 跑一轮，打印摘要，退出码反映是否有 source_error / Failed。
  - `ear-adapter run [--interval 秒]`：常驻，每轮之间等待（默认 60 s，限定合理范围），收到 SIGTERM/SIGINT 时把当前一段录音处理完再退出；每轮输出一行结构化摘要日志。单轮内旧 Ear 掉线或 ① 不可用（`ServiceUnavailable`）只记日志，下一轮重试，不退出进程；`AuthenticationError` / `PermissionDenied` 这类配置错误直接退出非零。
- 配置只从环境变量读，token 绝不进命令行参数或日志：沿用 `EAR_ADAPTER_EAR_URL`、`EAR_ADAPTER_EAR_TOKEN`、`EAR_ADAPTER_DATA_ROOT`；新增 `EAR_ADAPTER_STORAGE_URL`、`EAR_ADAPTER_STORAGE_TOKEN`（① 签发给 `adapter` 的 token）。核对 `deploy/.env.example` 和 `deploy/` 的约定，必要时在 `.env.example` 增加这两项的占位（不放真实值）。
- `__main__.py` 顶部 docstring 里「① 的持久化服务还没有实现」等过时内容要改掉。

### 2. 远程写入的错误处理（`runtime.py`）

- 每段录音仍是**一批原子写入**。写入时显式生成并保留 request_id；遇到 `CommitUnknown`，用 `e.request_id`、**相同的 ops 和 context** 重放，有限次数、带退避；仍未知则该录音记为 Pending（下一轮会先查 `audio_ref` 是否已存在，确定性 id + dedup_key 保证不会重复）。不要每次重算 ops 再写。
- `ServiceUnavailable`：本轮中止或该录音 Pending（选一种并说明理由），不要标成 Failed。
- `ResourceLimit` / 请求体超限：该录音 Failed，原因写清（例如批次字节数），不要静默拆批——拆批会破坏「③ 收到声纹事件时，局部说话人和录音已可读」的顺序保证（见 `tests/test_runtime.py::test_voiceprint_event_arrives_after_its_local_speaker`）。如果你认为必须拆批，只在报告里提出方案，不实现。
- 在报告里估算真实录音的批次大小（一段 30 分钟录音大约几百条记录，声纹 embedding 内联），判断 8 MiB 是否够用；可以用合成数据按真实条数量级构造一批测量序列化大小。

### 3. 权限

② 的 token 需要的授权：写 7 种原始数据类型（由登记表 writer=adapter 决定），**读**这 7 种类型（`Runner` 用 `audio_ref` 查询判断是否已导入，以及去重相关读取），不需要订阅。在 `services/adapters/README.md` 或 `ai-docs/implementation.md` 写明所需 `read_types`，并说明：① 当前部署初始化（`init-identities`）只签发 api 管理员和 manage-worker 两个身份，**没有 adapter 身份的签发流程**，正式部署需 ① 负责人 / I 决定；本地联调用测试夹具里的 `AuthOperator.issue_principal("adapter", read_types=[...])`。不要修改 ① 的部署脚本。

### 4. 真实 ① 联调测试（门控）

在 `services/adapters/tests/` 新增一个集成测试文件，只在 `EAR_RUN_POSTGRES_TESTS=1` 且 `EAR_RUN_NATS_TESTS=1` 时运行（否则 skip），复用或仿照 `services/storage/tests/conftest.py` 的临时 Docker PostgreSQL/NATS 夹具与 ① 服务的启动方式（参考 `services/storage/tests/test_http_postgres.py`、`test_api_gateway_integration.py` 怎么起 HTTP 服务和签发身份）。如果夹具不能跨包直接复用，选最小的复用方式（例如把 conftest 里的夹具提成可导入的测试辅助），并说明；不要复制一大段夹具代码。测试用合成数据（`ear_adapter.testing` 的 `FakeSource` / `make_evidence` 一类），覆盖：

- 经 `RemoteStorageClient` 导入一段合成录音：各类型条数与内存版一致，每条通过 `contracts/records/raw-record.schema.json`。
- 新建 `Runner`（模拟重启）重扫：全部 AlreadyIngested，① 里没有新增记录、没有新事件。
- 另一个模块身份（例如 `attribution`，授予读和订阅 `voiceprint`/`local_speaker`/`audio_ref`）订阅后能收到「新增声纹」事件，并在 handler 里读到声纹引用的局部说话人和 audio_ref（远程版的 `poll_once` / `run_until_idle`）。
- `CommitUnknown` 重放：用可注入的故障（例如包装 `StorageClient`，第一次 write 真正提交后抛 `CommitUnknown`）验证重放使用同一 request_id、最终只有一份数据。这一条也要有不依赖 Docker 的单元测试版本。
- 没有读授权的 adapter token：报出明确错误，而不是把所有录音当成未导入反复写。

**你的沙箱很可能无法使用 Docker 或访问本机网络**。如果跑不了门控测试，照常写好，跑一遍确认会被 skip、并且 pyright/ruff 通过；在报告里写明「门控集成测试未在本环境运行」，由审查方在本机跑。不要为了能跑而去掉门控。

### 5. 文档

- `services/adapters/README.md`「当前状态」、`ai-docs/implementation.md`（数据流、第 5 节验收、5.3 尚未覆盖、新增运行方式与环境变量、权限要求）。
- 去掉所有「命令行仍只写 MemoryStorage」之类将变过时的描述（全仓 grep，包括 `services/storage/` 和 `ai-docs/plans/mvp-implementation.md` 里提到 ② 现状的地方；不在 ② 目录的文件只改关于 ② 现状的那句话）。
- 实现说明里补一节「本机真实 ① 联调步骤」：怎么跑门控测试；以及怎么让真实旧 Ear 数据写进一个**本机临时** ① 的步骤草案（审查方会照着做并回填结果）。真实数据不进仓库。

## 不做

- 不改 ① 的服务代码、部署脚本、contracts、`ear_storage_client`（如发现 SDK 的 bug，只在报告里描述）。
- 不改 7 种数据的 payload 字段格式（另有提案处理）。
- 不改转换规则和 readiness 规则。
## 通用要求（三个任务都适用）

- 仓库规则：先读 `AGENTS.md`、`README.md`。不填写或修改 `reviewed-by` / `reviewed-at`。不把凭据、真实录音、GPS、转写写进仓库。
- 只在当前工作目录（一个 git worktree，分支已建好）里改。**不要 commit、不要 push、不要切换分支**；改动留在工作区，由审查方提交。
- 改了行为、接口、命令、配置，就同时更新描述它们的文档（模块 `README.md`、`ai-docs/`、会变错的注释）；收尾前在仓库里搜一遍旧名称，改掉过时引用。
- 交付前运行完整检查，并在报告里贴出每一项的结果（通过数 / 失败输出）：
  `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest && uv run python tools/check_docs.py`
- 报告（last.md）用中文，写清：改了哪些文件、为什么这样改、测试结果、没做或做不到的事、发现的文档/契约/代码冲突。不确定的地方如实写，不要猜测成已完成。
