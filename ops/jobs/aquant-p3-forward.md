You are Codex in /Users/prts/Projects/aquant/.worktrees/multiday (branch research/multiday-20261021). Implement the forward repricing line registered by Claude in docs/p3_forward.json (sha256 6f4c5d9bc26a0106fabb279bc4934d29a5d1fa70b6ef133a1600f50bbcffe8e4). It must be deployable on lain before the 2026-10-22 US close (16:40 ET), so keep scope tight.

Read: AGENTS.md, docs/p2_daily.json, docs/p2_forward.json, docs/p3_costs.json, docs/p3_forward.json, src/aquant/multiday/p2/, src/aquant/multiday/p2_daily.py, src/aquant/multiday/p3/.

## Hard rules
- Never edit docs/*.json registrations or any file listed in docs/p1_forward.json / docs/p2_forward.json source_sha256. New code only, e.g. src/aquant/multiday/p3_forward.py (+ helpers under p3/ if they are not hash-listed elsewhere).
- No network downloads of its own: read the dated as-of snapshot that the P2 forward runner already wrote under outputs/research/p2-daily/forward/snapshots/<date>/ and the P2 forward ledger for that date (for LOGIT annual fit reuse). If the P2 snapshot/ledger for the session is missing, fail closed with a clear status.
- No orders, no broker calls, never write outputs/daily/, no systemd/launchd changes, no push/merge.

## Behaviour
- `python -m aquant.multiday.p3_forward`: validate its own registration (sha256 above + new docs/p3_forward_impl.json with implementation commit, committed_at and source hashes, like p2_forward.json), find the latest completed session, and if the P2 forward ledger for it exists, simulate the 7 rules forward with the P2 engine but the frozen per-ETF per-leg table from docs/p3_forward.json plus SEC fee on sells (FINRA TAF 0), for BASE and STRESS separately, $2,000 each. Same start session as P2 forward (2026-10-22), same missed-session fail-closed semantics, idempotent per date, atomic writes, output outputs/research/p3-forward/{ledger,status.json}.
- `summary(record)` returning one short Chinese line (<= 60 chars) like "P3F实测成本前向：BASE $a–$b，STRESS $c–$d".
- Tests (synthetic): cost lookup per leg/ETF and floor values taken from the frozen table; SEC fee rounding; identical signals to P2 for the same snapshot (only costs differ; with a zero-cost table the equity path equals a zero-cost P2 run); missing P2 ledger -> fail closed; idempotency; no writes under outputs/daily. Full suite + ruff pass.
- Do a dry run against a temp output dir only.
- Commit (trailer "Co-Authored-By: Codex <noreply@openai.com>"), then write docs/p3_forward_impl.json pointing at that implementation commit and commit it. Final message: implementation commit, tests, dry-run status.
