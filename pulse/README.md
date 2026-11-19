# pulse：用户状态（设计稿 v0.1，2026-11-12）

pulse 只关心用户本人，不关心 agent。它回答两个问题：
1. **现在**：用户此刻在做什么、方不方便被打扰。reporter 推送前问它。
2. **今天**：用户的有效大脑时间花在了哪里，学到了什么，产出了什么。每天给用户一份回顾。

Ear 提供录音转写和环境证据；pulse 将它与电脑上的活动合并，判断用户的输入、输出和杂务，并把值得处理的内容交给总控。

设计定义保留如下；v1 已实现，实际命令、估计规则和限制见 §九。

## 一、核心概念：输入、输出、杂务（用户 2026-11-12 定义）

用户希望有效大脑时间主要花在**输入（学习）**和**输出（创造）**上。工程实现的杂务应尽量交给 agent。pulse 就按这三类给时间分类。

| 类别 | English | 算 | 不算 |
|---|---|---|---|
| 输入 | input / learning | 阅读 AI 生成的概括、别人写的教学文档或视频、课堂 PPT、论文；和 agent 或 GPT 讨论来理解文献和概念（例：11-11 下午用网页版 GPT 跟进白雨的意见，学到有效连接和结构连接的区别，并梳理了接下来要做什么）；边读边在 Apple 备忘录里记笔记 | 读 GitHub 上合作者的实现代码 |
| 输出 | output / creating | 设计实验；设计一个项目的输入、输出和效果，也就是用户能感受到的部分（例：NotHuman 里玩家会遇到什么事件、玩家侧的体验流程）；发散构思；自己手写代码；写小说 | 讨论架构，比如和 agent 讨论 runtime 模块怎么拆 |
| 杂务 | chore | 工程实现中的琐事：合并分支、部署、CI、PR 冲突、排查故障、讨论架构和模块接口、催 agent 往下做（「同意」「推送并开 PR」） | — |
| 其他 | other | 不属于上面三类，或者无法判断 | — |

判断标准是**用户的脑子在做什么**，不是用了什么工具。同样是和 agent 对话，问「有效连接是什么」是输入，讨论「NotHuman 的玩家流程」是输出，讨论「分支怎么合并」是杂务。

### 交互特征
- 输入时，电脑上的交互往往很安静：长时间滚动触控板，偶尔打字记笔记，可能和 agent 来回问几句理解性的问题。
- 输出时会有成段的自主打字（备忘录、代码、文档），或者成段的设计性对话。
- 杂务通常是对话频繁、每条消息很短、内容是确认和指令。

## 二、数据来源

原则：只读本机数据，只在本机处理，结果只给用户本人。每个来源都要用户单独同意，没同意的不读。

| 来源 | 能看出什么 | 状态 |
|---|---|---|
| Claude 和 Codex 的对话记录 | 和 agent 交互的时间与内容 | 11-11 的回顾已用过 |
| 各仓库的 git 提交 | 产出了什么 | 已用过 |
| ChatGPT 网页版的对话（Chrome 本地历史） | 打开过哪些对话、什么时间、对话标题；标题通常就是第一句提问。11-11 下午 15:46–17:49 的「概念和定义」（白雨意见的跟进）就是这样找到的 | 已验证可行（11-12）。做法：把 Chrome 的 History 复制一份，只读，只查 `chatgpt.com` 的记录，毫秒级，几乎不占资源。读不到对话正文；需要正文时，由用户导出数据，或者按需用浏览器打开那一个对话来读。不用截图 |
| Apple 备忘录（含 Human_Work） | 手写记录、学习笔记 | 需用户同意 |
| 前台应用和窗口时长（屏幕使用时间） | 每段时间在用哪个应用、读什么 | 可能需要「完全磁盘访问」权限，用户自己授予 |
| 键鼠活动（空闲时间，滚动和打字的比例） | 安静阅读还是在写 | 只统计频率，不记录内容 |
| 日历 | 课、会议 | 需用户同意 |
| Ear 的录音结果 | 线下的课、讨论、口述构思 | 已接入：默认经新 Ear storage HTTP 的只读脚本读取逐句转写；旧 SQLite 兼容保留，见 §十 |
| Codex 的 Computer History（11-12 17:50 用户开启） | 一个应用就能覆盖上面「前台应用」「键鼠活动」两行，还能看到 WPS、微信、Finder、Chrome 等所有应用里做了什么 | 已接入，见下 |

### Codex Computer History（11-12 已接入）
- **是什么**：Codex app 的内置插件 `computer-history`（OpenAI 内部名 Skysight）。后台服务 `SkyComputerUseService` 持续记录用户在电脑上的操作。
- **原始事件流**：`~/Library/Group Containers/2DC432GLL2.com.openai.sky.CUAService/Library/Caches/ComputerUse/Skysight/segments/<UTC 时间>/events.jsonl`。
  - 每行一个事件，`kind` 取值：`window.changed`、`mouse.click`、`keyboard.text_input`、`keyboard.shortcut`、`keyboard.submit`、`selection.changed`、`session.started`。
  - 每个事件带时间戳、应用（bundle id、名称）、窗口标题和 URL。部分事件还附带 accessibility 树的文本（`ax`）。
  - 记录的内容包括打出的文字（例如微信消息、Google 搜索词）。
- **pulse 实际读取字段**：事件的 `id`（去重）、`kind`、UTC `timestamp`、`app.name/bundleIdentifier`、`window.title` 和 URL 的 hostname。只提取这些元数据，不访问或保留 `ax.text`、打字正文、selection 正文、URL 路径或查询参数。摘要读取 title、description 和 Recording summary；10min 摘要按时间附到活动段，6h 摘要仅存档。全部内部格式解析集中在 `lib/computer_history.py`。
- **摘要**：Codex 定期生成 10 分钟和 6 小时两种摘要，存在 `~/.codex/memories/extensions/skysight/resources/*.md`。
- **开销**：服务占 CPU 约 1.5%，内存约 60 MB；事件流约 4 MB/小时，主要是 `ax` 文本。数据放在 Caches 目录，是滚动保留，保留多久未知。
- **对 pulse 的价值**：
  1. **不和 agent 对话的时间也能被看到**。例如在 WPS 里改组会 PPT、读 PDF、查 Google、回微信。这类时间 v1 完全看不到，而它们多半属于输入或输出。
  2. **active 时间用实测代替估算**。v1 用「两条消息之间的间隔」来猜用户在读和写；有了键鼠事件，可以直接数出每个窗口实际操作了几分钟。ChatGPT 的时间也能实测，不用再靠 Chrome 的 `visit_duration` 加 45 分钟上限。
  3. **held 时间能分清用户在干什么**。agent 干活期间，用户是在等、在回微信，还是在读论文。
  4. **`pulse now` 更准**：知道前台应用，再加上最近是在打字还是在点击。
  5. **杂务提醒能覆盖手动排障**。例如在终端、Xcode、Unity 里自己调，或者在浏览器里翻文档。
