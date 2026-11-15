# pulse 接入新 Ear

已实现新 Ear 逐句转写 → 时间段 → 既有分诊/inbox/R18 事件 → 日报流程，默认 source=new；source=old 保留只读 SQLite 兼容。未 push，pulse/state 不提交。

## 验证过

- fixture 使用假的 read_transcripts 命令和模型/通知/事件替身，无真实 Ear 数据或外部推送。覆盖半小时对齐、长间隔切段、scope 标签隔离、设备过滤/多设备、内容不变跳过、补句重分诊、补传跨 gap 合并后清理过期结果、回看游标、缺 token/来源不可用警告及恢复、日报缺失标记与时间线/人做了什么、项目 alias 规范化。
- reporter 替身测试验证 remind/recap 各调用一次 sync，recap 带 --no-notify，sync 失败仍继续 check/day。
- `python3 -m unittest discover -s reporter/tests`：22 项通过。
- `python3 -m unittest discover -s interaction/tests`：44 项通过（包含 gh 超时故障替身测试的预期日志）。
- `bash interaction/tests/test_wake.sh`：PASS。
- `python3 -m unittest discover -s pulse/tests`：126 项通过，含 source=old 旧测试。
- `git diff --check`：通过。
- 新测试子进程 stdin=DEVNULL；read_transcripts 与既有模型/通知/事件子进程不继承 stdin。没有新增定时器。

## 试过与未核实

- 只读连接探测 `curl --connect-timeout 2 --max-time 3 http://127.0.0.1:18796/` 失败（curl 7）。这只能说明当前沙箱无法连接，不能判断沙箱外 storage 是否关闭。
- 未在沙箱内调用真实 read_transcripts、真实分诊或真实日报；uv 缓存写入和真实数据链路未核实。没有修改 EchoAsRecord 或直连 PostgreSQL。
- 首轮 fixture 暴露了查询游标被段结束时间覆盖的问题，已修复；新 Ear 专项 5 项复测通过。另一次回归的新增测试错误地让替身返回空数据后仍断言保留旧活动，已修正 fixture 再全量运行；最终 126 项通过。

## 总控在沙箱外执行

```sh
cd ~/PRTS
pulse/bin/pulse ear sync --no-notify
pulse/bin/pulse day 2026-11-15
```

核对 sync 确实读到新段、availability.ok=true；日报的时间线和「人做了什么」包含 Ear 内容。--no-notify 沿用既有语义：不推送手机，但 high 仍入 inbox、发 R18 agent_work 事件，并将通知记 suppressed，不补推。

## 行为和边界

- new_transcripts 是唯一新格式兼容入口；设备在 pulse.toml 的 devices 数组配置。按 UTC 30 分钟窗、10 分钟 gap 切段，ID 使用设备和首句 UTC 时间，标签仅在本段/speaker_scope 内有效。
- new-cursor.json 与旧 cursor.json 分开保存，按内容指纹幂等；默认回看 24 小时，对齐完整窗口。中断后游标不推进至未完成查询末尾；替代段全部处理完成后移除过期结果。显式 --retriage 仍不推送、不入队。
- 同步不可用正常退出并 warning；日报保留已有缓存并注明「Ear 数据缺失」，缓存不代表完整数据。
- 沿用 canonical 名称 Ear、segment、capture（兼容既有落盘接口）、group，无新增同义模块。删除独立 Ear launchd 模板。通知每日额度、连续组去重和 R18 逻辑沿用原流程。
- remind 实际排程为 0 点、9–23 点第 7 分钟；recap 为 23:40。本任务没有扩展时段或安装任务。
- 文档更新：pulse/README.md（§九、§十及来源表）、reporter/README.md、GLOSSARY.md、human/README.md 报告链接；ROADMAP.md 的旧模板引用也已更新（这部分被同时工作的总控提交 f4d392d 收录，本提交不再重复）。
