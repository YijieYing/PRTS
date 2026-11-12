# pulse：用户状态（设计稿 v0.1，2026-11-12）

pulse 只关心用户本人，不关心 agent。它回答两个问题：
1. **现在**：用户此刻在做什么、方不方便被打扰。reporter 推送前问它。
2. **今天**：用户的有效大脑时间花在了哪里，学到了什么，产出了什么。每天给用户一份回顾。

和 Ear 的区别：Ear 从录音里总结线下发生过的事；pulse 看的是用户在电脑上的工作状态。

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
| Ear 的录音结果 | 线下的课、讨论 | 以后再接 |
| Codex 的 Computer History（11-12 17:50 用户开启） | 一个应用就能覆盖上面「前台应用」「键鼠活动」两行，还能看到 WPS、微信、Finder、Chrome 等所有应用里做了什么 | 已查看，还没接入，见下 |

### Codex Computer History（11-12 查看）
- **是什么**：Codex app 的内置插件 `computer-history`（OpenAI 内部名 Skysight）。后台服务 `SkyComputerUseService` 持续记录用户在电脑上的操作。
- **原始事件流**：`~/Library/Group Containers/2DC432GLL2.com.openai.sky.CUAService/Library/Caches/ComputerUse/Skysight/segments/<UTC 时间>/events.jsonl`。
  - 每行一个事件，`kind` 取值：`window.changed`、`mouse.click`、`keyboard.text_input`、`keyboard.shortcut`、`keyboard.submit`、`selection.changed`、`session.started`。
  - 每个事件带时间戳、应用（bundle id、名称）、窗口标题和 URL。部分事件还附带 accessibility 树的文本（`ax`）。
  - 记录的内容包括打出的文字（例如微信消息、Google 搜索词）。
- **摘要**：Codex 定期生成 10 分钟和 6 小时两种摘要，存在 `~/.codex/memories/extensions/skysight/resources/*.md`（刚开启时还是空的）。
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
  - **保留期未知**：pulse 可能需要每小时在 `check` 时把当天的聚合结果（每分钟的前台应用和操作次数）存进 `pulse/state/`，不能只靠第二天去读原始数据。
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

第一版按 11-11 那份回顾的格式，改进三点：
1. 先给结论：输入、输出、杂务各花了多少时间。
2. **学到的东西**和**产出的东西**单独成节，每条附时间和出处。这是用户最想记住的部分。
3. 列出占用用户时间最多的杂务，并给建议：哪些以后可以完全交给 agent，不用用户参与。

## 六、分阶段

1. **每日回顾 v1**：数据来源用对话记录和 git，加上用户同意的 ChatGPT 和备忘录；用 LLM 按上面的定义分类。用户先人工纠正几天的分类，用来校准定义。
2. **加上交互特征**：屏幕使用时间和键鼠活动，让「安静地读」这类没有对话记录的时间也能被看到。
3. **`pulse now`**：给 reporter 和 question queue 用。

## 七、实验
- [experiment-chore-ab.md](experiment-chore-ab.md)：EchoAsRecord 实施「杂务交给 agent」，NatureCalls 对照，比较用户的体感。每日回顾要能按项目统计。

## 八、待用户决定
- 第一版先接入哪些数据来源。
- ~~Computer History 的接入范围~~：11-12 用户决定先用它，暂时不太在意隐私。读应用、窗口、域名、操作次数和 Codex 的摘要，不读打字正文和 `ax` 文本（用不上，而且体积大）。接入已派给 Codex（任务 `pulse-computer-history`）。
- 每日回顾在什么时间送达、走什么渠道。
- 分类出错时怎么纠正：比如直接改回顾文件，由 pulse 学习。

## 九、v1 实现与使用

已实现 `bin/pulse day [YYYY-MM-DD] [--no-classify] [--classification-file JSON]`、`bin/pulse check [--window 90m] [--at 带时区ISO时间] [--dry] [--no-classify] [--classification-file JSON]`、`bin/pulse now`。`next-available`、活动类别的实时识别、定时调度留待后续。