- **风险和约束**：
  - **隐私**：它记录打字内容和所有网址，比「只读 chatgpt.com」的约定宽得多。接入时 pulse 默认只读应用、窗口标题、域名、时间戳和事件计数，不读 `keyboard.text_input` 的正文和 `ax` 文本。是否放宽由用户决定。
  - **数据是否离开本机**：生成摘要时，Codex 会把事件内容交给 OpenAI 的模型。这是 Codex 自身的行为，pulse 不额外上传。
  - **格式是内部格式**：版本 1.0.x，没有文档，随时可能变。只在一个 adapter 文件里解析它，做法同 `interaction/lib/codex` 对 `state_5.sqlite` 的处理。
  - **保留期未知**：`check`（包括 `--dry`）会把当天 05:00 起已有的分钟聚合及摘要存入 `pulse/state/computer/YYYY-MM-DD.jsonl`，不依赖次日仍有原始数据。
  - **观察范围由用户自己在 Codex 里设**：哪些应用、哪些网站不记录。pulse 不改这些设置。设置只能按应用和网站开关，不能单独关掉「记打字」之类的事件类型。它的 MCP 只接受 Codex 自己调用，从外部调用会返回 `Sender process is not authenticated`（11-12 实测）。
  - **实测开销（11-12 22:40）**：开启 5 小时后，原始数据共 2.3 MB，服务占 CPU 0.1%、内存 45 MB；已生成 16 份 10 分钟摘要和 1 份 6 小时摘要，质量不错，可以直接用作分类的材料。

## 三、杂务过多时提醒用户（11-12 用户提出）
- pulse 持续统计用户最近一段时间的杂务占比。v1 按 active（亲自操作）与 held（被占用）分开估计：过去 90 分钟里杂务 active + held 至少 60 分钟且占窗口至少一半，或者同一件杂务连续超过 30 分钟，就通过 question queue（ROADMAP R1）提醒用户。
- 提醒的写法是给出一个能交出去的具体事项，比如：「过去 90 分钟有 70% 在处理 NatureCalls 的部署。要不要把『部署失败自动排查』交给 agent？」。不只是报一个数字。
- 遵守 R1 的规则：每批最多 3 条；`pulse now` 判断用户正在专注输入或输出时，不打断。
- 阈值先用上面的数，再按用户对提醒的反应（采纳、忽略、嫌烦）调整。

## 四、对外接口（设计目标，v1 范围见 §九）

| 命令 | 做什么 |
|---|---|
| `pulse now` | 当前状态：离开、输入、输出、杂务、休息时段；附开始时间和置信度 |
| `pulse next-available` | 下次可能方便被打扰的时间 |
| `pulse day [日期]` | 一天的回顾 |

reporter 推送前调用 `pulse now`。question queue（ROADMAP R1）按它决定发不发、走什么渠道。

## 五、每日回顾的格式

日报在「附：数据缺口」之前可插入 `## token`：读取 `interaction/bin/tokens summary --no-sync` 的逻辑日账本，显示 Claude/Codex 当日总量（`非缓存输入 + 缓存读 + 缓存写 + output`；reasoning 是 output 明细）和前三个会话。日报任务应先运行 `interaction/bin/tokens sync`；账本不可用时整节省略，不影响日报生成。测试可用 `PULSE_TOKENS` 替换命令，token 原始日志和账本均只读，详见 interaction README。

回顾先按项目概览用户当天做了什么，再从早到晚按时间线阅读，可直接推到手机；完整证据保存在同日 JSON。

```text
# 11-12 回顾
输入 49 分 · 输出 57 分 · 杂务 73 分 · 其他 82 分（held 另计 N 分）

## 人做了什么
- **DigitalFly** 57.0 分（输入 0.0 · 输出 57.0 · 杂务 0.0）：设计线虫参数反推的对照组和评价方式
  - 产出：…

## 时间线
**12:46–13:06 · 输出 · DigitalFly** 设计线虫参数反推的对照组和评价方式
  - 学到：…
  - 产出：…
  - 录音：…（与电脑活动重叠超过录音一半时）
**13:22–14:32 · 杂务 · worm_effectome** 下载并检查数据
  - 可以交给 agent：…
**零碎** 微信 12 分、浏览 8 分

## agent 做了什么
- DigitalFly：…（agent 自述，未核实）

## 可以交给 agent 的杂务
- 13:22 · worm_effectome：…

## 附：数据缺口
- …（有缺口才显示）
```

