# status threads 分层投影交付

已新增顶层 `groups`，保持原 `threads` 内容与字段不变。大项目按登记顺序排列，同名工程合并路径，未分组置后；无活动工程仍显示。ROADMAP 支持编号表格和 Markdown 任务清单，最多显示 5 条未完成事项，读取或格式错误以 error 返回。

采用通用 `roadmap_prefix`：PRTS 总控台使用 R，AgentConsole 使用 M。规范术语沿用 `group`（大项目）、工程和 `team`（工作团队），新增内部 groups 模块；没有引入同义层或需要删除的旧名称。

team 复用订阅与 registry：有效工程订阅全部保留；历史非订阅成员按最近 14 天筛选、去重，最多 10 个，整体按活动时间倒序。历史记录覆盖 PRTS 派发的 Codex 与 caller，caller 表示派发参与者，不代表其自身 cwd 已核实。未派发、未订阅的桌面会话不在该数据源中。Codex UUID 对应左栏 agent.id；Claude CLI ID 对应 agent.id，local ID 对应 app_session_id；无映射的两种 Claude ID 不猜测合并。

任务统计复用原 project thread：running 数量；已结束且未 reviewed 数量；最近事件时间。

## 真实环境摘要

运行 `interaction/bin/status threads --json` 成功，采样时间：2026-11-15T17:18:35.873587+00:00。完整快照在 status.json。以下数量是返回的 ROADMAP 条目数（最多 5），不是文件中全部未完成项数。

| 大项目 | 工程 | ROADMAP 条目 | team 人数 |
|---|---|---:|---:|
| 工具与赚钱 | aquant 交易 bot / BigQuant | 0 | 10 |
| 工具与赚钱 | 记账 | 0 | 1 |
| 工具与赚钱 | AIInfra 中转站 | 0 | 0 |
| 工具与赚钱 | lain 上的项目 | 0 | 0 |
| PRTS | PRTS 总控台 | 5 | 10 |
| PRTS | PRTS 研究 | 0 | 10 |
| PRTS | CodexBridge 微信秘书 | 0 | 0 |
| PRTS | CodexBridge 秘书 | 0 | 0 |
| PRTS | Codex 原理学习 | 0 | 1 |
| PRTS | Ear 手机端（octopus-flutter） | 0 | 2 |
| PRTS | Ear（EchoAsRecord） | 0 | 9 |
| PRTS | DsHarness | 0 | 0 |
| PRTS | AgentConsole | 5 | 5 |
| 具身与果蝇脑 | 果蝇脑 DigitalFly | 0 | 6 |
| 具身与果蝇脑 | SomaNet | 0 | 0 |
| 机器人硬件 | SwarmBot 多机器人 | 0 | 0 |
| 机器人硬件 | XinDong 小车 | 0 | 0 |
| 课程 | NatureCalls（软工课 Unity） | 0 | 3 |
| 课程 | 课程作业 | 0 | 10 |
| 课程 | OS 课（rCore） | 0 | 0 |
| Outreach | Outreach | 0 | 0 |

Ear 配置指向的 mvp-implementation.md 是其他结构的规划文档，未找到支持的编号表格或任务清单；roadmap.open=[]，error 明确说明格式不支持。没有把 0 条解释为没有待办，也没有修改该工程文档。

本次 GET http://127.0.0.1:7788/api/state 未连接成功（curl 退出 7），未核实 AgentConsole 运行状态或前端展示；CLI 不依赖该服务。

## 兼容与验证

对冻结的同一份真实 registry、事件和订阅输入，运行 HEAD 旧实现与新实现，17 条 threads 完全相同。旧严格 schema 保持 threads 各字段校验，仅对顶层投影排除新 groups 字段。新增 fixture 覆盖分组与未分组、路径合并、两种 ROADMAP、前缀、缺失/不支持文件、空闲工程、团队去重/窗口/上限、派发重启与 worktree、订阅优先、任务计数。测试运行器和新增 CLI 子进程都关闭 stdin。

## 文档

更新 interaction/README.md 的 groups 契约、来源边界和 ID 对应；GLOSSARY.md 的 group/team 与 ROADMAP 定义；human/projects.toml 的前缀注释和 R/M 配置；human/README.md 增加本报告入口。

## 回归结果

interaction、pulse、reporter 共 16 个测试入口全部通过（194 个 Python unittest，另有 wake shell 验收）。reporter/test_ear_sync.py 没有 main 入口，已通过 unittest discover 实际执行。逐项结果见 tests.json；git diff --check 通过。

仅提交本任务实现、测试、文档和验收产物；不提交其他任务的 registry/state 改动，不 push。
