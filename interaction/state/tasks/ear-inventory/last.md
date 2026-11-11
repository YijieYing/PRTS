已实现 `ear-baselines inventory [--out DIR]`，保留现有改动，未提交。**真实全集验证受沙箱阻塞，尚未生成真实索引，不能报告最终六类段数或可用总时长。**

数据库只读副本核对结果：

- 共 433 段，日期范围 **2026-07-14～2026-11-05**（上海时区）。
- 最新 run：386 succeeded、47 degraded；不能直接等同于 ready/failed。
- 数据库中没有 pending/running/waiting_retry 的 run；未验证进程实际状态。

失败原因按录音去重如下，同一段可能属于多组：

| 原因 | 段数 | 能否重跑及前提 |
|---|---:|---|
| MOSS 连接失败或超时 | 25 | 是；远端服务在线且可连接 |
| 说话人模型加载失败/锁定 | 18 | 不确定；先修复模型路径、依赖并恢复可用 |
| `embedding_provenance` 字段校验失败 | 4 | 不确定；先修复输出字段兼容性 |
| 环境声检测超过 120 秒 | 1 | 是；先确认 PANNs、资源和超时配置 |

修复后使用 `POST /api/recordings/reprocess`，请求体为 `instance_id`、`record_id`，需要管理权限和完整 Brain 源素材。`analysis-rerun` 无法修复感知失败。未执行任何重跑。

分类保留了不确定性：48 小时无进展仅判“疑似卡住”；数据库失败、音频无法探测、Evidence 与数据库 run 不一致会阻止 ready，即使 `readiness` 返回 Ready。未入库文件的推定时间也注明来源。

改动包括：

- 新增 `inventory.py`、`tests/test_inventory.py`。
- 在 `__main__.py` 注册命令。
- 更新实验 README 和 `ai-docs/implementation.md`。
- 移除同时出现的 `player.py` 中一个无效 lint 忽略注释。
- 沿用 `inventory`、`Capture`、`readiness`，未引入重复概念；未改审核字段。

检查结果：ruff、格式、pyright、文档检查及 `--base origin/dev` 均通过；pytest **376 通过、1 错误**，其中 inventory 13 项全通过。错误来自既有 HTTP 测试被禁止绑定 localhost。

真实命令已执行，但连接旧 Ear 返回 `Operation not permitted`。当前环境禁止本机网络且不允许提权，因此真实盘点和全部检查通过这两项仍未完成。