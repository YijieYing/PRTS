Implement and run the pre-registered E1 earnings-reaction study in /Users/prts/Projects/aquant. Read AGENTS.md first, then docs/e1_earnings.json (registered and committed in c474973, SHA256 3575e9863ea465c9ef48167c575d9c86d387ae2deec9b2e50493bf1a52de99c8). Follow the registration exactly; do not change thresholds, windows, costs or verdict rules. If something in it is ambiguous, write the ambiguity and your conservative resolution into the report BEFORE computing results and say so.

Inputs already built (read-only, do not overwrite):
- outputs/research/earnings/sec_dates.json (SHA256 b0769a47e335c7d9f2c34281d88c7b9c776ebe483ee9a60a256cbb21fe933047)
- outputs/research/earnings/events.json and bars.csv (daily OHLC, adjustment=all, SIP) built by scripts/ops/earnings/event_table.py. You may re-use bars.csv; if you need more history call the same Client in src/aquant/multiday/data.py (GET only).
- docs/x1_hsbc.json for the HSBC execution model; reuse existing code from the X1/P5 implementation where possible rather than re-implementing fees.

Write:
- src/aquant/earnings_study.py (pure functions + a main) and tests/test_earnings_study.py (day-0 assignment incl. pre-09:30 filings, pre-announcement exclusion, close_location, entry/exit index, one-position account logic, fee months). Run the full test suite with the multiday worktree venv: /Users/prts/Projects/aquant/.worktrees/multiday/.venv/bin/python -m pytest -q (from the repo root).
- outputs/research/earnings/e1/ : events_with_signals.csv, trades_{rule}.csv, account_{rule}_{HSBC|FRACTIONAL}.csv, report.json (all metrics in the registration, per period, BASE and STRESS, verdict per rule, git commit, input hashes).
- human/e1-earnings-2026-10-30.md : a short plain-Chinese report for a user without finance background (what was tested, table of results per rule, verdicts, what it means for a US$1,300 HSBC account in USD). Keep every failed result.
- Append the new output files with SHA256 to outputs/research/ARTIFACTS.json ONLY if that file has no uncommitted changes by someone else (check git diff); otherwise list them in the report instead.

Constraints: no orders of any kind, no paid data, do not touch outputs/daily, do not modify any file hash-listed in docs/p1_forward.json, docs/p2_forward.json, docs/p3_forward_impl.json, docs/p4_forward_impl.json. The working tree has unrelated uncommitted files from another session (configs/events, scripts/ops/event, src/aquant/event.py, tests/test_event.py, human/amazon-*.md, human/broker-architecture-*.md, human/README.md, human/direction-*.md, .gitignore, outputs/research/ARTIFACTS.json): never stage, edit or revert them. Commit only your own files (git add explicit paths), message starting "research: E1", do not push.
