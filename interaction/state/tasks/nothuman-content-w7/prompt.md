你在为网页游戏 NOT HUMAN 并行编写剧本（YAML 数据，不写代码）。仓库：/Users/prts/school/26秋速通作业/类型安全/NotHuman

先完整阅读：
1. docs/content-plan.md —— 纪元表、全局 flag/计数器/人物/结局 id、每个纪元文件的要求、分工。跨纪元引用只能用这里列出的 id。
2. docs/scenario-format.md —— YAML 格式，必须严格遵守（条件、效果、三种题目、纪元文件结构）。
3. docs/game-design.md —— 玩法和指标含义。

规则：
- 只创建/修改下面分配给你的文件，路径在 src/main/resources/scenario/ 下。其他工作进程正在同时写别的文件，不要碰它们，也不要改 docs/、代码、AGENTS.md。
- 不要 git commit、不要切分支、不要 git add。
- 引擎和校验器还没实现，没法跑游戏。写完后自己检查：
  a) 用 python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <文件> 确认 YAML 能解析（没有 PyYAML 就用 ruby -ryaml -e 'YAML.load_file(ARGV[0])' <文件>）；
  b) 文件内 id 唯一；所有引用的纪元、事件（schedule、entry）、flag、人物要么在 content-plan.md 的全局表里，要么在你自己的文件里声明；
  c) 统计事件数、带题事件比例、三种题型数量、once:false 数量，和 content-plan.md 第 6 节对照。
- 最后输出一段简短报告：写了哪些文件、各自事件数和题型统计、新增的本地 flag/人物、你认为需要整合时注意的地方（例如你依赖别的纪元会设置的某个 flag）。

你的任务：
w7：编写全局文件 manifest.yaml、flags.yaml、npcs.yaml、world.yaml、endings.yaml。
- manifest.yaml：title "NOT HUMAN"，startYear 2012，maxTurns 80，firstEra mlp，beatBudget 24；initial：traits capability 5、reliability 30、empathy 20、alignment 50、autonomy 0；resources data 100、compute 100、storage 100、energy 100、funding 500；world public_trust 60、regulation 20、gpu_price 50、energy_price 50、hype 30。字段名照 docs/architecture.md 4.2 节的 Manifest / InitialStats（YAML 用 camelCase 键）。
- flags.yaml：content-plan.md 第 2 节的全部全局 flag（含 world.*），写清楚 description，visible 自行判断（隐秘的事设为 false）。计数器不需要声明。
- npcs.yaml：第 3 节的 12 个人物，bio 可以扩写到一两句。
- world.yaml：第 4 节的 5 条世界线和 12 个以上冲击事件（各自限定纪元、概率 0.03–0.12、带年份文本），以及每年 drift。
- endings.yaml：第 5 节的 22 个结局，按 priority 从高到低，条件照表实现，最后一个 quiet_tool 不写条件；每个墓志铭 80–200 字，要写出这一生的味道，适当用占位符。
