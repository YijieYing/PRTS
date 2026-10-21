You are Codex, implementing aquant research P1 in the git worktree /Users/prts/Projects/aquant/.worktrees/multiday (branch research/multiday-20261021). Claude is the decision layer and will audit your work; you implement.

Read first: AGENTS.md, CLAUDE.md, human/direction-2026-10-21.md, docs/multiday.json, docs/p1_trend.json, human/p1-trend-2026-10-21.md.

## Hard rules
- docs/p1_trend.json is the frozen preregistration. Its sha256 must stay 85f892614dac5ec9f8a1ba9bc2870f2bd4006b8ef141c7fa9637eeaf1b915c26. Never edit it. If something in it is impossible or ambiguous, implement the most literal reading, record the issue under "deviations" in report.json and in the human doc, and do not change rules after seeing results.
- No Paper/Live orders, no trading API calls at all. Market data endpoints only. No paid data.
- Credentials: read APCA_API_KEY_ID / APCA_API_SECRET_KEY from /Users/prts/Projects/aquant/.env at runtime (dotenv, read-only). Never copy, print, log or commit them.
- Do not touch the main checkout /Users/prts/Projects/aquant except reading .env; do not touch launchd jobs or existing forward/shadow/strategy code. Put new code in a new package src/aquant/multiday/.
- Keep all results, including bad ones. Do not tune parameters. Do not merge branches, push, or rewrite history.

## Tasks
1. Data (cache under data/raw/multiday/, gitignored, with sha256 manifest):
   - Alpaca daily bars 2015-01-01..2026-10-20 for the 27 ETFs, feed=sip, both adjustment=raw and adjustment=all; corporate actions raw.
   - FRED DTB3 CSV (https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3).
   - Ken French 10 Industry Portfolios daily+monthly and F-F Research Data Factors daily+monthly (mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/ zip CSVs).
   - Data quality report: per-ETF first/last date, missing sessions vs Alpaca calendar, zero/negative prices, large gaps.
2. Engine in src/aquant/multiday/: month-end signals for TSMOM, SMA10, XSMOM, DUAL and the 4 benchmarks exactly as registered; daily mark-to-market portfolio simulator with cash accruing risk_free, next-open and next-close execution, per-side costs 0/5/15 bp on executed notional including initial entry and terminal liquidation; metrics and moving-block bootstrap per docs/multiday.json + p1_trend.json; DSR with N=100.
3. Tests (pytest, synthetic data): each rule's signal; look-ahead test (mutating bars after the signal date must not change the signal); cost/turnover accounting; benchmark rebalancing; bootstrap determinism with seed. Run the full suite and ruff.
4. Run P1. Write outputs/research/p1-trend/report.json and report.md: all 4 rules x 2 timings x 3 costs + 4 benchmarks, Ken French diagnostic (1927-2015 vs 2016+), verdict per rule per the registered verdict rules, deviations list. Append one line per primary trial to outputs/research/trial_ledger.jsonl.
5. Daily forward runner (code only, do NOT schedule it): `python -m aquant.multiday.daily` that fetches the latest completed daily bars, marks the registered forward simulated portfolios (all 4 rules, hypothetical, start at first month-end after your implementation commit), rebalances only at month-end, appends to outputs/research/p1-trend/forward/ledger, and writes outputs/daily/YYYY-MM-DD.md plus outputs/daily/latest-wechat.txt (<= 900 Chinese characters). The WeChat text starts with a 2-3 line market summary of the day (SPY/QQQ/IWM/TLT/GLD daily return, best/worst sector ETF, 10Y proxy IEF move), then forward simulated portfolio status, then any research progress line. It must be idempotent per date and must not run on non-trading days (use Alpaca calendar).
6. Human doc: add a short "结果" section to human/p1-trend-2026-10-21.md (Chinese, concise, a table of base-cost next-open results vs EW_BH, verdicts, honest limits). Update the status line and its row in human/README.md.
7. Commit in logical commits with message trailer "Co-Authored-By: Codex <noreply@openai.com>". Final message: summary of verdicts, test counts, data coverage issues, deviations, and anything Claude must decide.