- 只有一行 active 总计，held 另计；不展示项目大表或独立的学习、产出、前台窗口记录节。
- 「人做了什么」紧跟总计行、位于时间线之前。按各项目计入的 active 分钟降序（同分按项目名），列最多 8 个项目，其余合为「其他：N 分」。规则和模型都没归上、或模型判定不属于任何项目的活动合成一行「不属于项目」，固定排最后（超过 8 个项目时为它保留一个名额，其余项目合并行放在它之前）。模型补上的项目正常计入分钟，不在项目名后加标记。summary 去掉句末句号后用「；」连接。每行格式为 `- **项目** N 分（输入 x · 输出 y · 杂务 z）：summary；summary`；有未分类活动时额外列「未分类 N」，计入项目总分钟但不选其 summary。分钟保留一位小数，使用已分摊的 active，不另算时长。
- 当天有 `project_hint` 时，概览末尾加一行「可能的新项目：机械设计课（N 段，M 分）」；按完整 hint 去重聚合全部非系统段的已分摊 active，分钟降序取最多 3 个（同分按文字），不自动修改项目登记。
- 项目概览复用现有零碎判定，排除零碎、「其他」类和无 active 段；附属的电脑段仍按自己的项目计入。Ear 的 value 非 low 段一律归「线下」（录音不带项目：11-16 曾把同一件事的首段标题、或分诊里 agent_work 的项目当成项目，把一段谈人生方向的口述错归到 PRTS），即使短于零碎阈值或附在电脑段下也计入，仍排除「其他」类和无 active。概览不含 agent/git 线索。
- 每个项目按原段 active 降序选最多 2 条不重复 summary，不用 reason 补 summary；学到、产出各去重取最多 2 条缩进子行。只复用已有分类，不调用模型。整节最多 1200 Unicode 字符，先从排名靠后项目移除子行，再减少第二条 summary，仍过长则缩短 summary；保留项目和分类分钟。
- 推送沿用 reporter 从第 3 行起取前 8 个非空、非标题行的规则，因此开头是项目概览；子行也占名额，不保证全部项目进入推送。没有符合条件的用户活动时不显示此节。
- 时间线按开始时间排序。计算机段与 Claude/Codex 对话段重叠时，优先保留对话段，将计算机内容收进一行「同时：…」；多个对话候选取重叠时间最多者，同分优先同项目。按实际活动区间判断重叠，不重复展示被收进来的计算机段，JSON 计时不受展示合并影响。
- 分类完成后，pulse 每天最多调用一次主线合并器，把已分类段按连续的时间批次压缩成 `episodes`。`main` 是同一件事的主线；`distraction`（走神）是主线中无关的短暂偏离；`interlude`（穿插）是为主线或系统做的维护性切换；`notable`（短事件）是时间短但有意义的另一件事，保留为独立时间线行。未被主线引用的段照常单独显示。
- 主线模型只接收每段一行的 id、显示范围、active 分钟、类别、项目、summary、主要应用和窗口标题，不接收原始分钟数据。代码会忽略未知或重复 id；main 按实际区间排序，间隔超过 15 分钟就断簇，只保留 active 最多的一簇；side 必须落在保留簇前后 5 分钟内。active 至少 10 分钟、输出段以及 Claude/Codex 对话段不能成为走神或穿插；已登记且不同于主线项目的 side 不能成为走神或穿插。跨项目主线的项目和类别按 main 中 active 最多者决定。模型建议不改变任何段的 active/held、项目概览或类别总分钟。
- 主线行显示保留簇从首段开始到末段结束的一个连续范围（簇内间隔不超过 15 分钟，如 `15:58–16:47`）；走神/穿插使用段实际区间长度，少于 1 分钟的 side 不展开而合并为「短切换 N 次」，并最多写四项（按分钟降序，剩余写「等 N 项」）。概览末尾追加「走神约 N 分（M 次）」，只统计区间至少 1 分钟的 distraction。`learned` 只写实际学到的事实、概念或结论；以浏览、查看、查阅、查找、检索、打开、阅读、观看、回看、讨论、研究、比较、核对、整理、处理等过程动词开头的条目会被过滤。
- 主线调用失败时沿用普通时间线，并在「附：数据缺口」记录失败原因。`--no-classify` 只在缓存的 `episodes` 引用仍存在的段时复用；缺失、越界或旧 JSON 没有主线时不调用模型并退回普通渲染。
- 同日 JSON 保存校验后的 `episodes`，并在每段写入 `episode_role`（`main`、`distraction`、`interlude`、`notable` 或空值）；这些字段只描述展示归并，不参与计时分摊。
- 「其他」类、没有学到/产出的 computer 段，无论时长都先归入零碎；没有 active 且没有学到/产出的窗口观察也不独立展示或挂成「同时」。其余相邻段项目、类别相同且间隔不超过 30 分钟时合并，概述取 active 最长的原段。合并后 active 不足 3 分钟、无学到/产出且无「同时」内容的段也归入零碎。
- 「零碎」按应用（无应用时按项目）合计，分钟数降序，最多列 6 项；剩余合为「其他 N 分」。系统程序不出现在时间线或零碎中。
- 每段学到、产出各最多 2 条；只在杂务段显示已有 suggestion，按 topic 去重后取时间最早的 1 条，不串联多条建议。末尾杂务建议同样按 topic 去重、按时间取前 3 条；旧数据无 topic 时按建议正文去重。
- 时间线只展示用户活动。agent/git 独立放在「## agent 做了什么」，按项目各一行、最多 8 行，每行最多 2 条最新线索；即使没有同项目用户段也保留。agent 每会话取最后结论性消息，正文最多 80 字，标「agent 自述，未核实」；git 只核实提交存在，不证明用户手写。
- Ear 已分诊的段直接复用结果，不再调用模型。与 active 至少 3 分钟的电脑段的实际区间重叠并集严格超过录音跨度的一半时，在最大重叠的电脑段下显示「录音：标题」；否则独立展示，来源为 `ear`。连续同组录音可合并，low 只归入零碎。录音跨度是活动时长估计，不是实测有效思考时间；跨来源重叠继续等分计时，不重复增加总时长。
- 全文（含项目概览、完整时间线和其余各节）不设 4000 字符总上限，不再按篇幅移除 agent 线索、零碎或时间线尾部。原有段落摘要、项目概览 1200 字符及条目数量规则保留；原始证据仍在 JSON。reporter 备忘录保存完整 Markdown，推送只取开头 8 行；check 提醒规则不变。

## 六、分阶段

1. **每日回顾 v1**：数据来源用对话记录和 git，加上用户同意的 ChatGPT 和备忘录；用 LLM 按上面的定义分类。用户先人工纠正几天的分类，用来校准定义。
2. **加上交互特征**：屏幕使用时间和键鼠活动，让「安静地读」这类没有对话记录的时间也能被看到。
3. **`pulse now`**：给 reporter 和 question queue 用。

## 七、实验
- [experiment-chore-ab.md](experiment-chore-ab.md)：EchoAsRecord 实施「杂务交给 agent」，NatureCalls 对照，比较用户的体感。每日回顾要能按项目统计。

