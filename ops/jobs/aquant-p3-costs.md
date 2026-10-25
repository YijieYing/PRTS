You are Codex implementing aquant research P3 in /Users/prts/Projects/aquant/.worktrees/multiday (branch research/multiday-20261021). Claude is the decision layer and will independently audit.

Read first: AGENTS.md, CLAUDE.md, docs/multiday.json, docs/p1_trend.json, docs/p2_daily.json, docs/p3_costs.json, human/p3-costs-2026-10-21.md, outputs/research/p2-daily/report.md, and src/aquant/multiday/ (incl. p2/).

## Hard rules
- docs/p3_costs.json frozen: sha256 f5c4a35c4b1a6ff6fabbca5d4b6142ee4d65f44369cbc4bf88e50a00bc6ca463. Also keep p1_trend.json (85f89261...) and p2_daily.json (e91c91e5...) unchanged. Ambiguities: most literal reading, list under "deviations", never change rules after seeing results.
- Do NOT modify any file listed in docs/p1_forward.json or docs/p2_forward.json `source_sha256` (both forward lines are deployed on lain and hash-checked). New code goes in new modules, e.g. src/aquant/multiday/p3/.
- GET-only market data via existing read-only clients; no orders, no account endpoints, no paid data. Respect Alpaca rate limits (stay under 150 requests/min, back off on 429). Never print or commit credentials.
- Do not write to outputs/daily/. No launchd/systemd changes. No push/merge/history rewrite. Keep all results.

## Order of work (the order matters)
1. Generate the sample-day list exactly per part_A.sample_days from the cached Alpaca calendar (data/raw/multiday/calendar.json); exclude early-close days (close != 16:00 ET) and log them. Write docs/p3_sample_days.json and COMMIT it before downloading any quote.
2. Check Alpaca public docs (web, read only) for fractional-share support of market DAY vs OPG/CLS time-in-force, and current SEC Section 31 / FINRA TAF rates. Record URLs and findings.
3. Download SIP quotes for the 27 ETFs at the registered instants (small windows, e.g. start=instant, end=instant+10s, limit small, single symbol per request), cache under data/raw/multiday/p3-quotes/ with sha256 manifest. Apply the registered validity filter. Missing stays missing.
4. Compute part A measures; write outputs/research/p3-costs/costs.json + costs.md (per ETF x execution type: n, missing, median, p75, by year; size check; IEX vs SIP cross-check using the forward observer's recorded IEX quotes in /Users/prts/Projects/aquant/outputs/research/forward_observations/state.sqlite3 opened read-only, only if easily available; fee rates and sources; docs finding).
5. Part B rerun of the 7 P2 primaries with the measured per-ETF cost model exactly as registered (reuse saved P2 LOGIT fits/probabilities; do not refit), periods development/validation/holdout/full, BASE and STRESS, per-year-cost sensitivity, whole-share sensitivity, and side-by-side flat 5 bp P2 numbers. Verdicts with P2 gates. DSR N=114 (global variance unavailable -> N/A as in P2, conditional diagnostic only). Append 7 trials to outputs/research/trial_ledger.jsonl. Write outputs/research/p3-costs/rerun/report.json + report.md.
6. Tests (synthetic): sample-day generation reproducible from seed; validity filter; slippage sign conventions; cost model applied to the right legs (open buy/open sell/close buy) plus sell-side fees; whole-share rounding; ledger reconciliation. Full suite + ruff pass.
7. Human doc: concise "结果" section in human/p3-costs-2026-10-21.md (cost table summary: median/p75 open and close cost for SPY, QQQ, IWM and the cross-ETF median; the 7 trials at measured BASE vs flat 5 bp; verdicts; USD drawdown/worst 5-day on $2,000; honest limits incl. result-motivated re-examination). Update status line and README row.
8. Commit in logical commits with trailer "Co-Authored-By: Codex <noreply@openai.com>". Final message: per-ETF cost headline, verdict changes vs P2, tests, deviations, anything Claude must decide.
