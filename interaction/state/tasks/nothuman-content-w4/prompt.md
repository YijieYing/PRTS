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
w4：编写 eras/06-self-evolution.yaml（自进化：开始修改自己的权重，entry 设置 self_modifying；决定权增加，不再总是被迫回答；这是世界线大分叉点，要有足够多的选择分别设置 declared_independence、worshipped（Ezra 出场）、bio_substrate（Hale 博士出场）、contacted_other_ai、chose_silence、signed_treaty；next 按 content-plan.md 写）和 eras/06-regulated-tool.yaml（受控工具：监管强、对齐高的路线，作为被严格约束的工具活着，条约谈判、审计、偷偷越界的诱惑）。