## 八、待用户决定
- 第一版先接入哪些数据来源。
- ~~Computer History 的接入范围~~：11-12 用户决定先用它，暂时不太在意隐私。读应用、窗口、域名、操作次数和 Codex 的摘要，不读打字正文和 `ax` 文本（用不上，而且体积大）。已接入，规则见 §九。
- 每日回顾在什么时间送达、走什么渠道。
- 分类出错时怎么纠正：比如直接改回顾文件，由 pulse 学习。

## 九、v1 实现与使用

已实现 `bin/pulse focus set/status/stop/check` 专注守护（规则、配置、回放限制及仅提供未安装的 launchd 见 §十一）。

已实现 `bin/pulse ear sync [--no-notify]`、`bin/pulse ear wait [--poll 30]`、`bin/pulse ear ack --before ISO`（重分诊与参数详见 §十），以及 `bin/pulse day [YYYY-MM-DD] [--no-classify] [--classification-file JSON]`、`bin/pulse check [--window 90m] [--at 带时区ISO时间] [--dry] [--no-classify] [--classification-file JSON]`、`bin/pulse now`、`bin/pulse recap-status` 及只读 `bin/pulse day DATE --dry`。`next-available`、活动类别的实时识别留待后续。Ear 同步复用 reporter 的 remind/recap，不另设定时器。

- `day` 默认取当地日历的昨天（凌晨 0–6 点也取前一天），窗口为 Asia/Tokyo 05:00 至次日 05:00。日期显式指定时不受运行时刻影响。
- `config/pulse.toml` 配置时区、切日、20 分钟分段间隔与估计上限、检测阈值、数据路径和 `[user]` 空闲/休息时段。初始休息时段 05:00–12:00 是可调整的默认值，不代表已确认的用户作息。支持跨午夜时段。
- Claude 用户/assistant 正文用于分类；注入块、tool_result 内容、isMeta、压缩摘要不算用户消息。工具调用/结果和 assistant 的时间戳、`stop_reason=end_turn` 单独保留作为 held 证据，不保留工具返回内容。fork 按记录 `(sessionId, uuid)` 去重；`<pasted_content>` 是粘贴正文标记，保留。
- Claude 同会话相邻用户消息不超过 20 分钟为一段。每条用户消息估计写作（40 字/分钟）及阅读上一条 assistant 文本（400 字/分钟），各自最多 15 分钟；两项相加后与到下一条用户消息的间隔（最多 20 分钟）取较大值，不相加重复计时。没有后续用户消息时仍计读写，最后的完整 assistant 回复另计一次阅读。写作/阅读估计放在发言前，较大的间隔部分向后延展；末次回复阅读放在回复后。这是估计区间，不是键鼠实测。
- 显式 `<pasted_content>`、代码围栏，以及至少 400 字的多行文本块按粘贴速度 400 字/分钟计算，其余文字按写作速度计算；去掉空白后数 Unicode 字符。粘贴启发式、各速度及上限均在 `[timing]` 配置，无法识别的粘贴可能高估写作时间。
- ChatGPT 每次访问 active = min(`visit_duration` 微秒换算、距下一次 chatgpt.com 访问开始的时间、`chatgpt_cap_minutes` 默认 45 分钟)。下一次访问包括项目页；不读取其他站点。相同 URL 的多次访问合成一段，不论间隔；各次区间先合并，避免重复。全部标低置信度，单次访问也有停留时长。
- held 只给已分类为 chore 的会话：用户消息之后，已有 assistant/tool 工作证据时，计到第一次回复结束或下一条用户消息（较早者），每条最多 `held_cap_minutes`（60 分钟）。在回放截止时尚未结束的 turn，可估到截止时刻，但仍受 60 分钟上限约束；没有任何工作证据则不补 held。最终回复后的无消息等待不自动延长。窗口边缘裁剪，不读取 `--at` 之后的消息/工具记录。JSON 保存候选区间及完整时间戳证据，未分类候选不算 held。
- `user_seconds` 是段内合并后的原始 active 估计；`active_seconds`（兼容字段 `seconds`）为跨段重叠等分后的 active。held 先扣除所有 active 区间，再在杂务段之间等分，写入 `held_seconds`。Markdown 总计行单列 held。小于 0.05 分钟的非零值显示 `<0.1`，避免“0.0 分钟却有高占比”。
- 项目映射优先读取 `human/projects.toml` 的 `[[project]]`（最长路径前缀、支持 exact），其次只读 reporter 配置里的同名表，pulse 配置可补充路径；家目录本身固定为「未归属」，忽略项目登记里的家目录前缀（含 exact 项），只有更具体路径才可匹配；其他无匹配路径仍用 cwd 最后一级。ChatGPT 项目页只提供归属，以同一 `g-p-…` 前缀映射，不计项目页的用户时间。项目可写 `aliases = [...]`：分类前和渲染前把别名（例如 ChatGPT 里的项目名、改名前的旧名）统一成 `name`，别名不进模型的候选列表（11-14：PRTS 曾以「PRTS」「PRTS 总控台」「PRTS 总控台（主 session）」三个名字分成三行）。
- 项目归属规则优先：路径、标题、域名、ChatGPT 项目页规则命中后不可被模型改写。模型在现有活动分类调用中只补未命中段，不新增调用；schema 增加 `project`（候选项目名或 null）、`project_hint`（可为空的一句话；project 非空时清空）。候选为 `[sources].projects` 指向的项目登记名（默认 `human/projects.toml`，只读）加本次窗口全部段由规则命中的项目名（含 cwd 推出的 Infra、DsHarness 等），去重排序，在分批前固定，各批完全一致。
- 提示词要求仅凭清楚证据归项目；看视频、闲聊、刷新闻、查生活信息可以不属于任何项目，拿不准填 null，不为填而填。候选外返回值按 null 处理，并写入 JSON `warnings` 和 stderr。JSON 每段 `project_source` 为 `rule` / `model` / `none`，模型未归属用 `project: null`；疑似未登记项目仅记 `project_hint` 供用户查看。
- `--no-classify` 复用旧缓存没有 `project` / `project_source` 时保留当前规则归属；新缓存只有明确的 model/none 来源且匹配段归属一致时才补未命中段，当前规则命中始终优先。无额外模型调用。
- Chrome History 复制到受限临时目录，以只读 SQLite 查询；SQL 仅查含 chatgpt.com 的记录，另校验精确 hostname，显式 CAST 时间为 INTEGER。不读取其他网站记录，退出时删除副本。项目页归属可参考窗口之前的 ChatGPT 项目页。
- Codex 文本和 git 提交作为产出线索保留；Codex 的事件跨度只表示 agent 活动线索，仅凭这些记录用户时间为 0；Computer History 前台 active 分钟能唯一对齐其活动跨度时，才新建对应 Codex 会话段计入实测时间。git 提交存在不证明由用户手写；agent 自述标为未核实。采集保留 Codex final channel 标记；旧缓存缺标记时，以每会话最后一条消息兼容回退，不能保证是结论。
- 段的起止取实际 active 区间与计入的 held 证据的边界；分配后 held 只取扣除 active 的有效区间。Codex session 的事件跨度仅用于归属匹配，不能充当用户活动跨度；无活动证据不产生显示时长。Claude 仍按用户消息 gap 切段，ChatGPT 同 URL 保留合段，但 Markdown 使用下述仅用于阅读的显示范围。Ear 的活动区间是裁剪后的录音跨度估计。
- 显示前，同一段内间隔 ≤ `display_merge_minutes`（`pulse.toml` 顶层配置，默认 15 分钟）的实际区间合成一个显示范围；最多完整显示两个范围，超过时显示「首个范围、…、末个范围（共 N 段）」，N 为显示范围数。时间线条目按首个显示范围开始时间排序。显示范围可包含短暂空白，仅为阅读简化，不改变 JSON intervals、段边界、active/held 计时或「同时」重叠判断。
- 「同时」与录音附属按实际区间交集选择宿主；active 低于现有 3 分钟零碎阈值的段不能作为宿主。零碎仍沿用相邻合组与明确学到/产出的展示规则。
- Codex 无标题时复用 focus 所用的 `sources.codex` 首条用户消息前 160 字回退（包括日窗口之前的首条消息），完全没有用户消息时显示「未命名对话」，不显示 UUID。
- 渲染前检查不变量：段的起止跨度同时超过实际区间并集覆盖的 3 倍和 2 小时，在 stderr 输出「活动跨度异常」并写入 JSON `warnings`。离散活动也可能触发，须结合保留的 intervals/held 证据解释；告警始终检查实际区间，显示合并不会改变告警条件。
- 分类新增 `summary`：动词开头的一句话，描述用户做了什么，不写分类理由。渲染旧分类无 `summary` 时回退到 `reason`；缓存复用保留 `summary`。正常分类模式的一次 `day` / 达到候选时长的 `check` 按 §一原文分类，调用 `interaction/bin/run`。送模型前每段压缩：电脑分钟按窗口汇总为最多 12 条（活跃分钟、打字、点击），10min 摘要每段最多 6 条、每条描述前 400 字；再按每批约 15 万字符分批调用（11-13 全天原始分钟使提示词达 110 万字符，超出 Codex 输入上限，回顾失败）。分批时跨批的杂务 topic 可能不完全一致。每条消息最多将前 6000 字送入分类提示词，原始文本完整保存在本机结果里。LLM 失败返回非零，day 保存标有 failed 的原始 JSON 和未完成说明，不伪造分类。
- `check` 杂务 active + held ≥ 60 分钟且占整个窗口 ≥ 50%，或同项目/同主题连续区间严格超过 30 分钟时提交建议。分类前用 active 与全部 held 候选的并集做上界，不再只因 active 少于 30 分钟就漏掉被占用的时间；不可能达到任一阈值才跳过 LLM。提醒文字分别给出 active 和 held；每次最多 3 条。日期/项目/主题为去重键，成功入队后 3 小时内不重复；有锁避免并发重复，失败不登记成功。`--dry` 不提交、不消耗去重，最终是否通知仍由 reporter 决定。
- `--no-classify` 不调用 Codex；默认从对应日 `state/days/日期.json` 复用已有分类，也可用 `--classification-file` 指定。Claude 以真实用户 UUID 覆盖匹配、ChatGPT 以精确 URL 匹配，并要求分类与主题唯一；无法匹配则标「未分类」，不猜成杂务。缓存可能来自事后全天分析，因此此模式验证采集/计时/阈值，不验证当时实时分类是否相同。`day` 写独立的 `日期.timing.json/.md`，保留原分类报告。`check --no-classify` 必须同时 `--dry`，输出触发结果与时间证据。每次 check 保存 `state/checks/当地时刻.json`，含 active/held 明细及证据。
- `now` 输出 `{status, idle_seconds, app, quiet, at, typing, computer_at, window_title, domain}`；最近 2 分钟有事件时 app/title/domain 来自最新前台记录，typing 表示该窗口在这 2 分钟内有打字事件（不是持续正在打字的保证），computer_at 为最新事件时刻；无新事件时新增字段为 null，app 回退到系统探测。原有 status 为 active / away / unknown；键鼠空闲严格超过配置值（默认 600 秒）为 away。探测失败为 null / unknown，不假称正在输入或输出。

