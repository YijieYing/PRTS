Committed as `e2f4662` with the requested co-author trailer. Worktree clean.

Both frozen files match `f364f06` byte-for-byte. Active registration hashes:

| Registration | Matching hashes |
|---|---:|
| P1 | 13/13 |
| P2 | 22/22 |
| P3 implementation | 32/32 |
| P4 implementation | 45/45 |

Moved five functions into `history_ml03`: `parameters`, `quality`, `eligibility`, `verify_gaps`, `verify_feed`. Updated callers in `scripts/research/{ml01,ml02,ml03,market}.py`, `tests/test_market.py`, and migrated ML condition tests into `tests/test_history_ml03.py`.

All six dependency pins moved unchanged to `requirements-ml.txt`; installation guidance updated.

Validation: **1122 passed, 4 existing external-fixture skips**. All four requested registration tests passed. `test_model_persists_exact_feature_contract` passed after installing missing dependencies locally and using PyTorch’s bundled OpenMP. Ruff lint and formatting passed.

Other protected files, registrations, and results remained unchanged. No deployment or push.