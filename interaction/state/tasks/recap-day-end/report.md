# 日报全文与活动结束判断

已实现，未安装/卸载 launchd，未推送真实通知或写入真实备忘录。

- 日报 Markdown 和备忘录取消 4000 字符总上限，完整保留时间线；原有段落摘要和项目概览规则保留。推送仍为开头 8 个非空、非小节标题行。
- 保留 recap、remind、pulse 的领域命名；新增 `pulse recap-status` 作为跨模块命令接口，不直接导入对方内部实现。删除旧 `com.prts.reporter-recap.plist` 模板和全文裁剪分支，没有增加同义领域层。
- 逻辑日仍为 05:00–次日 05:00；23:00 起（满 18 小时）可在连续 90 分钟无电脑活跃分钟、无用户会话交互、无 Ear 句子后提前结束；05:07 对前一逻辑日无条件兜底。全天每小时 :07 判断。只补最近已完成逻辑日，不批量补更早历史。
- `recap-sent.json` 使用锁和逐渠道收据；自动重复调用不重复已成功渠道，手动指定日期可重发并替换同名备忘录。外部通知与本地收据之间不存在跨系统事务，崩溃窗口仍可能重复；Bark/macOS 单渠道失败也可能重复成功的另一渠道。
- quiet 时所有问题暂缓，日报照常写备忘录并推送，这是按用户要求选择的行为。
- Ear 句子活动在分类前保存，短句亦阻止结束；同步不可用时不推断静默，但 05:00 兜底不受其影响。ChatGPT 目前只能复用浏览历史的会话访问，不能核实实际用户消息；采用保守代理。旧 Ear 来源缺少该静默证明，仅走兜底。

## 真实数据只读验证

运行 `reporter/bin/recap --dry 2026-11-16` 成功，输出 5707 Unicode 字符，日期标题为 `2026-11-16 回顾`。`--dry` 从保存的分类 JSON 和本地 Ear 缓存重新渲染，不调用模型、不同步、不写 state、备忘录或通知。已确认 17:49 之后的内容一直展示到 23:42。

新 Ear 远端最新转写、本机备忘录送达和实际 launchd 触发均 **未核实**；本次严格只读，没有尝试同步。总控可在沙箱外同步后再做同一预览。时间线末尾原样如下（单段原有摘要省略号仍保留）：

```markdown
**21:51–21:59 · 其他 · 线下** 疑似用户的说话人计划将一件重物从 X five 六楼搬到南区，询问能否获得搬运帮助或借用小推车。；随后到现场询问借车，遇到不便出借的情况后礼貌结束；本段未确认借到推车或完成搬运。；前面的考试闲聊和零…

**23:00–23:26 · 输入 · 线下** 前半段主要是游戏交流，无法可靠归属用户，不提取为用户想法。；后半段结合提问和向 AI 求证的习惯，推测用户是主要倾听、提问的一方，但身份仍有不确定性。；用户理解了原地转灰度会丢失彩色信息，以及读取下…
  - 学到：在原缓冲区把 RGB 转成灰度后，无法再从该缓冲区取得原来的彩色信息。
  - 学到：当前读取机制要求先释放已读取的缓冲区，再请求下一帧。

**23:26–23:29 · 输出 · XinDong 小车** 讨论芯动小车轻量视觉实验及灰度图输入是否足够。
  - 产出：轻量视觉实验的初步需求与输入选择问题
  - 产出：包含陨石图片识别、避障、对照组及灰度输入选择的实验构想

**23:28–23:42 · 其他 · 不属于项目** 在微信中输入并进行交流。
  - 录音：梳理摄像头板与核心板的分工，确认计算集中在哪里
**零碎** 录音（低价值） 259.4 分、Google Chrome 32.0 分、WeChat 29.0 分、System Settings 4.0 分、Finder 3.6 分、ChatGPT 1.4 分、其他 7.9 分
```

## 测试

最终回归全部通过：

- `python3 -m unittest discover -s pulse/tests`：130 项，73.179 秒。
- `python3 -m unittest discover -s interaction/tests`：47 项，87.651 秒，覆盖 filter、github_poll、groups、modules、run、threads、worktrees；日志中 gh 超时是失败恢复 fixture，最终结果 OK。
- `bash interaction/tests/test_wake.sh </dev/null`：PASS。
- `python3 -m unittest discover -s reporter/tests`：28 项，47.531 秒。
- `git diff --check` 通过；用 plistlib 核实 remind 模板只指定 Minute=7，旧 recap 模板已不存在。

新增 fixture 覆盖超过 4000 字符的完整时间线与全文送达、推送头部、18 小时边界、90 分钟边界、各来源活动阻止提前发送、Ear 短句、05:00 兜底、幂等、手动重跑、quiet 时仅日报发送、部分渠道失败只重试未成功渠道，以及 dry 无通知和无状态写入。

首轮 pulse 回归遇到同时进行的另一任务修改 `sources.py` 时的 import 暂态错误，其修复完成后全量通过；首轮 interaction 的 1 秒替身命令超时，单独重跑及全量重跑都通过。没有为消除这些失败放宽测试断言或改动其他任务代码。

## 文档和启用

更新 `reporter/README.md`、`pulse/README.md`、`GLOSSARY.md`，并清理 `ROADMAP.md` 中旧固定排程说明，`human/README.md` 添加本报告入口。测试子进程关闭 stdin，外发渠道及模型均用替身。

用户需执行以下操作才会更新已安装排程（本次未执行）：

```sh
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.prts.reporter-recap.plist
rm -f ~/Library/LaunchAgents/com.prts.reporter-recap.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.prts.reporter-remind.plist
cp ~/PRTS/reporter/config/launchd/com.prts.reporter-remind.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.prts.reporter-remind.plist
```

任务未加载时 bootout 可报找不到服务，继续复制和 bootstrap。旧 Claude 日报任务保持暂停。未 push。
