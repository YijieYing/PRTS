# M11：PRTS 数据、完成标记与提醒

已实现契约中 PRTS 侧全部功能。没有 push，没有对真实 roadmap 执行 mark、review 或 PR 轮询，没有发送真实通知。

## 交付

- 按表头解析，兼容旧 PRTS 表格、前缀与清单；保留旧 open/error 语义，新增 items、工程和大项目 next_ddl、meetings。过期 DDL 参与最早值。
- roadmap list/mark，精确改单元格，证据缺列追加到最后一列；按文件所属仓库提交单一路径，其他暂存文件不进入提交。
- dispatch --roadmap 启动前校验并写入 start registry；review 写回完成。复用 github_poll，按工程已有独立编号关联 PR，打开只记录 pr_open，合并写回完成；文件锁和终态记录防重复。
- reporter remind 使用 notify phone，支持 7 天、2 天、当天和过期首次提醒、12:00 后组会提醒；quiet 持久化待发并延后发送。组会正文三行，最近完成包括 Git 历史中手工完成和自动记录。
- 统一使用既有 canonical 名词 roadmap、item、review、meetings、next_ddl，没有引入重复领域层或遗留兼容模块。

## 验证

所有子进程 stdin 关闭，模型、GitHub 和通知均使用 fixture/替身；Git 写回使用临时仓库。

| 检查 | 结果 |
|---|---|
| interaction 全套 unittest discover | 52 项通过（含当时新增的 5 项 roadmap 测试） |
| reporter 全套 unittest discover | 31 项通过（含当时新增的 3 项 DDL 测试） |
| pulse 全套 unittest discover | 130 项通过 |
| interaction/tests/test_wake.sh | PASS |
| 最终 roadmap 专项 | 7 项通过；新增跨工程最早 DDL、手工完成历史、提交失败恢复 |
| 最终 github_poll 回归 | 9 项通过 |
| 最终 DDL 专项 | 4 项通过；补测公开接口与 phone 路由 |
| git diff --check | 通过 |

覆盖列重排、缺日期列、旧表头前缀、过期日期、两工程最小值、改单元格原样保留、其他暂存文件排除、非法编号/状态、dispatch 校验及 registry、review、PR 打开/合并、错误工程编号、重复运行、终态跳过、每个提醒阶段去重、完成条目不提醒、12:00 边界、quiet 跨午夜补发。

## 真实环境只读快照

命令：`interaction/bin/status threads --json`。采集时间：`2026-11-17T08:31:30.765389+00:00`。
下面逐项列出所有大项目与工程，值来自当时真实输出。另一个任务正在写 roadmap 和 projects.toml，null 表示采集时没有可解析的未结束 DDL，并不证明工程没有截止日期。

```json
[
  {
    "name": "PRTS",
    "next_ddl": null,
    "projects": [
      {
        "name": "PRTS 总控台",
        "next_ddl": null,
        "meetings": []
      },
      {
        "name": "PRTS 研究",
        "next_ddl": null,
        "meetings": []
      },
      {
        "name": "CodexBridge 微信秘书",
        "next_ddl": null,
        "meetings": []
      },
      {
        "name": "CodexBridge 秘书",
        "next_ddl": null,
        "meetings": []
      },
      {
        "name": "Codex 原理学习",
        "next_ddl": null,
        "meetings": []
      },
      {
        "name": "Ear 手机端（octopus-flutter）",
        "next_ddl": null,
        "meetings": []
      },
      {
        "name": "Ear（EchoAsRecord）",
        "next_ddl": null,
        "meetings": [
          {
            "weekday": 4,
            "start": "17:00",
            "end": "19:00"
          }
        ]
      },
      {
        "name": "DsHarness",
        "next_ddl": null,
        "meetings": []
      },
      {
        "name": "AgentConsole",
        "next_ddl": null,
        "meetings": []
      },
      {
        "name": "SpeakerLocality",
        "next_ddl": null,
        "meetings": []
      }
    ]
  },
  {
    "name": "工具与赚钱",
    "next_ddl": null,
    "projects": [
      {
        "name": "记账",
        "next_ddl": null,
        "meetings": []
      },
      {
        "name": "AIInfra 中转站",
        "next_ddl": null,
        "meetings": []
      },
      {
        "name": "lain 上的项目",
        "next_ddl": null,
        "meetings": []
      },
      {
        "name": "aquant 交易 bot / BigQuant",
        "next_ddl": null,
        "meetings": []
      }
    ]
  },
  {
    "name": "具身与果蝇脑",
    "next_ddl": null,
    "projects": [
      {
        "name": "果蝇脑 DigitalFly",
        "next_ddl": null,
        "meetings": [
          {
            "weekday": 4,
            "start": "15:00",
            "end": "17:00"
          }
        ]
      },
      {
        "name": "SomaNet",
        "next_ddl": null,
        "meetings": []
      }
    ]
  },
  {
    "name": "机器人硬件",
    "next_ddl": "2026-10-12",
    "projects": [
      {
        "name": "SwarmBot 多机器人",
        "next_ddl": null,
        "meetings": []
      },
      {
        "name": "XinDong 小车",
        "next_ddl": "2026-10-12",
        "meetings": []
      }
    ]
  },
  {
    "name": "课程",
    "next_ddl": "2026-11-30",
    "projects": [
      {
        "name": "NatureCalls（软工课 Unity）",
        "next_ddl": "2026-12-21",
        "meetings": []
      },
      {
        "name": "课程作业",
        "next_ddl": null,
        "meetings": []
      },
      {
        "name": "OS 课（rCore）",
        "next_ddl": "2026-11-30",
        "meetings": []
      }
    ]
  },
  {
    "name": "Outreach",
    "next_ddl": "2026-11-21",
    "projects": [
      {
        "name": "Outreach",
        "next_ddl": "2026-11-21",
        "meetings": []
      }
    ]
  }
]
```

## 文档和边界

更新 interaction/README.md（格式、字段、CLI、派发、PR 自动完成）、reporter/README.md（DDL/组会与 quiet）、GLOSSARY.md（路线图条目），human/README.md 增加本报告入口。
没有修改 human/roadmaps/、human/projects.toml 或 AgentConsole/；这些路径上的并行变更不纳入本次提交。

真实 GitHub 合并写回、真实手机推送均未核实，只验证了隔离命令链。现有每小时 remind 会自然使用新增逻辑；未改定时任务安装配置。
通知渠道成功至本地写入 sent 之间崩溃仍可能重复送达；无法在现有外部通知接口上实现跨系统事务。
对 roadmap 单文件提交会包含该文件已有未提交内容（不会包含其他文件），这是路径提交本身的边界。
