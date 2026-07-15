# MOFFIT Build Log

## 2026-07-14
- Merged PR #1 (project scaffold): verified pyproject.toml deps, directory layout, CLI entry point.
- Merged PR #2 (PaySim ingestion): verified column normalization incl. oldbalanceOrg -> sender_balance_before.
- Merged PR #3 (case DB): verified SHA-256/MD5 auto-hashing in add_evidence, Finding.confidence as float.
- Local verification: pip install -e . clean, moffit --help OK, pytest 11/11 passed (1.48s).
- Environment note: running Python 3.14.6 — no issues observed.
- Queued issues #4, #6, #8 to check and implement by 15-07-2026.
- Merged PR #4 (transaction graph builder) and PR #6 (CLI interface).
- Resolved merge conflict on PR #8 branch: I had committed __pycache__/*.pyc
  bytecode artifacts to version control. Purged via git rm --cached, unified
  .gitignore (added __pycache__/, *.pyc, venv/, *.db, .env).
- Merged PR #8 (evidence hashing + chain of custody) after conflict resolution.
- Caught missing dependency: graph_builder.py imports matplotlib but PR #4 did not
  declare it in pyproject.toml — pytest collection failed with ModuleNotFoundError.
  Fixed by hand (added matplotlib>=3.8), commit 086b02a.
- Local verification: pytest 20/20 passed (case_db 6, graph_builder 5, ingestion 5,
  integrity 4).
- Repo migrated from Sapien100/ to 254francis/ account; updated git remote URL and
  re-pointed automated tools used at the new location.
- First end-to-end smoke test on real data:
  - Created case TEST-001 (c8a9c5fb-9c31-47f0-a43b-372881364f08).
  - Ingested full PaySim dataset: 6,362,620 rows (~470MB), no memory issues.
  - Evidence registered with SHA-256 16910f90577b0d981bf8ff289714510bb89bc71b...
    and MD5 e92a5f7447f43712f1dca473d0b0fa85 (evidence 4461c547...).
  - moffit case list confirms persistence: 1 case, 1 evidence item, 0 findings
    (findings expected zero — detector is issue #5, in progress).
- Queued issue #5 (fraud pattern detector) to workflow. Next in chain: #7 → #9.
-  (most significant change of the day): moffit analyze was a stub fixed that — 
  CLI predated the #5 detector and analyzed an empty DataFrame (dummy_df), returning
  zero findings in 2.2s with a success message. Integration seam between parallel
  issues that no single task owned. Fixed by hand: added CaseManager.get_evidence(),
  changed add_evidence to store absolute paths (forensically more correct — evidence
  records now identify acquisition location), wired analyze to evidence lookup →
  PaySimLoader.load_csv → normalize → FraudPatternDetector. Updated test_add_evidence
  to the new path contract. 27/27 tests passing.
  - Performance intervention (#5): naive detectors unusable at scale. Profiled per-
  detector on 500K rows; found groupby-Python-loops over ~400K near-singleton
  account groups (rapid_drain, fan_out, fan_in), iterrows in dormant_activation,
  and per-finding DB commits as compounding bottlenecks. Fixes: vectorized
  candidate pre-filters (strict superset, detection logic unchanged), cumcount
  rewrite of dormant_activation, balance_inconsistency redefined to one dataset-
  level finding (78.3% of PaySim rows fail reconciliation — dataset property, not
  account signal), add_findings_bulk single-transaction insert. Result: 500K
  analyze >20min (aborted) -> 2m08s; 309,607 findings persisted. Detection-only
  time ~48s. Round_trip — did an individual since i suspected this was the main suspect — reason being it was Jules's best-
  implemented detector (vectorized self-merge); profiling beat intuition.