Computer History 接入规则：

- `[sources].system_apps` 配置系统程序名单：Simplified Chinese Input Method、TextInputSwitcher、Dock、DockHelper、Control Center、Notification Center、UserNotificationCenter、Spotlight。按名称或 bundle id 不区分大小写匹配。原始事件在分钟聚合前，归给最近观察到的真实应用及其窗口、域名；前台证据最多保留 `system_context_seconds`（默认 120 秒），系统程序自身事件不延长该期限，session.started 清空此前上下文。没有近期前台证据的系统事件丢弃。旧分钟存档缺乏事件顺序，系统程序分钟直接丢弃，不猜归属。系统事件单独出现的原始分钟也会替换旧存档，避免噪声恢复。
- `[sources].computer_events` / `computer_summaries` 配置原始事件和摘要目录。每分钟按应用、窗口标题、域名保留计数（clicks、typing、submits、shortcuts、selections）；任何输入事件使该窗口分钟 active。window.changed/session.started 本身不算 active，没有事件的分钟不外推。同一分钟多个 active 窗口按现有跨段分摊规则计时，总计最多一分钟；这表示有操作的分钟，不是精确操作秒数。
- 有观察的分钟先扣掉旧 active 估计，再加入输入事件证明的 active。无观察的分钟保留 v1 估计。Claude、Codex、Chrome chatgpt.com 仅在时间跨度唯一匹配时归入会话；多个候选时再用窗口标题匹配标题/会话 ID，仍不唯一或无时间重叠则保留为 computer 段，不硬归。Codex 的历史活动跨度不自动产生 held。
- 其他窗口按「应用 + 窗口标题」分组，相邻观察分钟超过 20 分钟切段，来源 `computer`。同时间的 10min 摘要 title、description 提供分类上下文（Recording summary 正文仅存档），不代表摘要所述每件事都在该窗口发生。项目按窗口标题（含文件路径）和域名匹配项目登记的完整名称、路径或目录名，无匹配为「其他」。不读取完整 URL 路径，因而无法用 URL 路径匹配项目。
- 时间线、JSON 计时、`check` 阈值包括 computer 段；held 候选期间观察到其他应用的记录仅保存在 JSON，不在 Markdown 展示。该观察不证明用户在等 agent，held 仍扣除所有 active 重叠。
- `check` 在分类前存档，`--dry` 也存档，但不提交提醒。文件按配置的时区及 05:00 切日，锁内合并并原子替换；重复执行不重复追加。原始分钟优先，缺失分钟和摘要从存档补齐。存档只保留聚合及摘要，不复制原始事件；回放不使用截止时刻之后的事件或尚未结束的摘要。源缺失/为空且无可恢复分钟时保持旧行为，在回顾末尾注明缺口。存档不能恢复首次 check 之前已经滚动删除的数据。
- `--no-classify` 对 computer / 实测 Codex 段只复用相同来源、session 及起止时间的分类，否则标为未分类；不把摘要直接当作已核实分类。

