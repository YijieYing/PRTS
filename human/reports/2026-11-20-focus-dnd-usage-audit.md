# 勿扰联动与每周功能使用盘点

## 改动

- `pulse focus start-dnd` 读取前 20 分钟本地 Computer History，创建 `source=dnd` 的默认 3 小时时段；有手动时段时只写 `focus/dnd.log` 并退出 0。
- `pulse focus stop --reason R` 写结束原因、时长、偏离分钟和主要去向；无时段静默退出。勿扰偏离提醒标题带「勿扰中偏离：」。
- `interaction/bin/usage-audit [--weeks N] [--json]` 只读现有状态，输出每功能每周次数、连续未用周数和候选标记。

用户需要在快捷指令中建两条个人自动化：快捷指令 → 自动化 → 新建个人自动化 → 专注模式 → 勿扰模式 → 打开时/关闭时 → 运行 Shell 脚本 → 粘贴命令 → 关闭「运行前询问」。打开命令是 `~/PRTS/pulse/bin/pulse focus start-dnd`，关闭命令是 `~/PRTS/pulse/bin/pulse focus stop --reason dnd-off`。

## 信号边界

Ear 只把 high 且出现在 `ear/handed.json` 的段算已处理；问题队列只把 delivered 后有 answered/delegated/expired 结果的题算使用；杂务提醒只计实际 `reminded=true`，现有数据不能可靠把提醒和后续回答或杂务下降关联。专注按 `focus/log.jsonl` 的开始次数计数。日报要求 `recap-sent.json` 的 `note=true` 与 `sent=true`。DDL/组会读 `ddl-sent.json`。todo 当前接口没有新增/完成时间，AgentConsole 没有稳定 server 访问日志，tokens 没有人工调用与日报调用的来源区分；报告标出这些缺口并给了最小埋点建议。系统定时运行本身不算用户使用。

## 真实状态冒烟

`pulse focus start-dnd --dry` 原文：

```json
{"goal": "专注（勿扰模式）", "on": [], "off": [], "note": "勿扰模式自动开启", "source": "dnd", "start": 1795171986.162051, "until": 1795182786.162051, "rows": [], "counts": {"on": 0, "off": 0, "unknown": 0, "away": 0}, "reminders": [], "warnings": []}
```

`usage-audit --weeks 3` 原文：

```text
Ear → 总控 inbox high 推送：0 / 11 / 0；连续未用 1 周
每小时 remind 的问题推送：0 / 1 / 0；连续未用 1 周；无信号：questions.jsonl 不存在
杂务提醒：0 / 0 / 0；连续未用 3 周 候选；无信号：没有可把提醒与用户回答或杂务下降关联的持久信号
专注时段：0 / 1 / 0；连续未用 1 周
每日回顾：0 / 0 / 4；连续未用 0 周
DDL / 组会提醒：0 / 0 / 12；连续未用 0 周
todo（Apple 提醒事项 PRTS）：0 / 0 / 0；连续未用 3 周 候选；无信号：todo 输出没有时间戳，无法计算每周新增/完成，需最小埋点建议：保存只读快照差分
AgentConsole：0 / 0 / 1；连续未用 0 周；无信号：缺少 server access log，无法统计浏览请求与改状态动作
token 统计：0 / 0 / 0；连续未用 3 周 候选；无信号：没有区分人工调用/日报调用的信号；最小埋点建议：tokens 命令写调用来源和时间
```

## 验证

- pulse tests：140 tests，OK。
- reporter tests：33 tests，OK。
- interaction run/modules/wake：3、15、shell smoke，均通过。
- 新增 focus DND fixture：14 tests，OK；usage-audit fixture：1 test，OK。

没有删除、停用或写入真实 state；冒烟使用 `--dry` 和独立临时 state。
