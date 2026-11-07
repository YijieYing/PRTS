# ~/PRTS 规则（所有 agent）
- `human/`：给人看的入口，必须简短易读，人类可以直接写。产出报告时，要同步更新 `human/README.md` 里的链接。开工时先用 `git diff human/` 读取人类的修改。
- `memory/`：只由总控写。其他 agent 只读，产出写到自己的项目里。
- 模块结构见 `README.md` 和 `GLOSSARY.md`：每个模块分 `bin/`（对外命令）、`lib/`（内部）、`config/`、`state/`（运行时数据）。模块之间只调用对方的 `bin/`。运行日志（`*.log`）不进 git。
- `interaction/`：派发（`bin/dispatch`）、续跑、唤醒、事件队列。任务说明和报告在 `interaction/state/tasks/<任务>/`。
- `reporter/`：周报、日报、通知（`bin/notify`）。只有它对外发消息，而且只发给用户本人。
- `human/inbox.md` 只由总控写；其他代码有事要报告时，调用 `interaction/bin/event add`。
- 事件监控类任务（财报、发布、定时汇报）：列出每个需要 agent 判断的阶段，并用 `interaction/bin/wake` 给每个阶段安排唤醒时间。timer 只能跑代码，session 不会自己醒来。还没核实的结果，要在结论里写明「未核实」，不能只在数字旁边标。
