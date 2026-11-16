# 工程团队纳入桌面会话

已把按 cwd 归属工程的 Claude / Codex 本机会话并入 team。复用 AgentConsole scan.py，只调用数据读取函数，不调用进程扫描、HTTP 或详情读取；AgentConsole 文件未修改。

沿用 group、project、team；新增内部 sessions 适配器负责复用扫描器，没有增加并列会话解析器。projects.match 是唯一目录前缀匹配实现；pulse/lib/sources.py 的 project 仅保留未归属/目录名回退，删除原先重复的前缀循环。这一处是共享匹配所需的适配，没有修改 reporter、pulse 日报生成或配置文件，也没有提交其他任务改动。

Claude CLI ID 根据 desktop 元数据统一为 local ID，含旧 transcript；与派发、订阅去重，归档 Claude 排除。本机会话提供标题，活动时间取最新来源。订阅者置顶且不受窗口或上限限制；非订阅成员按最近 14 天（含边界、不含未来）、时间倒序最多 10 个。家目录本身及家目录登记项不参与匹配。扫描器提前多读一天，精确窗口由 groups 统一裁剪。

## 真实环境只读核验

`interaction/bin/status threads --json` 成功，generated_at：2026-11-16T18:11:45.026090+00:00。
DsHarness 2 人、SomaNet 2 人、OS 课（rCore）3 人，完整 team 如下：

```json
[
  {
    "name": "DsHarness",
    "team": [
      {
        "kind": "claude",
        "id": "claude:local_66a82cf1-44da-4ece-926e-0b109e146819",
        "title": "仓库同步",
        "subscribed": false,
        "last_active": "2026-11-15T04:16:36.939000+00:00"
      },
      {
        "kind": "claude",
        "id": "claude:local_6c93f091-123e-4584-acf2-a24fe39260c2",
        "title": "DeepSeek Harness 设计文档导读",
        "subscribed": false,
        "last_active": "2026-11-13T23:40:28.991000+00:00"
      }
    ]
  },
  {
    "name": "SomaNet",
    "team": [
      {
        "kind": "codex",
        "id": "codex:01a1d147-d3f3-7f10-801e-9a1044be9d15",
        "title": "概述当前几个 E 的设计",
        "subscribed": false,
        "last_active": "2026-11-15T15:06:38.951000+00:00"
      },
      {
        "kind": "claude",
        "id": "claude:local_aa5280c7-fab7-4316-b8de-d95dc70372d6",
        "title": "生物与AI网络架构对比",
        "subscribed": false,
        "last_active": "2026-11-13T10:34:54.447000+00:00"
      }
    ]
  },
  {
    "name": "OS 课（rCore）",
    "team": [
      {
        "kind": "codex",
        "id": "codex:01a1d314-c0ee-79f2-89b6-3303bbfcb7d9",
        "title": "查看K3开发板与机器人选题",
        "subscribed": false,
        "last_active": "2026-11-16T12:39:17.034000+00:00"
      },
      {
        "kind": "claude",
        "id": "claude:local_eed7eda1-6039-4d38-acee-2fcbf4661f2a",
        "title": "OS 晚间补课计划与大作业选题",
        "subscribed": false,
        "last_active": "2026-11-13T10:34:54.421000+00:00"
      },
      {
        "kind": "claude",
        "id": "claude:local_9e1ad094-9f70-4e04-825c-a53a79ea5d44",
        "title": "PRTS硬件层探索与OS课题",
        "subscribed": false,
        "last_active": "2026-11-10T20:19:03.089000+00:00"
      }
    ]
  }
]
```

GET http://127.0.0.1:7788/api/state 连接失败（curl 退出 7）；未核实 AgentConsole UI，以上为 CLI 的实际输出。ID 沿用其 agent.id / app_session_id 契约。

## 测试

fixture 使用临时 Claude JSONL、desktop 元数据与 SQLite 数据库，覆盖最长前缀、路径边界、exact、家目录排除、14 天边界、过期/未来过滤、两来源归档、订阅/派发/目录匹配去重、标题、倒序和最多 10 个。也核验 pulse 使用共享匹配后保留原有未匹配目录回退。测试运行器的所有子进程使用 DEVNULL stdin。

现有 18 个测试入口已跑完。初轮 pulse 因共享匹配导入缺少仓库根路径而失败，补齐 sources.py 的独立入口导入后，重跑 test_pulse 的 91 项全部通过（包含完整 18 项 EarTests、12 项 FocusTests）；groups 最终 3 项全部通过，其余入口均通过，含 wake shell 验收。没有遗留失败。原始结果与修复后输出保存在 tests.json；git diff --check 通过。

## 文档与交付

更新 interaction/README.md 的 team 来源、ID、窗口与排序契约；更新 GLOSSARY.md 的 team 定义；human/README.md 增加报告入口，human/projects.toml 修正家目录登记项的过时注释。AgentConsole 内部 API 与数据库格式是兼容依赖；缺失 checkout 时保留订阅/派发，单源读取失败在 stderr 报警。

仅按文件路径提交本任务变更，不 push。
