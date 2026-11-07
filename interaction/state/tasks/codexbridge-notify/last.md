Committed **`cbcfaa6`** on `feat/weixin-notify` in `.worktrees/notify`. Worktree is clean. No merge, push, or service restart.

Design in five lines:

1. `Outbox` atomically stores private notification requests; CLI performs no network operations.
2. Serve polls every two seconds and reuses `DeliveryService`, chunking, acknowledgements, and retries.
3. Missing/expired context tokens leave notifications pending; inbound messages trigger delivery first.
4. Secretary fences allow `/auto add` drafts; confirmation and management remain user-only.
5. `AutomationSchedule.once` stores UTC timestamps, reports skipped past times, and pauses after exhaustion.

Existing canonical terms were retained; no parallel sender or duplicate architecture was introduced.

Validation:

| | Baseline | Final |
|---|---:|---:|
| Passed | 514 | 526 |
| Failed | 96 | 96 |
| Skipped | 34 | 34 |

Failure names match exactly; **no new failures**. Tsc also matches baseline: 6 relay-test errors plus 6 existing example-module resolution errors.

Program command, after deployment:

```bash
codexbridge weixin notify --state-dir "$HOME/.codexbridge" \
  --file /absolute/path/result.txt --title aquant
```

For this source checkout, replace `codexbridge` with `node --import tsx src/cli.ts`.

Changed files:

```text
README.md
docs/architecture/codexbridge-automation.md
docs/command-skills/auto.md
docs/usage/weixin-slash-commands.md
src/cli.ts
src/core/{automation_job_service,bridge_coordinator,bridge_record_actions,delivery_service}.ts
src/i18n/index.ts
src/platforms/weixin/{outbox,plugin}.ts
src/platforms/weixin/official/context_tokens.ts
src/providers/codex/plugin.ts
src/runtime/weixin_bridge_runtime.ts
src/types/core.ts
test/core/{automation_job_service,bridge_coordinator,bridge_record_actions}.test.ts
test/platforms/weixin/outbox.test.ts
```

Proposed wording for `secretary/AGENTS.md`—**not edited**:

> When the user requests scheduled system work and the task and timing are clear, append `/auto add <complete natural-language request>` inside a `codexbridge` fence. The bridge creates and displays a confirmation draft. Never emit `/auto confirm`, `/auto del`, or any other automation management command; the user approves the job. Preserve explicit dates, timezone, and one-shot intent. Ask for missing details, and do not claim the job is active before confirmation.