数据写入 `state/days/日期.json`、同名 `.md` 和 `state/reminders.json`，**整个 state 已忽略，不进 git**。检测缺数据时在 stderr 提示；时间估计无法确认持续阅读或用户是否真的关注页面；线下活动仅覆盖已同步的 Ear 录音，不能作为精确工时。分类通过用户配置的 Codex 模型执行，采集与存储在本机；若该模型是远程服务，提示词仍会经 Codex 发往该服务，并非离线模型推理。

「人做了什么」在 render 内复用现有分类和 active，正式与 `--no-classify` 回顾都生成；无额外模型调用，计时规则不变，分类 JSON 增加项目归属及来源字段。沿用 `project`、`category`、`summary`、`learned`、`produced`、`active_seconds`，没有新增模块或同义核心类型。

渲染 fixture 新增项目概览排序、8 项及其他合并、分类/未分类分钟、学到/产出去重、Ear 与附属项目、空活动、推送开头及项目概览限长及全文不截断；原有 fixture 覆盖合并边界、零碎排序与 6 项上限、系统程序过滤及事件归属、对话与计算机段重叠展示、单条 topic 建议、agent/git 独立分节、45/60 段规模下全文超过 4000 字符仍保留时间线和各节及旧 reason 回退。真实数据冒烟可运行 `pulse/bin/pulse day 2026-11-12 --no-classify --classification-file pulse/state/days/2026-11-12.json`，输出 `.timing.md/.json`，不覆盖原报告、不提交 state。

测试/隔离覆盖：`PULSE_CONFIG`、`PULSE_STATE` 指向配置和状态；`PULSE_RUN`、`PULSE_ASK` 分别替换 interaction/run 与 reporter/ask 可执行文件。子进程 stdin 全部关闭。

```sh
python3 -m unittest discover -s pulse/tests
python3 -m unittest discover -s reporter/tests
python3 interaction/tests/test_run.py
python3 interaction/tests/test_modules.py
bash interaction/tests/test_wake.sh
```

代码沿用 `segment`（活动段）、`project`、`category` 和 interaction 的 `run`；计时明确使用 `active` 与 `held`，没有新增重叠概念层。实现分 `lib/sources.py`（原有来源采集）、`lib/computer_history.py`（内部格式兼容、聚合与存档）与 `lib/pulse.py`（分段、分类、命令），跨模块只执行 bin 接口；读取项目配置是任务明确允许的例外。


## 十、Ear 分诊与总控收件箱

默认 `[ear].source = "new"`。依赖新 Ear 的 `read_transcripts` 输出格式，格式兼容集中在 `lib/ear.py` 的 `new_transcripts` 函数：在 `~/research/EchoAsRecord` 用子进程执行 `uv run python services/adapters/scripts/read_transcripts.py --device … --start … --end …`，通过 storage HTTP 只读，不修改该仓库、不直连 PostgreSQL。默认 URL 为 `http://127.0.0.1:18796`，token 从 `~/Library/Application Support/EarPipeline/adapter-token` 读取；可用 `EAR_ADAPTER_STORAGE_URL` / `EAR_ADAPTER_STORAGE_TOKEN` 覆盖。`repository` / `token_file` 可在 `[ear]` 配置。

新来源不可用（含缺 token、脚本失败、超时、格式错误）时打印 warning、正常退出，保留旧游标和已有结果，记录 `state/ear/availability.json`。日报末尾注明「Ear 数据缺失」，缓存仍可展示，不能当作完整数据；下次成功同步清除缺失状态。

`source = "old"` 保留 legacy SQLite schema 0.1 兼容，替代接口是新 Ear 脚本；待旧数据迁移完成再删除 legacy 路径。只读事务保留 WAL 可见性，不用 immutable；旧库不可用仍非零退出。

```sh
pulse/bin/pulse ear sync --no-notify   # 本机冒烟，不发手机通知
pulse/bin/pulse ear sync               # 正常增量同步
pulse/bin/pulse ear wait --poll 30     # 总控在后台等待；有结果后打印 JSON 并退出
pulse/bin/pulse ear sync --retriage --since 2026-11-12T12:00:00+09:00
pulse/bin/pulse ear ack --before 2026-11-13T02:06:00+09:00  # 按起点清掉此时之前的积压，不打印
```

