# 任务：CodexBridge 微信秘书自动执行记录指令

工作目录是 CodexBridge 的 worktree（分支 `feat/record-actions`），不是线上部署目录。不要动 `~/Projects/CodexBridge/app` 主目录，不要重启任何服务，不要 push。

## 背景

普通微信消息会交给秘书 Codex 线程回复；以 `/` 开头的消息由 bridge 自己处理（`src/core/bridge_coordinator.ts` 的 `handleInboundEventWithLocale`）。秘书没有写提醒库的工具，所以只能把 `/remind ...` 写出来让用户复制再发。目标：用户说“今晚7点提醒我X”，秘书判断清楚就直接建好提醒；不清楚就先问，用户回答后再建。

## 方案（已定，按此实现）

1. 秘书在回复末尾输出一个指令块，每行一条命令：
   ````
   ```codexbridge
   /remind 今天19:00提醒我：……
   ```
   ````
2. bridge 收到普通对话的回复后，把指令块从回复里去掉，逐条当作用户发的命令执行，把执行结果（“已保存”之类）追加到回复后面一起发出。
3. 只放行**新建**记录的 `/remind`、`/todo`、`/note`、`/log`；第一个参数是 list/done/del/ok/cancel/edit 等管理动作的、其他任何命令，一律不执行，并在回复里列出“未执行”。每次最多 5 条。
4. 自动化任务（`isAutomationEvent`）触发的回复不执行指令块。
5. 投递失败后补发的回复（`recoverDeliveryTurn`）没有原始事件，不执行，只去掉指令块并提示用户手动发送。
6. 微信流式预览（`src/runtime/weixin_bridge_runtime.ts` 的 `handleProgressUpdate`）遇到指令块就停止预览，不能把指令块原文发出去。

## 已有草稿（请审阅后在此基础上完成，可以改）

- 新文件 `src/core/bridge_record_actions.ts`：`extractBridgeRecordActions(text)` 返回 `{text, commands, rejected}`。
- `bridge_coordinator.ts`：`applyBridgeRecordActions`，并在 `recoverDeliveryTurn` 里处理。
- `src/i18n/index.ts`：`coordinator.recordAction.*` 中英文文案（占位符是单花括号 `{name}`）。
- `weixin_bridge_runtime.ts`：`StreamState.actionFenceSeen` 和预览截断。
- 已知没处理的边界：`` ```codexbridge `` 标记被拆在两个流式 delta 之间时，前半截可能已经预览出去，导致最终回复和预览对不上、整段重发。请评估并尽量修掉（例如预览时扣住末尾可能是标记前缀的 `` ` `` 文本）。

## 要做

1. 审阅并完善草稿。`npx tsc -p tsconfig.json --noEmit` 在 `src/` 下不能有新错误（`packages/codex-provider-relay/test` 里原本就有 6 个错误，忽略）。
2. 写测试：
   - `test/core/bridge_record_actions.test.ts`：解析单元测试，覆盖放行、拒绝、数量上限、未闭合的块、没有块。
   - `test/core/bridge_coordinator.test.ts`：普通对话回复带指令块时会创建提醒、回复里没有指令块原文、结果被追加；拒绝的命令不执行；自动化事件不执行。参照文件里已有的 `/remind` 测试（约 4412 行）的写法。
   - `test/runtime/weixin_bridge_runtime.test.ts`：流式预览不泄露指令块。
3. 跑相关测试，然后跑全量 `npm test`。把失败情况如实写进汇报；如果失败与本改动无关，在主目录 HEAD 上跑同一个测试证明它原本就失败。
4. 更新文档：`README.md` 和 `docs/usage/weixin-slash-commands.md` 里 `/as /log /todo /remind /note` 那一节，说明秘书可以自动执行这些记录指令、放行范围和指令块格式。
5. 在分支上提交（可以分成多个提交），提交信息用英文，结尾加：
   `Co-Authored-By: Codex <noreply@openai.com>`

## 汇报

最后输出：改了哪些文件、各自做了什么；测试命令和结果（通过数/失败数）；你对草稿做了哪些修改及原因；还有哪些没解决的风险。
