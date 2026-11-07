# AgentConsole: merge Claude desktop-app sessions by the app's own metadata

Repository: `~/PRTS/AgentConsole` (Python stdlib only, read-only toward agent data). Read `README.md` and `agent_console/scan.py` first, especially `claude_agents()` and `fold_forks()`.

## Problem (diagnosed)
The Claude desktop app stores one JSON per app session at
`~/Library/Application Support/Claude/claude-code-sessions/<a>/<b>/local_<id>.json`. Relevant fields:
- `sessionId`: the app id, `local_…`.
- `cliSessionId`: the CLI transcript currently in use, `~/.claude/projects/*/<cliSessionId>.jsonl`.
- `priorCliSessionIds`: transcripts the app used earlier for the same session. The list holds strings; tolerate dicts with an id field, too.
- `title` and `titleSource`: the title the user sees in the app. `previousTitles` holds the old titles.
- `isArchived`.

AgentConsole only scans the jsonl files. When the app moves a session onto a new transcript, the old transcript shows up as a separate row under its old title. Live example: app session `local_0d4ca8f6…`, titled "PRTS_E2 上下文压缩", has `cliSessionId` `91be3537…` and `priorCliSessionIds` `[27b8fd88…, 92dde3e1…]`. The console shows `92dde3e1` as its own dormant row, "PRTS 项目尝试", next to `91be3537`. That is the same session listed twice, once under the name it had before the rename.

The console also ignores this metadata in two other places:
- Rows whose app session has `isArchived: true` (`6a7f9f82…`, `4a01904f…`) still show as dormant.
- Titles come from `custom-title.json` or the first prompt, not from the app's title. For example, `269e2735` shows its first message, while the app calls it "PRTS 项目尝试".

## Do
1. **Read the app metadata.** In `scan.py`, read every `local_*.json` under that directory. If the directory is missing (remote hosts, Linux), do nothing. Skip a file that fails to parse; never crash the scan.
2. **Merge by app session.** For every app session, the row is its `cliSessionId` transcript. Hang each existing `priorCliSessionIds` transcript under that row the same way `fold_forks` hangs forks, labelled e.g. `（旧 transcript，app 已切换，停于 MM-DD HH:MM）`. Apply this before or together with the first-uuid fork folding, so a transcript is never both a row and a child. Prior transcripts must not be counted or shown as separate dormant rows.
3. **Titles.** Use this priority:
   1. AgentConsole's own `titles.json` override (unchanged);
   2. the app `title`;
   3. `custom-title.json`;
   4. the first prompt.
   
   Keep the existing `auto_title` and `custom` semantics consistent.
4. **Archived sessions.** If the app session is archived, mark the row `archived: true` and keep it out of the default tree and out of state counts. Check how the UI in `agent_console/static` renders states, and add the smallest toggle or filter that can still show archived rows. Archived rows must not trigger `stale` or `idle_long` events.
5. **Expose the app id.** Add `app_session_id` (`local_…`) to the agent dict so later features can link it.
6. **Tests.** Add tests with the stdlib `unittest` under `tests/`. Build a fixture with a temp HOME-like tree: an app metadata dir plus a few small jsonl files. Cover four cases:
   - prior transcripts are folded;
   - the app title wins;
   - archived rows are hidden from counts;
   - a missing metadata dir changes nothing.
   
   Make the metadata path injectable, for example through an env var or a function parameter, so the tests do not read the real `~/Library`.
7. **Docs.** Update `README.md`:
   - the 详情面板 title rule;
   - a new short paragraph next to 分叉折叠 explaining "app 切换 transcript" folding;
   - archived handling;
   - remove anything that becomes wrong.
8. **Verify against the real data.** Run the scan locally (`python3 -c` importing `scan`, or start the server on a spare port; do not stop the live launchd service) and print the Claude rows. Confirm:
   - `92dde3e1` is no longer a top-level row and sits under `91be3537`;
   - `6a7f9f82` and `4a01904f` are hidden as archived;
   - `269e2735` is titled "PRTS 项目尝试".
   
   Then scan for any other row that has the same app session as another row and report it.
9. **Commit** on the current branch with a clear message. Do not push. Do not restart the launchd service; the console will do that after review.

## Report
List the changed files, the test results, the before/after Claude row listing (id prefix, title, state, parent), and any other duplicates found.
