Implemented and committed. **All 7 trials are WEAK; no candidates.** Five changed from REJECTED to WEAK; two remained WEAK. Every full-period STRESS Sharpe is negative.

Measured buy costs, **median / p75 bp**, excluding fees:

| ETF | Open buy | Close buy |
|---|---:|---:|
| SPY | 0.705 / 2.735 | −1.396 / 2.832 |
| QQQ | 0.218 / 3.866 | −0.618 / 3.754 |
| IWM | 0.486 / 6.492 | 0.000 / 3.780 |
| Cross-ETF median | 1.379 / 6.232 | 0.000 / 2.735 |

[All 27 ETFs and sell costs](/Users/prts/Projects/aquant/.worktrees/multiday/outputs/research/p3-costs/costs.md) · [Seven-trial results and dollar risks](/Users/prts/Projects/aquant/.worktrees/multiday/human/p3-costs-2026-10-21.md)

- **Validation:** 872 passed, 4 skipped; Ruff and formatting pass. All 28 P2 comparison ledgers reproduced; 126 scenarios reconciled.
- **Missingness:** 7,042/18,900 windows missing. Fourteen annual-cost scenarios remain unresolved; no substitution.
- **Ledger:** exactly +7 trials, N=114. Frozen protocols and protected sources unchanged.
- **Key interpretations:** current fees throughout history, terminal `close_sell`, signed costs retained, and whole-share entry rounding with P2 adjusted accounting. Global DSR remains N/A.

Claude should audit these interpretations and decide whether to separately register forward repricing. This cost re-examination was result-motivated.

Results: `9686af8`; human summary: `b9b23e7`. Working tree clean.