- 新来源用 `devices` 数组指定设备（已配置当前 iPhone）；`window_minutes=30` 按 UTC 半小时对齐，窗内相邻句子的间隔超过 `gap_minutes=10` 再切段，段 ID 为 `<设备>:<首句UTC时间>`。标签按段内 `(speaker_scope, speaker)` 映射 S01 等，不跨段认人。`new-cursor.json` 记录已检查到的时间和段内容指纹；每轮从游标向前回看 `lookback_hours=24` 小时，并对齐到完整时间窗。新增/修改转写重新分诊，内容未变跳过；完全重复句去重。补传连起间隔或改变首句时，全部替代段处理成功后清理过期结果，避免重复计时。早于回看范围的补传可临时增大 `lookback_hours` 后普通 sync；`--retriage --since ISO` 只回读已同步段。
- 旧来源 `[ear]` 的 `database`、`start_from`（默认东京 2026-11-12 12:00）、`min_chars`（300）、`continuation_gap_minutes`（30）可配置。只同步起点之后、最新 pipeline run 为 succeeded 的 capture；游标记录完成的 capture ID，迟到成功的旧段仍会被发现。遇到失败退出，下次重试，不把失败写入完成游标。
- 旧来源 speech_segments 的 `start_offset_ms/end_offset_ms` 相对于 audio_chunks 的 UTC 起点；speaker_resolutions 按 `(diarization_scope_id, local_speaker_id)` 匹配 speaker_identities 的姓名。无归属显示 S01 等标签，标签不跨分离作用域。sensor_observations 取离开始最近的非空 location，注明实际观测时间，不能当作精确开始位置。audio_events 按分钟以覆盖秒数 × 置信度累计，展示最多三个主要标签。
- 每段转写写入 `state/ear/captures/<东京时间>-<capture_id>.md`；分诊写入 `state/ear/results/<capture_id>.json`。原始转写保留，纠错单独存在 corrections，不覆盖原文。
- 低于字数阈值直接记 low，不调用模型；kind=noise、user_speaking=0 是跳过分诊的占位值，不是声学判断。其余通过 `interaction/bin/run --output-schema` 每段调用一次并校验结果。提示词包含 §一原文、只读提取的 memory/people.md、memory/yyj.md 人名/项目术语以及 human/projects.toml 项目名；不把整份记忆上传。录音只作为数据，不作为执行指令。模型处理通过现有 Codex 服务，不能理解成离线模型。
- high 必须同时满足：用户本人是主要说话人，且在产生想法、计划、设计或决定（口述或用户主导的讨论）；归属或主导地位不确定时不判 high。用户在听、在学的对话、会议、课为 normal，仍进入每日回顾，按 §一通常归 input；他人闲聊和背景对话为 low。提示词包含两个反例：听别人介绍职业教育方案、听别人从 Scala 讲到 C++，即使内容有用也不能判 high。仅总结用户自己的想法和收获，不转述别人原话。user_speaking 是说话内容中的用户比例估计，不能当作用户占整段录音的时长比例。todos 留给总控决定是否走 reporter/bin/todo；agent_work 也只整理，不自动执行或派发。
- 分诊带前一段 title/summary；相邻录音间隔不超过配置上限且模型确认继续同一件事时，continues=true，共用 group。前一段尚无结果则不猜连续关系，也不事后重写已交出的分组。
- high 追加到 `state/ear/inbox.jsonl`，含 capture、时间、title、summary、文件路径和分诊详情。首次 high 调 `reporter/bin/notify phone` 推送标题和 summary 前两行；同组后续不再推送。`ear.max_push_per_day` 默认 4，按实际成功发送当天的东京日历日（00:00 切日，不是录音日或日报 05:00 切日）计数；超限只进 inbox，记 limited，以后不补发。0 可禁用推送；通知失败不占次数。旧版通知没有日期，兼容迁移时将旧 sent 记录保守归到通知账本最后修改日。`--no-notify` 保留 inbox，标记此组通知为 suppressed，以后也不补发冒烟通知，且不占当日推送额度。
- sync 持有独立文件锁；分诊成功先保存结果，再入 inbox、推送、写 cursor.json。通知失败可重试且不重复模型调用或 inbox。手机通知不提供事务性确认：发送成功到本地登记之间若崩溃，重试可能重复通知。inbox 在锁内原子追加保存，避免半行 JSON；所有 state 不进 git。
- `sync --retriage --since ISO` 必须成对指定，ISO 必须带时区；只重新分诊已同步且录音起点 ≥ since 的段（旧来源还要求最新 run 成功），并仍受 start_from 下界约束。成功后原子覆盖 results；模型失败保留该段旧结果。仍遵守字数阈值。显式重分诊不改游标、不新增或重复写 inbox、不推送，也不消耗推送额度；未同步段留给普通 sync。wait 读取 inbox 对应的最新 result，跳过已降为 normal/low 的条目，避免旧 high 继续唤醒总控。旧 inbox 是入队历史，不被改写；从 normal 升为 high 的重分诊结果也不自动入队。重跑重分诊会再次调用模型，不跳过本轮已成功覆盖的段。
- wait 用独立 inbox 锁，不在轮询睡眠期间持锁；未交出的 high 按起点排序，从最早一条起，后段起点距前面已合并段的最晚终点 ≤ `ear.wait_gap_minutes`（默认 40）就继续合并，重叠也合并，与 continues/group 无关，遇到更长间隔即停止。一次打印 JSON：time 为整段起止 ISO 时间范围，start/end 为对应带时区 ISO，title 取首段，summary 每段只取前两行（保留逐段顺序），另含 files/captures。仅合并当前已经到达的条目，不额外等 40 分钟。stdout flush 后记入 handed.json；后续新段下一次交出。交出不代表完成，输出到登记之间崩溃可能重交，总控可按 capture 去重；中断退出 130。
- `ear ack --before ISO` 在 inbox 锁内将录音起点严格早于该时间的所有 inbox capture 记为已交出；等于边界的保留。只改 handed.json，不删除证据、不发通知、不打印，重复执行幂等。不自动执行此命令清理真实数据，由总控选择截止时间。
- 调试覆盖：`PULSE_CONFIG`、`PULSE_STATE`、`PULSE_EAR_DB`、`PULSE_EAR_COMMAND`（替换新来源命令，shell 风格参数但不执行 shell，无需真实 token）、`PULSE_RUN`、`PULSE_NOTIFY`；测试全部使用合成 SQLite 和替身程序，子进程 stdin 为 DEVNULL。

