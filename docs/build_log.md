# MOFFIT Build Log

## 2026-07-14
- Merged PR #1 (project scaffold): verified pyproject.toml deps, directory layout, CLI entry point.
- Merged PR #2 (PaySim ingestion): verified column normalization incl. oldbalanceOrg -> sender_balance_before.
- Merged PR #3 (case DB): verified SHA-256/MD5 auto-hashing in add_evidence, Finding.confidence as float.
- Local verification: pip install -e . clean, moffit --help OK, pytest 11/11 passed (1.48s).
- Environment note: running Python 3.14.6 (spec says 3.11+) — no issues observed.
- Queued issues #4, #6, #8 to check and implement by 15-07-2026.

