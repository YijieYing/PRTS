URGENT, small scope. You are Codex in /Users/prts/Projects/aquant/.worktrees/multiday (branch research/multiday-20261021). The deployed daily forward job on lain failed on 2026-10-21 16:40 ET. Claude diagnosed two causes:

1. `src/aquant/multiday/data.py::fetch` sends `end = <date>T23:59:59Z` for Alpaca SIP bars. On the free plan Alpaca returns HTTP 403 "subscription does not permit querying recent SIP data" whenever end is within the last 15 minutes or in the future, so every same-day run fails. Verified: end=2026-10-21T20:00:00Z returns 200 at 18:20 ET.
2. FRED returned its "Site Maintenance" HTML page, so DTB3 (and VIXCLS in `src/aquant/multiday/p2/data.py::fetch_vix`) failed validation.

## Fix (minimal, no research-logic change)
- Bars: end = min(<date>T23:59:59Z, now_utc - 16 minutes), formatted RFC3339 with Z. Make `now` injectable for tests. Historical runs whose date is in the past keep exactly the same request (end = <date>T23:59:59Z), so historical reproducibility is unchanged — assert this in a test.
- FRED (DTB3 and VIXCLS): retry up to 3 times with backoff; if still invalid, copy the most recent previously validated file from the latest earlier dated forward snapshot (or the base cache for DTB3) into this snapshot, and record `{"fallback": true, "source": <path>, "source_sha256": ..., "reason": ...}` in the snapshot's fetch.json / manifest. The marks remain valid because risk-free uses strictly prior observations and LOGIT already skips a day with missing VIX. If no earlier valid copy exists, keep failing closed.
- Do not change signals, costs, engine, start rules or any output format. Do not edit docs/p1_trend.json, docs/p2_daily.json, docs/p3_*.json registrations.

## Re-registration (deadline: commit before 2026-10-22 00:00 America/New_York, i.e. 13:00 JST, so the P2 first session stays 2026-10-22 and P1 first signal stays 2026-10-30)
- docs/p1_forward.json, docs/p2_forward.json, docs/p3_forward_impl.json: bump version, new implementation_commit/committed_at/source hashes, keep start rules, record the previous content in `supersedes`, add a `change_note` explaining the fix. Verify with each module's validate function that first sessions are unchanged (P1 2026-10-30 signal, P2/P3F 2026-10-22).
- Tests for end clamping (same-day vs historical), FRED fallback with flag, fail-closed without prior copy. Full suite + ruff pass.
- Do NOT run anything against outputs/daily or the production forward folders. No systemd/launchd changes, no push/merge.
- Commit with trailer "Co-Authored-By: Codex <noreply@openai.com>". Final message: implementation commit, the three new registration commits/versions, confirmed first sessions, tests.
