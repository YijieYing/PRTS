# 任务：实现 question queue `reporter/bin/ask`（给 Codex）

工作目录 `~/PRTS`（git 仓库，私有）。先读：
- `ROADMAP.md` §三-R1：已定的设计，**照它实现**；
- `GLOSSARY.md`；
- `reporter/README.md`；
- `pulse/README.md` §三：杂务提醒是第一个用户。

另一个 Codex 任务正在同时实现 `pulse/` 和 `interaction/bin/run`。**你不要改 `pulse/` 和 `interaction/`。**

## 背景
总控和其他 agent 需要一个地方攒问题，挑合适的时候、一次少量地问用户，并收回答案。
- 送达渠道（总控已决定）：一个每小时运行一次的 Claude 定时任务。它调用 `ask due --channel claude`，在 Claude 桌面和手机 app 上把问题展示给用户；用户在那个 session 里回答，session 再调用 `ask answer`。
- 你只实现命令和数据，不实现定时任务。

## 结构
- `reporter/bin/ask`：对外命令。
- `reporter/lib/questions.py`：内部实现。
- `reporter/config/questions.toml`：每批最多几条（3）、每日推送上限（blocking 每天最多推几次）、blocking 的重复提醒间隔（30 分钟）、soon 的每日汇总时间。
- `reporter/state/questions.jsonl`：**只追加的事件流**，个人数据，不进 git（检查 `reporter/.gitignore`）。
- `reporter/tests/`。

## 数据（事件流）
每条事件都有 `qid`、`t`、`event`，再加各自的字段：
- `created`：`question`、`why`、`default`、`urgency`（blocking / soon / whenever）、`source`、`dedupe`、`expires`、`project`（可选）。
- `delivered`：`channel`、`batch_size`、`batch_id`。
- `opened`：渠道能知道时才记。
- `answered`：`answer`、`via`（session / file / wechat / claude）、`latency_s`（从第一次送达算起）。
- `closed`：`outcome`，取值为 answered、deferred、delegated、rejected、expired_unseen、expired_seen、superseded。
- `default_used`、`default_ok`：后者在用户事后改了 default 时记 false。

问题的当前状态由事件折叠得出。
- `qid` 形如 `Q1`、`Q2`，递增，方便在手机上输入。
- `dedupe` 相同、还没关闭的问题，`add` 时不新建，返回已有的 qid。

## 命令
```
ask add "<问题>" --why ... --default ... --urgency blocking|soon|whenever --source <来源> --dedupe <键> [--expires ISO] [--project P]
    → 打印 qid
ask list [--open] [--json]
ask next [--max 3]        # 用户此刻在场（比如开工时）要问的那几条：先 blocking，再 soon，再 whenever，每组内先旧后新
ask due --channel claude [--now ISO]
    # 现在该推送的：blocking（距上次送达 ≥ 30 分钟）；soon（到了每日汇总时间，并且今天还没送过）
    # whenever 不推送
    # 一批最多 3 条；记 delivered；输出给人看的文字，没有就输出空并以 0 退出
    # 推送前问 `~/PRTS/pulse/bin/pulse now`：存在且返回 quiet 为 true 时，只推 blocking；命令不存在或失败就当作不 quiet
ask answer Q12 "<答案>" --via session|file|wechat|claude
ask close Q12 <outcome>
ask expire [--now ISO]    # 关掉过期的问题：送达过但没有 opened 的记 expired_unseen；有 opened 的记 expired_seen；从没送达的也记 expired_unseen
ask render                # 打印给 human/questions.md 用的视图（打开的问题、怎么回答）；不直接写 human/
ask wait Q12 [--poll 30]  # 阻塞到 Q12 有答案或被关闭，打印答案；用法同 interaction/bin/wait
```
- `due` 的输出写给手机看，要简短：每条一行「Q12 · 问题」，下面一行写「没人回答时：<default>」。最后一行写怎么回答：直接回复「Q12 你的答案」，或者「Q12 你定」（delegated，用 default）、「Q12 以后」（deferred）、「Q12 别问」（rejected）。
- 再提供 `ask reply "<用户的原话>"`：解析「Q12 …」「Q12 你定」「Q12 以后」「Q12 别问」，转成相应的 answer 或 close，`via=claude`。这样定时任务的 session 只要把用户原话交给它就行。

## 测试
- 覆盖：
  - 事件折叠；dedupe；
  - `next` 和 `due` 的排序与每批上限；
  - blocking 的重复提醒间隔；soon 的每日汇总时间；
  - quiet 时的行为（用替身的 `pulse now`）；
  - `reply` 解析中文；
  - `expire` 的 outcome；
  - `wait`；
  - `latency_s`。
- 所有测试在临时目录里跑：加环境变量 `PRTS_REPORTER_STATE`（现有的那个），不碰真实 state。子进程不能继承 stdin。
- `reporter/` 现有的测试，以及 `python3 interaction/tests/test_modules.py`，都要通过。

## 文档
在 `reporter/README.md` 加一节 ask：命令、事件、用户怎么回答。

## 不要动
`pulse/`、`interaction/`、`human/`、`memory/`、`GLOSSARY.md`、`ROADMAP.md`、根目录的 `README.md`、launchd。

## 交付
- 另一个 Codex 任务同时在这个仓库里提交：只 `git add` 你自己改的路径，不要用 `git add -A` 或 `git commit -a`；遇到 `index.lock` 就稍等再试。
- 分几次提交，每个提交只做一件事。`state/` 不进 git。
- 报告写清楚：文件、接口、测试命令和输出；「试过」和「验证过」分开写。
