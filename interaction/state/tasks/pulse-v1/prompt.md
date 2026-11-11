# 任务：实现 pulse v1（每日回顾 + 杂务过长检测）（给 Codex）

工作目录 `~/PRTS`（git 仓库，私有）。先读：
- `pulse/README.md`：设计稿，**§一 输入、输出、杂务的定义是本任务的核心，原样使用**；
- `pulse/experiment-chore-ab.md`；
- `GLOSSARY.md`、`README.md`、`AGENTS.md`；
- `interaction/README.md`、`reporter/README.md`。

另一个 Codex 任务正在同时实现 `reporter/bin/ask`（question queue）。**你不要改 `reporter/`**，只按下面约定的接口调用它。测试里用替身代替它。

## 模块结构（按 GLOSSARY 的约定）
- `pulse/bin/pulse`：对外命令。
- `pulse/lib/`：内部实现。
- `pulse/config/pulse.toml`：阈值、项目映射等可调参数。
- `pulse/state/`：运行时数据。**全部是用户的个人数据，必须加进 `.gitignore`，绝不能提交。**
- `pulse/tests/`。

## 数据来源（只读本机，只在本机处理）
1. **Claude 对话**：`~/.claude/projects/*/*.jsonl`。
   - 按每条记录自带的 `sessionId` 和 `uuid` 去重：fork 出来的对话会复制原对话的历史。
   - 只取用户自己发的消息（`type=user`，`message.content` 是文本，跳过 tool_result、系统提醒、`<…>` 开头的注入）和 assistant 的文本回复。
   - session 标题和 local id 来自 `~/Library/Application Support/Claude/claude-code-sessions/**/local_*.json`（`cliSessionId`、`title`、`cwd`）。
2. **Codex 会话**：`~/.codex/sessions/YYYY/MM/DD/*.jsonl`。大多是 agent 被派出去跑的，**不算用户时间**。只用于产出列表，以及判断某段时间 agent 在替用户干活。
3. **git 提交**：`~/PRTS`、`~/PRTS/AgentConsole`、`~/research/*`、`~/Projects/*` 下的仓库，加上 `config` 里可以添加的路径。用于「产出」。
4. **ChatGPT 网页版**：把 `~/Library/Application Support/Google/Chrome/Default/History` 复制到临时文件，只读打开，**只查 `url like '%chatgpt.com%'` 的记录**（visits 联 urls：时间和标题）。查完删掉副本。
   - 其他网站的浏览记录一律不读、不存。
   - Chrome 的时间是自 1601 年起的微秒数。注意 SQLite 里 text 和 integer 比较的坑，要显式 cast。
   - 标题是「ChatGPT - <项目名>」的是项目页；其余通常是对话标题，即第一句提问。

## 命令
1. `pulse day [YYYY-MM-DD]`：默认是昨天；如果现在是 0–6 点，就是前一天。
   - 时间窗是当地日期 05:00 到次日 05:00（Asia/Tokyo），写进 config。用户常熬夜，不能以 0 点切日。
   - 把用户的活动切成**段**：同一来源、同一 session 或同一个 ChatGPT 对话、间隔不超过 20 分钟的算一段。
   - 估计每段的**用户时间**：
     - 两条用户消息之间，如果间隔不超过上限（config，默认 20 分钟），算用户在读和写；超过上限只算上限。
     - ChatGPT 按对话的首次到末次打开计，同样有上限，并标为「低置信度」。
   - 用 LLM 给每段分类：input、output、chore、other。附一句理由，并提取「学到的东西」「产出的东西」各 0–3 条。
     - **分类的提示词必须原样包含 `pulse/README.md` §一的定义表和那句「判断标准是用户的脑子在做什么」。**
     - 一天的所有段打包成一次调用，避免一段调一次。
   - 项目归属：
     - Claude 和 Codex 按 cwd 映射；映射表优先读 `~/PRTS/human/projects.toml`（周报已在用），读 reporter 的配置时只读不写；
     - ChatGPT 按「ChatGPT - <项目名>」页面或同一 `g-p-…` 前缀归属。
   - 输出：
     - `pulse/state/days/YYYY-MM-DD.json`（原始段、分类、时间）；
     - `pulse/state/days/YYYY-MM-DD.md`，格式见设计稿 §五：先给输入、输出、杂务的时间和占比，并按项目分开；再列学到的和产出的，各附时间和出处；最后列最占时间的杂务，以及能交给 agent 的具体建议；附一张时间线表（时间、项目、session 或对话、类别、一句话）。
     - 命令本身把 md 打印到 stdout。
