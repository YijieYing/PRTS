You are Codex in /Users/prts/Projects/aquant/.worktrees/multiday (branch research/multiday-20261021). Run the diagnostic registered in docs/p3_sensitivity.json (sha256 53dfabcfdfac74ac54ca0c6731c3e96f6375a89e45a30777b9e026514dc15252).

Rules:
- Never edit docs/*.json registrations or any file listed in docs/p1_forward.json, docs/p2_forward.json or docs/p3_forward_impl.json source hashes (all deployed on lain). New code only, e.g. src/aquant/multiday/p3/sensitivity.py.
- Reuse the existing P2 engine and P3 cost plumbing; reuse saved LOGIT probabilities/fits (no refit). No downloads, no orders, never write outputs/daily/. No push/merge.
- Reproduce P3_SIGNED and FLAT_5_P2 from saved results and assert they match the saved reports exactly before computing new scenarios.

Deliver:
1. outputs/research/p3-sensitivity/report.json + report.md exactly as registered (7 rules x 7 scenarios x 4 periods; PROFITABLE flags; break-even flat bp per rule by bisection, 0.1 bp tolerance, searched in [0, 15] bp; decision label per the fixed rules).
2. One diagnostic line appended to outputs/research/trial_ledger.jsonl (kind=cost_sensitivity).
3. Tests for: scenario cost lookup (FLOOR uses docs/p3_forward.json table), SEC fee on sells for FLAT scenarios, bisection monotonic handling, decision-label logic on synthetic flag patterns. Full suite + ruff pass.
4. A concise Chinese section "成本敏感性（2026-10-22）" appended to human/p3-costs-2026-10-21.md: table of full-period excess Sharpe and net return per rule for FLOOR_BASE / FLAT_1 / FLAT_2 / FLAT_3, break-even bp per rule, and the decision label. Note it is a diagnostic, not new trials.
5. Commit with trailer "Co-Authored-By: Codex <noreply@openai.com>". Final message: decision label, break-even bp per rule, reproduction check, tests.
