# ~/PRTS 规则（所有 agent）
- `human/`：给人看的入口，必须简短易读，人类可以直接写。产出报告时，要同步更新 `human/README.md` 里的链接。开工时先用 `git diff human/` 读取人类的修改。
- `memory/`：只由总控写。其他 agent 只读，产出写到自己的项目里。
- `ops/`：派发脚本与 job prompt。运行日志（`*.log`）不进 git。