2. `pulse check [--window 90m] [--at ISO时间] [--dry]`：检测杂务是否过多。
   - 默认看最近 90 分钟（`--at` 用于回放历史，测试和验收要用）。
   - 触发条件（写在 config 里）：窗口内用户时间里杂务占比超过 50%，且杂务至少 30 分钟；或者同一件杂务连续超过 30 分钟。
   - 为了省调用：窗口内用户时间不到 30 分钟就直接结束，不调 LLM。
   - 触发时，生成一条**能交出去的具体建议**（例：「过去 90 分钟有 70% 在处理 NatureCalls 的部署。要不要把『部署失败自动排查』交给 agent？」）。
   - 用 `--dry` 时只打印建议；否则调用 `reporter/bin/ask add` 提交（接口见下）。
   - 去重键：日期、项目、杂务主题。同一件事 3 小时内只提醒一次。
3. `pulse now`（最小版）：
   - 键鼠空闲秒数：`ioreg -c IOHIDSystem` 里的 `HIDIdleTime`；
   - 前台应用名：`lsappinfo` 或 `osascript`；
   - 状态取值：away（空闲超过 10 分钟）、active、unknown，输出 JSON。
   - 休息时段等用户属性放在 `pulse/config/pulse.toml` 的 `[user]` 一节，`now` 要读它：在休息时段内就输出 `"quiet": true`。

## LLM 调用
- 用 Codex：新增 `interaction/bin/run`，一次同步的 `codex exec`。
  - 只读沙盒，关闭 stdin；支持 `--output-schema <file>` 和 `-o <file>`；把最终回复打印到 stdout。
  - 实现放进 `interaction/lib/codex`，不要另写一套。
  - 这样只有 interaction 接触 Codex。pulse 通过 `interaction/bin/run` 调用。
- 在 `interaction/README.md` 写明这个命令。可以改 interaction，但现有接口和测试必须保持不变、全部通过。

## 和 reporter 的接口约定（对方正在实现）
```
~/PRTS/reporter/bin/ask add "<问题>" --why "<答案能解锁什么>" --default "<没人回答时怎么办>" \
    --urgency blocking|soon|whenever --source pulse --dedupe "<去重键>" [--expires <ISO>]
```
成功时打印问题 id（如 `Q12`）并以 0 退出。测试里用替身脚本记录调用，不要依赖它的真实实现。

## 测试
- 测试用 fixtures：几段假的 Claude、Codex、Chrome 数据，**不能用用户的真实数据**。LLM 调用用替身。
- 要覆盖：
  - 去重（fork 副本）；
  - 05:00 切日；
  - 用户时间估计和上限；
  - Chrome 时间换算和只查 chatgpt.com；
  - 项目归属；
  - `check` 的阈值、`--at` 回放、`--dry`、去重；
  - `now` 的输出格式。
- 现有测试全部通过：`python3 interaction/tests/test_modules.py`、`bash interaction/tests/test_wake.sh`。
- 测试的子进程不能继承调用方的 stdin（替身会读 stdin）。

## 真实数据冒烟（只在本机跑，结果不提交）
- 用 `pulse day 2026-11-11` 跑一次真实数据，结果写进 `pulse/state/`，在报告里贴出摘要。总控会拿这一天来验收。
- 已知那天的情况，供你自查：
  - 上午 10:20–12:05 是 NatureCalls 的合并和部署（杂务）；
  - 15:46–17:49 有 ChatGPT DigitalFly 项目里的「概念和定义」（输入）；
  - 21:55–23:13 是 Ear codex 基线的出题审题和试跑（偏输出，属实验设计）；
  - 22:01 是录音场景头脑风暴（输出）；
  - 22:31 是线虫和白雨讨论的整理（输入）；
  - 18:03–19:47 是排查手机录音上传（杂务）。
- 再跑 `pulse check --at 2026-11-11T19:45+09:00 --dry`，应当触发一条关于 Octopus 上传排查的提醒。

## 不要动
`reporter/`、`human/`、`memory/`、`GLOSSARY.md`、`ROADMAP.md`、根目录的 `README.md`（总控来改）、launchd、`~/.agentconsole/`。

## 交付
- 另一个 Codex 任务同时在这个仓库里提交：只 `git add` 你自己改的路径，不要用 `git add -A` 或 `git commit -a`；遇到 `index.lock` 就稍等再试。
- 分几次提交，每个提交只做一件事。`pulse/state/` 绝不进 git。
- 报告写清楚：改了哪些文件；对外接口；测试命令和输出；真实数据冒烟的摘要；「试过」和「验证过」分开写。
