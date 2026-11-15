# dispatch worktree 交付报告

实现 dispatch --worktree 分支 [--base ref]、worktrees list / clean [--dry] [--all]，沙箱策略与 writable_roots 构造保持不变。未 push，未清理真实 worktree。

## 验证过

- 临时仓库测试 test_worktrees.py：6 项通过。覆盖创建、复用、非法分支、路径冲突不派发、registry 元数据、外部 worktree、无远程与显式 base、已有 worktree 当前 HEAD、干净已合并删除、未跟踪文件/未合并/未推送跳过、dry-run、squash PR 当前提交核验、branch -d 拒绝时保留分支。
- test_modules.py：15 项通过；test_run.py：3 项通过；test_github_poll.py：8 项通过；test_filter.py 单独复跑：5 项通过；test_wake.sh：PASS。运行入口均关闭 stdin，新增测试的所有子进程也关闭 stdin。
- start 事件记录实际 cwd 和 worktree 的 path / branch / repo；Codex 使用替身，真实沙箱内任务执行未核实。
- 真实仓库仅执行以下只读检查，两个退出码均为 0，stdout/stderr 均为空（默认根目录下没有发现登记工作树）：

```text
$ interaction/bin/worktrees list
[无输出]
$ interaction/bin/worktrees clean --dry
[无输出]
```

## 试过

- 首轮并发运行现有测试时 test_filter.py 的一个替身失败用例触发 1 秒超时；单独复跑全部通过。并发负载是否为原因未核实，未修改该测试或业务实现。
- 新增测试首轮因 macOS /var 与 /private/var 的规范路径差异断言失败，已统一测试临时路径后验证通过。
- GET http://127.0.0.1:7788/api/state 连接失败，未核实其他 agent 的实时状态；保留原有及其他任务改动。

## 使用与边界

worktree 统一在 ~/.worktrees/<主检出目录名>/<分支名斜杠换短横线>，可用 PRTS_WORKTREE_ROOT 覆盖。一次派发一个分支；不要让 Codex 自己创建 worktree。调用方验收合并后运行 worktrees clean，dispatch 不自动清理。

清理用本地 origin 默认分支引用或 gh merged PR 的精确头提交作为证据；不自动 fetch。主检出、锁定工作树与 detached HEAD 始终保留。所有删除仅用 git worktree remove 与 git branch -d；后者拒绝时明确报告保留分支，不强制删除。忽略文件不算改动。dispatch --dry --worktree 会准备工作树但不派发，此副作用已在文档中注明。

沿用 canonical 名称 dispatch、registry、worktrees；没有增加近义架构层，也没有旧名称需要迁移。已更新 interaction/README.md、GLOSSARY.md、human/README.md（本报告入口），并搜索检查相关用法；AGENTS.md 无行为约定需要更改。
