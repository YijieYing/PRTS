已提交 `94c20af`，分支 `feat/record-actions`，工作区干净。包含指定署名；未修改主目录、重启服务或 push。

文件改动：

- `src/core/bridge_record_actions.ts`：解析、白名单、管理动作拒绝、5 条上限、未闭合块处理、预览前缀保留。
- `src/core/bridge_coordinator.ts`：执行并追加结果；自动新建直接保存；自动化不执行；恢复补发仅去块并提示。
- `src/runtime/weixin_bridge_runtime.ts`：隐藏指令块，修复跨 delta 标记及反引号去重问题。
- `src/providers/codex/plugin.ts`：普通对话注入生成指令块、信息不足先追问的提示。
- `src/i18n/index.ts`：中英文执行结果文案。
- `README.md`、`docs/usage/weixin-slash-commands.md`：说明格式、范围和限制。
- `test/core/bridge_record_actions.test.ts`、`test/core/bridge_coordinator.test.ts`、`test/runtime/weixin_bridge_runtime.test.ts`、`test/providers/codex/plugin.test.ts`：新增共 25 个测试。

对草稿的关键修正：上限改为整次回复共享；空块也删除；自动创建绕过待确认及已有记录管理分支；缺少时间的提醒不保存；补齐秘书提示和拆分标记防泄露。沿用 `RecordAction` 词汇，未新增同义层。

测试结果：

| 命令/范围 | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|
| `npm test --` 四个相关测试文件 | 244 | 65 | 23 |
| 筛选新增测试 | 25 | 0 | 0 |
| `npm test` | 514 | 96 | 34 |
| 主目录 HEAD 临时副本 `npm test` | 489 | 96 | 34 |

96 个失败名称逐项一致，包含端口监听 `EPERM`、超时及断言失败。基线通过 `git archive HEAD` 导出到 `/tmp` 运行，未在主目录执行测试。

`npx tsc -p tsconfig.json --noEmit`：没有 `src/` 或新增测试错误；存在原有 relay 测试 6 错和 examples 模块引用 6 错，与基线输出完全一致。`git diff --check` 通过。

剩余风险：尚无幂等去重；保存成功但投递失败后，用户手动重发可能产生重复记录。意图、时间理解仍依赖模型，未做线上微信实测。