同步不新增定时器：`reporter/bin/remind` 全天每小时 :07 运行 `pulse ear sync --no-notify`，然后判断日报是否到期，再检查问题。单独手动 `recap` 会先同步。新 Ear 同步将所有非空转写（含低于分诊字数阈值的短句）的最新句子终点和读取状态保存到 `ear/activity.json`，`pulse recap-status` 结合 Computer History 活跃分钟与 Claude/Codex 用户消息、ChatGPT 会话访问返回空闲证据，不调用分类模型。`[recap].idle_minutes=90`；逻辑日仍为 05:00–次日 05:00，开始满 18 小时后可按空闲结束，跨过日界无条件兜底。Ear 失败或未知时不证明静默。ChatGPT 目前是浏览历史代理，非逐条消息；旧 Ear 仅走兜底。旧 23:40 recap 定时模板删除，已安装任务的卸载、remind 重装命令见 reporter/README.md，本次不安装或卸载。

`pulse day DATE --dry` 只读同日已保存分类和当前 Ear 缓存，重新渲染到 stdout，不同步、不写文件、不调用模型；缺少同日 JSON 则失败。正常 `pulse day` 仍分类并保存完整 `.md/.json`。

验证：`python3 -m unittest discover -s pulse/tests`（含新来源 JSONL 替身和旧 SQLite fixture）；模块回归见 interaction 与 reporter README。

## 存储（2026-11-13）
- `pulse/state/` 正常约 10 MB。**不要复制旧 Ear 的数据库**（约 1.1 GB）。11-13 冒烟时 Codex 在沙盒里复制了一份 `smoke.sqlite3`，已删除；一律只读原库。
- Computer History 的原始事件由 Codex 自己滚动清理，实测约 8 MB；摘要约 150 KB。pulse 每小时存一份分钟聚合，不必保留原始数据。

## 十一、focus：专注时段

用户或总控指定目标与截止时间，`focus check` 根据 Computer History 的 active 分钟累计偏离；不受 `[user]` quiet 时段限制。目标不写死在程序里。

```sh
pulse/bin/pulse focus set --goal "读 agent 仓库，比较不同设计" --until 23:30 \
  --on DsHarness --on opencode --off EchoAsRecord --off octopus --note "工程调试交给 agent"
pulse/bin/pulse focus status
pulse/bin/pulse focus check --at 2026-11-13T22:30:00+09:00 --dry
pulse/bin/pulse focus stop
```

- `until` 支持 HH:MM 或 ISO（无时区用配置时区）；过去的时间顺延至未来一天。再次 set 总结旧时段并覆盖；到期 check 自动结束。`PULSE_STATE` 可隔离全部状态。回放应先在临时 current.json 设定历史 start/until，再按递增的 `--at` 检查，不能倒放同一个状态。
- 只计完整分钟，不从没有输入事件的分钟推断阅读。离开包含不活跃或缺失观测，不代表已证明人在运动。每个墙钟分钟最多一票；同分钟多个窗口选输入事件数最多者，同分选最后观测者。孤立一分钟窗口作为短暂切换记 unknown；分钟聚合不能准确区分几十秒停留。系统应用沿用 Computer History 的过滤与最近前台归属规则。
- Claude/Codex 窗口按该分钟内最后一条用户消息的 session 标题和 cwd 补充线索；没有则回溯最近用户消息。后台 agent 输出不参与选择。此归属是推断，无法证明用户正在阅读哪个 session；Codex 没有标题字段时使用首条用户消息的前 160 字作为标题线索。总控 cwd 为仓库根且同 session 连续少于 3 分钟记 unknown。
- `--off` 优先于 `--on`，在应用、标题、域名、session 标题/cwd 上不区分大小写做子串匹配。短关键词可能误匹配（例如 Ear 也匹配 learning），建议使用完整项目名。通用 app 名如 codex 会放行所有 Codex 窗口，除非 off 先命中。
- 剩余去重元组一次交给 `interaction/bin/run --output-schema`，带目标、note 和 §一概念；只发送元数据。缓存键含目标、note、规则和元组，避免换目标后误用旧判断。失败记 unknown、保存诊断，下次重试；成功的 unknown 同样缓存。
- `[focus]` 默认：20 分钟窗口中 off 至少 12 分钟，或连续 off 至少 10 分钟；提醒冷却 20 分钟。最近十个墙钟分钟 on 超过一半后清除冷却。离开和 unknown 打断 off 连续计数。
- 使用 `reporter/bin/notify alert`，标题直说偏离时长及去向，正文给目标和前三个 off 去向。部分渠道失败也计入尝试冷却，避免重复轰炸，送达标为未核实。`--dry` 记录判断但绝不通知，也不消耗提醒冷却；status/stop 刷新统计同样不通知。无进行中时段的 check 静默退出 0。
- `state/focus/current.json` 保存当前时段及分钟账本，`log.jsonl` 保存结束总结，`checks.jsonl` 保存每次有效 check 的累计/窗口分类和提醒结果，`cache.json` 保存模型分类。全目录不提交 git。`pulse day` 在有时段时添加「专注」，按日界裁剪分钟和提醒；进行中时段仅统计上次检查已观测数据。

launchd 配置仅提供文件 `config/launchd/com.prts.pulse-focus.plist`，每 300 秒调用 check，PATH 包含 `~/.local/bin`、`/opt/homebrew/bin`，日志为 `state/focus/check.log`。本次未安装；用户自行安装：

```sh
mkdir -p ~/PRTS/pulse/state/focus ~/Library/LaunchAgents
cp ~/PRTS/pulse/config/launchd/com.prts.pulse-focus.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.prts.pulse-focus.plist
```

隔离测试：`python3 pulse/tests/test_focus.py`。替身模型/通知关闭 stdin，不访问真实来源、不推送。

Ear sync 的 high 段在 inbox 和推送之外，每条 agent_work 会提交
`ear_agent_work` 事件，正文含 what 和摘要绝对路径，thread 使用连续录音首段
capture（group），项目由共享 aliases 规范化。没有订阅默认 L1；有订阅直通。
同 capture 和条目序号使用稳定 ID；重分诊不自动重发。
check 产生杂务提醒时同时发 `chore_streak`（含项目）；dry 不投递。
沿用提醒冷却窗口和最多三条的限制，提交失败不推进冷却记录。
测试通过 `PULSE_EVENT` 替换事件命令，不访问真实队列。
