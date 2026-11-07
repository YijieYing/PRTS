You are Codex implementing aquant research P4 in /Users/prts/Projects/aquant/.worktrees/multiday (branch research/multiday-20261021). Claude is the decision layer and will independently audit.

Read first: AGENTS.md, CLAUDE.md, docs/multiday.json, docs/p2_daily.json, docs/p3_forward.json, docs/p4_relative.json, human/p4-relative-2026-10-22.md, and src/aquant/multiday/ (p2/, p3/).

## Hard rules
- docs/p4_relative.json is frozen: sha256 542355f97590b09f554c4f2d4e0443d782165f1fb4a5bd0f6608dc9907d98515. Keep all other docs/*.json registrations unchanged. Ambiguities: most literal reading, list under "deviations"; never change rules after seeing results.
- Do NOT modify any file hash-listed in docs/p1_forward.json, docs/p2_forward.json or docs/p3_forward_impl.json (all deployed on lain). New code in new modules, e.g. src/aquant/multiday/p4/.
- Reuse cached data (bars, calendar, DTB3, VIXCLS). No orders, no non-GET calls, no paid data, never write outputs/daily/, no systemd/launchd, no push/merge. Keep all results.

## Tasks
1. Engine: reuse the P2 episode simulator and the P3 per-ETF per-leg cost plumbing with the frozen BASE/STRESS table from docs/p3_forward.json plus SEC fee; flat 3 bp sensitivity.
2. Definitions exactly as registered (rel_k, dispersion D on ret_5, 252-session prior percentile, regimes 0.80/0.20, target_relative_H for H=2,5).
3. DISPERSION_CONDITIONAL hypothesis test: tercile spreads by regime, block bootstrap CI (20-session blocks, 2000, seed 2041) and Newey-West HAC t (lag H); full and holdout; supported / partially / not label per registration.
4. Trading rules DISP_H2/H5 and RANK_H2/H5 (Ridge alpha=1.0, cross-sectional z-scored features, rank target in [-0.5,0.5], annual expanding refit from 2019, purge + embargo H+1, VIX missing -> no prediction), benchmarks REV5_17_H2, MOM21_17_H5, EW17, SPY_BH, CASH.
5. Signal-level metrics: mean daily Spearman rank IC + HAC t for DISP (active regimes) and RANK.
6. Verdicts exactly per registration (including the IC t>=2 and beat-the-unconditional-benchmark gates); USD max drawdown and worst 5-day loss on $2,000. DSR N=126 (global variance N/A as before; conditional diagnostic only). Append 5 lines (4 trials + 1 hypothesis test) to outputs/research/trial_ledger.jsonl.
7. Tests (synthetic): definitions and regime assignment (no look-ahead in percentile: t excluded), tercile spread math, look-ahead tests for features and Ridge training rows, purge/embargo, decision top-3, cost legs, determinism. Full suite + ruff pass.
8. Write outputs/research/p4-relative/report.json + report.md, and a concise Chinese "结果" section in human/p4-relative-2026-10-22.md (hypothesis test result, the 4 trials vs benchmarks at BASE: full + holdout net return, excess Sharpe, rank IC & t, USD drawdown, verdicts, honest limits). Update its status line and README row.
9. Forward runner code only (not scheduled, not run on production paths): `python -m aquant.multiday.p4_forward`, modeled on p3_forward (reads the P2 forward dated snapshot; fails closed if missing; BASE and STRESS; idempotent; atomic), plus docs/p4_forward_impl.json (implementation commit, committed_at, source hashes; start session = first session strictly after its implementation commit date in America/New_York), plus `summary(record)` returning one Chinese line <= 60 chars.
10. Commit in logical commits with trailer "Co-Authored-By: Codex <noreply@openai.com>". Final message: hypothesis-test label, 4 verdicts, IC/t, tests, deviations, forward implementation commit and first session.