- `day` 默认取当地日历的昨天（凌晨 0–6 点也取前一天），窗口为 Asia/Tokyo 05:00 至次日 05:00。日期显式指定时不受运行时刻影响。
- `config/pulse.toml` 配置时区、切日、20 分钟分段间隔与估计上限、检测阈值、数据路径和 `[user]` 空闲/休息时段。初始休息时段 05:00–12:00 是可调整的默认值，不代表已确认的用户作息。支持跨午夜时段。
- Claude 用户/assistant 正文用于分类；注入块、tool_result 内容、isMeta、压缩摘要不算用户消息。工具调用/结果和 assistant 的时间戳、`stop_reason=end_turn` 单独保留作为 held 证据，不保留工具返回内容。fork 按记录 `(sessionId, uuid)` 去重；`<pasted_content>` 是粘贴正文标记，保留。
- Claude 同会话相邻用户消息不超过 20 分钟为一段。每条用户消息估计写作（40 字/分钟）及阅读上一条 assistant 文本（400 字/分钟），各自最多 15 分钟；两项相加后与到下一条用户消息的间隔（最多 20 分钟）取较大值，不相加重复计时。没有后续用户消息时仍计读写，最后的完整 assistant 回复另计一次阅读。写作/阅读估计放在发言前，较大的间隔部分向后延展；末次回复阅读放在回复后。这是估计区间，不是键鼠实测。
- 显式 `<pasted_content>`、代码围栏，以及至少 400 字的多行文本块按粘贴速度 400 字/分钟计算，其余文字按写作速度计算；去掉空白后数 Unicode 字符。粘贴启发式、各速度及上限均在 `[timing]` 配置，无法识别的粘贴可能高估写作时间。
- ChatGPT 每次访问 active = min(`visit_duration` 微秒换算、距下一次 chatgpt.com 访问开始的时间、`chatgpt_cap_minutes` 默认 45 分钟)。下一次访问包括项目页；不读取其他站点。相同 URL 的多次访问合成一段，不论间隔；各次区间先合并，避免重复。全部标低置信度，单次访问也有停留时长。
- held 只给已分类为 chore 的会话：用户消息之后，已有 assistant/tool 工作证据时，计到第一次回复结束或下一条用户消息（较早者），每条最多 `held_cap_minutes`（60 分钟）。在回放截止时尚未结束的 turn，可估到截止时刻，但仍受 60 分钟上限约束；没有任何工作证据则不补 held。最终回复后的无消息等待不自动延长。窗口边缘裁剪，不读取 `--at` 之后的消息/工具记录。JSON 保存候选区间及完整时间戳证据，未分类候选不算 held。
- `user_seconds` 是段内合并后的原始 active 估计；`active_seconds`（兼容字段 `seconds`）为跨段重叠等分后的 active。held 先扣除所有 active 区间，再在杂务段之间等分，写入 `held_seconds`。总表/项目表单列 held，active 占比的分母只含 active。小于 0.05 分钟的非零值显示 `<0.1`，避免“0.0 分钟却有高占比”；项目括号百分比以该项目的 active 为分母。
- 项目映射优先读取 `human/projects.toml` 的 `[[project]]`（最长路径前缀、支持 exact），其次只读 reporter 配置里的同名表，pulse 配置可补充路径；家目录本身固定为「未归属」，忽略项目登记里的家目录前缀（含 exact 项），只有更具体路径才可匹配；其他无匹配路径仍用 cwd 最后一级。ChatGPT 项目页只提供归属，以同一 `g-p-…` 前缀映射，不计项目页的用户时间。
- Chrome History 复制到受限临时目录，以只读 SQLite 查询；SQL 仅查含 chatgpt.com 的记录，另校验精确 hostname，显式 CAST 时间为 INTEGER。不读取其他网站记录，退出时删除副本。项目页归属可参考窗口之前的 ChatGPT 项目页。
- Codex 文本和 git 提交作为产出线索保留；Codex 的事件跨度只表示 agent 活动线索，用户时间恒为 0。git 提交存在不证明由用户手写；agent 自述标为未核实。
- 正常分类模式的一次 `day` / 达到候选时长的 `check` 只调用一次 `interaction/bin/run`，按 §一原文分类。每条消息最多将前 6000 字送入分类提示词，原始文本完整保存在本机结果里。LLM 失败返回非零，day 保存标有 failed 的原始 JSON 和未完成说明，不伪造分类。
- `check` 杂务 active + held ≥ 60 分钟且占整个窗口 ≥ 50%，或同项目/同主题连续区间严格超过 30 分钟时提交建议。分类前用 active 与全部 held 候选的并集做上界，不再只因 active 少于 30 分钟就漏掉被占用的时间；不可能达到任一阈值才跳过 LLM。提醒文字分别给出 active 和 held；每次最多 3 条。日期/项目/主题为去重键，成功入队后 3 小时内不重复；有锁避免并发重复，失败不登记成功。`--dry` 不提交、不消耗去重，最终是否通知仍由 reporter 决定。
- `--no-classify` 不调用 Codex；默认从对应日 `state/days/日期.json` 复用已有分类，也可用 `--classification-file` 指定。Claude 以真实用户 UUID 覆盖匹配、ChatGPT 以精确 URL 匹配，并要求分类与主题唯一；无法匹配则标「未分类」，不猜成杂务。缓存可能来自事后全天分析，因此此模式验证采集/计时/阈值，不验证当时实时分类是否相同。`day` 写独立的 `日期.timing.json/.md`，保留原分类报告。`check --no-classify` 必须同时 `--dry`，输出触发结果与时间证据。每次 check 保存 `state/checks/当地时刻.json`，含 active/held 明细及证据。
- `now` 输出 `{status, idle_seconds, app, quiet, at}`，status 为 active / away / unknown；键鼠空闲严格超过配置值（默认 600 秒）为 away。探测失败为 null / unknown，不假称正在输入或输出。

数据写入 `state/days/日期.json`、同名 `.md` 和 `state/reminders.json`，**整个 state 已忽略，不进 git**。检测缺数据时在 stderr 提示；时间估计无法观察持续阅读、线下活动或用户是否真的关注页面，不能作为精确工时。分类通过用户配置的 Codex 模型执行，采集与存储在本机；若该模型是远程服务，提示词仍会经 Codex 发往该服务，并非离线模型推理。

测试/隔离覆盖：`PULSE_CONFIG`、`PULSE_STATE` 指向配置和状态；`PULSE_RUN`、`PULSE_ASK` 分别替换 interaction/run 与 reporter/ask 可执行文件。子进程 stdin 全部关闭。

```sh
python3 pulse/tests/test_pulse.py
python3 interaction/tests/test_run.py
python3 interaction/tests/test_modules.py
bash interaction/tests/test_wake.sh
```

代码沿用 `segment`（活动段）、`project`、`category` 和 interaction 的 `run`；计时明确使用 `active` 与 `held`，没有新增重叠概念层。实现分 `lib/sources.py`（采集）与 `lib/pulse.py`（分段、分类、命令），跨模块只执行 bin 接口；读取项目配置是任务明确允许的例外。
