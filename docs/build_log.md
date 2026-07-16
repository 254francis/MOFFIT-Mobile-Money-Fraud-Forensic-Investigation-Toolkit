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
- Full-dataset benchmark (6,362,620 rows): analyze completed in 74m05s (~70s/100K,
  criterion <5min/100K PASSED). 3,808,826 findings: dormant_activation 2,212,161,
  rapid_drain 1,561,362, fan_in 35,302, balance_inconsistency 1 (dataset-level),
  round_trip 0, fan_out 0. Detection rate vs isFraud ground truth: 8,192/8,213 =
  99.7% (criterion >=90% PASSED). Precision ~0.2% — rule thresholds collide with
  PaySim dataset properties (accounts avg ~1.9 txns -> dormant fires broadly;
  drains are normal PaySim behavior). Documented as empirical motivation for ML
  triage layer (issue #11). Superlinear scaling noted (12.7x data -> 35x time).
  - Merged PR #7 (timeline reconstruction). Merge conflict in cli/main.py (Jules's
  \suggestion vs local implementation) — resolved keeping account-filtered findings
  (annotate_events matches by step range only; unfiltered findings cross-
  contaminate) + Jules's try/except; added narrative panel output. 31/31 tests.
- Timeline smoke test on TEST-500K, account C1000022742: correct chronology,
  [RAPID DRAIN][ACCOUNT DRAINED] annotations, coherent auto-narrative. Pipeline
  stages 1-3 (ingest -> analyze -> timeline) verified end-to-end on real data.
  ## 2026-07-15
- Merged PR #9 (PDF report generator) — Jules wired the CLI correctly this time
  (integration note in issue text credited). All tests passing.
- First complete forensic report generated: reports/TEST-500K.pdf. All 8 spec
  sections present: cover, exec summary, methodology (Lopez-Rojas cited),
  evidence integrity (SHA-256/MD5), findings capped top-100-of-309,607,
  annotated timelines, custody manifest + manifest hash, HMAC signature.
- ALL THREE SUCCESS CRITERIA MET: detection 99.7% (>=90%), runtime ~70s/100K
  (<5min/100K), ISO/IEC 27037 report fields complete. Core toolkit (issues
  #1-#9) finished ahead of 3-week schedule.
- Report audit findings for polish pass: findings table tie-breaking (rank by
  amount within equal confidence), exec summary should narrate top account by
  amount (currently arbitrary first finding), exclude DATASET pseudo-account
  from timelines section, header spacing.
  ## 2026-07-16
- Merged PR #10 (FastAPI dashboard) and PR #11 (ML classification module).
  pyproject.toml dependency conflict between the two resolved by union.
- Review #6: API test fixture failed on Windows (PermissionError —
  os.remove before engine.dispose; SQLite file still locked). Reordered dispose
  before removal in setup and teardown. Cross-platform defect: passes on Linux
  , fails on Windows.
- Full suite: 38/38 passing. ALL 11 ISSUES BUILT, MERGED, VERIFIED.
- Review #7: web report route called nonexistent generate_report() (real method:
  generate()) and reloaded the full CSV once per flagged account (~116K loads —
  unusable). Fixed: aligned signature, single CSV load, capped timelines at 5
  accounts, wired generate_narrative into exec summary.
- Review #8: web and CLI layers maintained separate case databases (API:
  MOFFIT_DB -> moffit.db; CLI: CASE_DB_PATH -> cases.db). Split-brain discovered
  when CLI ingest failed against a web-created case. Unified on CASE_DB_PATH
  resolution; updated API test env var; deleted orphan DBs.
- Review #9: analysis background task called nonexistent detect_all() and passed
  raw detector dicts to add_findings_bulk (schema mismatch). Aligned with
  detector.analyze() + severity-mapping payload (mirrors CLI implementation).
- Full web round-trip verified: web-created case -> CLI ingest -> web analyze
  (309,607 findings, ~2min background task) -> web report download.
- Reproducibility check: same evidence analyzed in two cases via two interfaces
  two days apart produced identical findings (309,607, same top-100, same
  timelines), identical evidence SHA-256; case-specific HMAC signatures and
  timestamps correctly differed. Deterministic analysis + per-case custody
  separation demonstrated.
- SYSTEM COMPLETE: CLI + web dashboard + ML triage, one shared database,
  38/38 tests, all success criteria passed.
