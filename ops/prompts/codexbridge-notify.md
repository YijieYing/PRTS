# CodexBridge: let local programs push WeChat messages, and let the secretary draft /auto jobs

Repository: `~/Projects/CodexBridge/app`. The live service runs from this checkout, on branch `fix/durable-weixin-replies`. **Work in a git worktree** (`git worktree add .worktrees/notify -b feat/weixin-notify`); `.worktrees/` is already excluded. Do not touch the main checkout and do not restart the service. Read `README.md`, `docs/usage/weixin-slash-commands.md`, `src/core/bridge_record_actions.ts` and the WeChat send and delivery code (`src/platforms/weixin/official/send.ts`, the `deliveries.json` store and its recovery) before designing. Reuse the existing vocabulary and delivery path; do not add a parallel sender.

## Why
1. **Programs cannot push.** Local programs, such as an aquant job that monitors an earnings release, have no way to push a message to the user's WeChat. The only route today is a scheduled `/auto` job that polls a file, which is clumsy and cannot react to events.
2. **The secretary cannot create jobs.** When the user asks the secretary in plain language for a scheduled job, it answers "please send this `/auto` command" (see the record-action design: only `/remind`, `/todo`, `/note` and `/log` may be emitted). The user wants the bot to act, not to hand back commands to copy.

## A. Outbound notify (main feature)
- **CLI.** `codexbridge weixin notify --state-dir <dir> (--text <TEXT> | --file <PATH>) [--scope <externalScopeId>] [--title <short label>]`. Follow the existing CLI style in `src/cli.ts`.
  - It must not log in or talk to WeChat itself, because the serve lock belongs to the running service. It only appends a request to a spool under the state dir (for example `<state-dir>/outbox/`), written atomically with mode 0600, and prints the request id.
  - With no `--scope`, use the single bound WeChat scope. Fail clearly if there are none or several.
- **Delivery.** The running `weixin serve` process picks up spool requests quickly (watch or poll within about 5 s) and delivers them through the same durable delivery and retry path that replies use. Chunk long text the way replies are chunked. Never interpret the content as commands.
- **Expired token.** WeChat only accepts sends that carry a recent context token from the user's last inbound message, valid for roughly 24 h; an expired token shows up as `ret=-2`.
  - When no usable token exists or a send fails for that reason, keep the request pending, not dropped.
  - On the next inbound message from that scope, deliver the pending notifications first, before handling the message.
  - Record clear state per request: pending, delivered, or failed with a reason.
- **Status.** `codexbridge weixin outbox --state-dir <dir>` lists recent requests and their states.
- **Bounds.** Cap the text size, for example 4000 characters per request, and reject anything larger, with a clear error. No network listener; this is local-only through the file spool.

## B. Secretary may draft `/auto` jobs
- Extend record actions so the secretary may also emit `/auto add <natural language>` (draft creation only) in the `codexbridge` fence. The bridge runs it like a user-sent `/auto add`, which already produces a confirmation draft, and shows the draft in the reply.
- `/auto confirm`, `/auto del` and every other management form stay user-only, so a person still approves every job.
- Update the developer instructions in `src/providers/codex/plugin.ts` and the record-action docs. Then propose, in your report and not by editing it, the wording change for `~/Projects/CodexBridge/secretary/AGENTS.md`; that file belongs to the console.

## C. One-shot schedules
- Add a schedule kind for one or more absolute times, for example `kind: 'once'` with ISO timestamps in UTC. After the last time has run, the job ends up completed or paused and never recurs.
- Make the `/auto` natural-language drafting able to produce it for requests like "only on 2026-10-30 at 06:15 and 07:45 Tokyo time". Times already in the past are skipped and reported in the draft.

## Tests and docs
- Add tests next to the existing ones for:
  - spool write and read;
  - delivery through the store;
  - an expired token keeping the request pending and flushing it on the next inbound message;
  - scope resolution;
  - size limit;
  - `/auto add` allowed from the fence while `/auto confirm` is rejected;
  - one-shot schedule next-run and completion.
- Run the full suite. The baseline has 96 known failures (EPERM port binding and others); report pass and fail counts against that baseline and confirm that nothing new fails. Run `tsc` and note the 6 pre-existing relay-test errors.
- Update `README.md` and `docs/usage/weixin-slash-commands.md`: add a notify section and the `once` schedule, and remove the sentence that says there is no outbound send entry, if one exists.

## Finish
- Commit on `feat/weixin-notify` in the worktree. Do not merge, push or restart; the console reviews and deploys.
- Report:
  - changed files;
  - the design in 5 lines;
  - test counts against the baseline;
  - the exact notify command for a program to use;
  - the proposed `secretary/AGENTS.md` wording.
