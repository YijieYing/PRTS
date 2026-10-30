# ~/PRTS 规则（所有 agent）
- `human/`：给人看的入口，必须简短易读，人类可以直接写。产出报告时，要同步更新 `human/README.md` 里的链接。开工时先用 `git diff human/` 读取人类的修改。
- `memory/`：只由总控写。其他 agent 只读，产出写到自己的项目里。
- `ops/`：派发脚本与 job prompt。运行日志（`*.log`）不进 git。
- 事件监控类任务（财报、发布、定时汇报）：列出每个需要 agent 判断的阶段，并用 `ops/wake.sh` 给每个阶段安排唤醒时间。timer 只能跑代码，session 不会自己醒来。还没核实的结果，要在结论里写明「未核实」，不能只在数字旁边标。
