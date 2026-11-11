# 任务：⑥ 的可浏览数据类型改为从登记表推出，不再硬编码

## 背景

⑥（`services/api`）在 `src/ear_api/business.py` 硬编码了 `BUSINESS_TYPES`（15 类），`app.py` 的 `business_type()` 用它决定 `GET /v1/records/{type}` 等路由接受哪些类型。这份清单和 `contracts/registry/data-types.json` 重复，登记表增删类型时 ⑥ 不会跟着变。负责人已同意改为从登记表读取。

现在的 15 类恰好是：登记表里 `kind` 为 `raw_record`、`semantic`、`rule` 的类型，去掉 `plugin_management_feedback`（插件管理反馈，走管理接口，不是业务数据）。`system_record` 全部不在内。

## 要做

1. 找到 `ear_contracts` 里加载核心登记表的方式（`libs/ear_contracts/src/ear_contracts/` 中的 `Registry` 及默认/核心登记表的构造；`MemoryStorage` 默认用的那份）。用它推出业务类型集合，替换硬编码：
   - 规则：`kind ∈ {raw_record, semantic, rule}`，排除管理类型。管理类型目前只有 `plugin_management_feedback`；如果登记表或 `ear_contracts` 里已有能识别管理类型的标志，用标志；没有就在 ⑥ 里用一个命名清楚的小常量（例如 `MANAGEMENT_TYPES`）显式排除，并注释原因。不要为此修改 contracts 或 ear_contracts。
   - 来源只用**核心登记表**（随代码发布的那份），不要改成运行时从 ① 的 `/v1/registry` 拉取，也不要自动纳入动态插件类型——那是产品语义变化，未经决策。在代码注释和文档里写明这一点，作为将来的可选项。
2. 加测试：推出的集合与改动前的 15 类完全相等（把旧清单写在测试里作为回归断言）；`system_record` 类型和 `plugin_management_feedback` 不在其中；对不在集合里的类型路由仍返回 404 `not_found`。
3. 更新文档：`services/api/ai-docs/implementation.md` 第 26 行附近 `BUSINESS_TYPES（15 类）` 的描述、`services/api/README.md` 第 3.4 节相关说明（若提到类型清单）。

## 不做

- 不改 contracts、`ear_contracts`、① 的代码。
- 不改路由形状、错误码或权限行为；行为应与改动前完全一致。
## 通用要求（三个任务都适用）

- 仓库规则：先读 `AGENTS.md`、`README.md`。不填写或修改 `reviewed-by` / `reviewed-at`。不把凭据、真实录音、GPS、转写写进仓库。
- 只在当前工作目录（一个 git worktree，分支已建好）里改。**不要 commit、不要 push、不要切换分支**；改动留在工作区，由审查方提交。
- 改了行为、接口、命令、配置，就同时更新描述它们的文档（模块 `README.md`、`ai-docs/`、会变错的注释）；收尾前在仓库里搜一遍旧名称，改掉过时引用。
- 交付前运行完整检查，并在报告里贴出每一项的结果（通过数 / 失败输出）：
  `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest && uv run python tools/check_docs.py`
- 报告（last.md）用中文，写清：改了哪些文件、为什么这样改、测试结果、没做或做不到的事、发现的文档/契约/代码冲突。不确定的地方如实写，不要猜测成已完成。
