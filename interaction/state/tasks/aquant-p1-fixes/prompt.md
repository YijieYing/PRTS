You are Codex working in /Users/prts/Projects/aquant/.worktrees/multiday (branch research/multiday-20261021). Claude audited your P1 work: the signals and results were independently reproduced (EW_BH and SMA10 match to 4 decimals). Now make the forward/daily path deployable. Forward tracking has NOT started (first signal 2026-10-30), so re-registering the forward implementation now is allowed; docs/p1_trend.json stays frozen (sha256 85f89261...).

## Claude decisions
1. Calendar: read-only GET of Alpaca /v2/calendar and /v2/clock through the existing `aquant.readonly.Client` (GET-only, raises on permission errors) IS allowed. It is the same access the frozen forward observer already uses. Still no order, account-mutation or any non-GET call. Add `python -m aquant.multiday.calendar_sync` that writes the raw response atomically to data/raw/multiday/calendar.json covering 2016-01-01 .. today+60 days, plus a sha256 manifest entry.
2. Historical calendar validation: compare the XNYS proxy used in P1 against the Alpaca calendar for 2016-01-04..2026-10-20. Write outputs/research/p1-trend/calendar-validation.json. If any session differs, rerun the P1 report into a NEW directory outputs/research/p1-trend-alpaca-calendar/ (keep the old one) and report whether any verdict changes. Do not change rules.
3. Reporter contract for outputs/daily/latest-wechat.txt (a watcher forwards it to WeChat):
   - first line exactly `aquant 日报 YYYY-MM-DD` (US/Eastern session date), then the market summary lines you already have;
   - whole text <= 900 characters (keep the check);
   - no secrets;
   - write every daily output (YYYY-MM-DD.md, latest-wechat.txt, ledger json) atomically: write to a temp file in the same directory, fsync, then os.replace.
4. Research progress line: read an optional single-line file outputs/daily/progress.txt (written by Claude) and use it as the 研究 line; fall back to the current default. Strip to 120 chars and drop it if it looks like a key/token.
5. Also write a human copy to human/daily/YYYY-MM-DD.md? NO — keep daily files under outputs/daily only; do not create per-day files in human/.
6. Re-register the forward implementation: new docs/p1_forward.json (version bump, new implementation_commit and source hashes, same rules/timing/costs, start rule unchanged so first signal stays 2026-10-30). Keep the old file content recorded in a `supersedes` field.

## Tests and delivery
- Tests for: header line, 900-char limit, atomic write (no partial file visible; temp cleaned), progress.txt handling, calendar_sync uses only Client.get (mock), stale-calendar refusal. Full suite + ruff must pass.
- Run calendar_sync for real once and run the validation. Do NOT run `aquant.multiday.daily` against outputs/daily (a watcher would forward it to the user's WeChat). If you want an end-to-end run, use a temp daily_dir.
- Update human/p1-trend-2026-10-21.md status/limits lines concisely (calendar validated or not, forward re-registered).
- Commit with trailer "Co-Authored-By: Codex <noreply@openai.com>". No push, no merge. Final message: calendar diff count, any verdict change, test counts, new forward implementation commit.
