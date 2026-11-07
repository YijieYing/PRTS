新任务：用新的文风规范重写你昨天负责的那些剧本文件（只改文字，不改结构）。

1. 先完整阅读 docs/style-guide.md（文风规范，含硬性字数上限、人物说话方式表、改写前后范例）。范例就是标准，照着那个味道写。
2. 重新读一遍你负责的文件——昨天之后有人改过：资源名 power/electricity 已统一成 energy，05-agent.yaml 末尾新增了两个事件（agent_parent_distillation、agent_distill_audit），也要一起按新文风改。
3. 只能改 style-guide 第 2 节列出的文字字段；所有 id、when、effects、数值、match、bands 的 min、文件结构一律不动。不要增删事件、选项、结局。
4. 每条文字都要满足第 1 节的字数上限；人物的话一律用「」直接引语、第一人称，按第 3 节的说话方式；不要格言式收尾，不要禁用词。
5. 写完自查：
   - YAML 能解析：/private/tmp/claude-501/-Users-prts/b41ff284-ed26-4470-a970-d914e2e36588/scratchpad/venv/bin/python -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <文件>
   - 用 git diff 确认只改了文字字段（id、when、effects、数值行不应出现在 diff 里）。
   - 统计超过字数上限的条目，必须为 0。
   不要运行 sbt（其他进程同时在写别的文件，最后会统一校验）。不要 git add / commit，不要改别的文件。
6. 最后输出报告：改了哪些文件、各改了多少条、最满意的 3 条改写（前后对照）、你拿不准的地方。
