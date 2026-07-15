# MOFFIT CLI — User Guide & Maintenance Manual

A practical guide to installing, using, and maintaining the MOFFIT command-line interface. For project background and architecture, see [README.md](README.md) and [FRAMEWORK.md](FRAMEWORK.md).

---

## Part 1 — Installation & Setup

### Requirements

- Python 3.11+ (developed and verified on 3.14)
- Git
- ~2 GB free RAM for full-dataset analysis (6.3M rows)
- The PaySim dataset from Kaggle: https://www.kaggle.com/datasets/ealaxi/paysim1

### Install

```bash
git clone https://github.com/254francis/MOFFIT-Mobile-Money-Fraud-Forensic-Investigation-Toolkit.git
cd MOFFIT-Mobile-Money-Fraud-Forensic-Investigation-Toolkit
python -m venv venv
venv\Scripts\activate          # Windows (PowerShell)
# source venv/bin/activate     # Linux/macOS
pip install -e .
```

Verify the install:

```bash
moffit --help     # should list: info, ingest, analyze, timeline, report, case
pytest            # full test suite should pass
```

### Dataset placement

Download PaySim from Kaggle, extract, and place the CSV at:

```
data/samples/paysim.csv
```

The `data/samples/*.csv` path is gitignored — dataset files are never committed. For faster development runs, create a smaller sample:

```bash
python -c "import pandas as pd; pd.read_csv('data/samples/paysim.csv', nrows=500000).to_csv('data/samples/paysim_500k.csv', index=False)"
```

### Configuration

MOFFIT reads settings from a `.env` file in the repo root (copy `.env.example`):

| Variable | Purpose | Default |
|---|---|---|
| `CASE_DB_PATH` | SQLite case database location | `sqlite:///cases.db` |
| `REPORTS_DIR` | Default directory for generated PDFs | `reports/` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `SECRET_KEY` | HMAC signing key for custody records | — |

**`SECRET_KEY` is forensically critical.** It signs evidence manifests and report integrity signatures. Set it to a long random value, never commit it (`.env` is gitignored), and never change it mid-case — records signed under the old key will fail verification under the new one.

---

## Part 2 — Investigation Workflow

A complete investigation is five commands, in this order. Terminology: a **case** is the container for one investigation; **evidence** is an ingested transaction log (hashed at acquisition); **findings** are detector outputs; a **step** is PaySim's time unit (1 step = 1 hour of simulation).

### Step 1 — Create a case

```bash
moffit case new --name "OP-SIMSWAP-001" --investigator "F. Investigator" --desc "Suspected SIM-swap drain ring"
```

Prints the case UUID. **Copy it** — every subsequent command needs it. Case naming convention: an operation-style prefix and a serial (e.g. `OP-<TYPE>-<NNN>`) keeps the case list scannable.

List existing cases anytime:

```bash
moffit case list
```

### Step 2 — Ingest evidence

```bash
moffit ingest --case-id <CASE-UUID> --file data/samples/paysim.csv
```

What happens: the CSV is loaded and normalized, the file is hashed (SHA-256 + MD5), and an evidence record with the **absolute file path** and hashes is written to the case database. The printed hashes are your acquisition fingerprint — record them in your case notes; they appear in the final report's integrity table.

Do not move or modify the evidence file after ingestion. The stored absolute path is how `analyze`, `timeline`, and `report` locate the data, and any modification will change the hash and fail verification.

### Step 3 — Run fraud analysis

```bash
moffit analyze --case-id <CASE-UUID>
```

Runs all six pattern detectors and bulk-saves findings to the database. Runtime scales with data size: ~2 minutes for 500K rows, ~75 minutes for the full 6.36M-row dataset (benchmarked; scaling is superlinear because windowed detectors grow with per-account history depth).

Optional: `--account <ID>` restricts analysis to transactions touching one account.

**Note:** `analyze` appends findings — running it twice on the same case doubles the findings. To re-run cleanly, delete the case's findings first (see Maintenance → Database operations).

The six detectors and their confidence weights:

| Pattern | Fires when | Confidence |
|---|---|---|
| `rapid_drain` | >90% of balance drained within a 5-step window | 0.90 |
| `round_trip` | A→B→A within 10 steps, amount ±5% | 0.85 |
| `fan_out` | >5 unique receivers within 10 steps | 0.75 |
| `fan_in` | >5 unique senders within 10 steps | 0.70 |
| `dormant_activation` | <3 prior transactions, then amount >2× global median | 0.80 |
| `balance_inconsistency` | Balance arithmetic fails to reconcile — emitted as ONE dataset-level finding | 1.00 |

**Interpreting volumes:** on PaySim, expect very large finding counts (hundreds of thousands). `dormant_activation` and `rapid_drain` in particular collide with PaySim's dataset properties (most accounts appear only 1–2 times; drains are routine simulator behavior). Recall against labelled fraud is ~99.7%, but precision is low by design — findings are a maximal-recall candidate set for triage, not verdicts. The `balance_inconsistency` finding with account `DATASET` is an evidence-quality flag, not an account.

### Step 4 — Inspect account timelines

```bash
moffit timeline --case-id <CASE-UUID> --account C1000022742
```

Prints the account's chronological transactions with annotations (`[RAPID DRAIN]`, `[ACCOUNT DRAINED]`, `[DORMANT ACTIVATION]`, `[FLAGGED BY PAYSIM]`) and an auto-generated plain-English narrative — the same narrative embedded in the report's executive summary.

To find accounts worth inspecting, query the findings table (see Maintenance → Useful queries) or take account IDs from the `analyze` output.

### Step 5 — Generate the forensic report

```bash
moffit report --case-id <CASE-UUID> --output reports/OP-SIMSWAP-001.pdf
```

Produces an ISO/IEC 27037-aligned PDF: cover page (CONFIDENTIAL marking), executive summary, methodology, evidence integrity table, findings table (capped at top 100, total count stated), annotated account timelines, chain-of-custody appendix, and an HMAC-SHA256 integrity signature.

Generated reports are gitignored (`reports/`) — archive them per your organization's evidence-handling procedure, not in the code repository.

### Quick-reference card

```bash
moffit case new --name NAME --investigator NAME [--desc TEXT]   # create case
moffit case list                                                # list cases
moffit ingest  --case-id ID --file PATH                         # register + hash evidence
moffit analyze --case-id ID [--account ACC]                     # run 6 detectors
moffit timeline --case-id ID --account ACC                      # annotated history + narrative
moffit report  --case-id ID --output PATH.pdf                   # ISO 27037 PDF
```

---

## Part 3 — Maintenance Manual

### Repository hygiene

The `.gitignore` protects four categories — keep it that way:

```
__pycache__/          # Python bytecode (never commit; caused a real merge conflict once)
venv/                 # virtual environment
data/samples/*.csv    # datasets (GitHub rejects >100MB files)
*.db                  # case databases (case data is evidence, not source)
.env                  # contains SECRET_KEY
reports/              # generated case reports
```

### Testing

Run the full suite after every change:

```bash
pytest                 # everything
pytest tests/test_pattern_detector.py -v   # one module, verbose
```

The suite covers ingestion, case DB, graph builder, pattern detectors (one triggering fixture per detector), integrity (including tamper tests), and timeline. Conventions to preserve when adding tests:

- Use `tmp_path` for any test needing a database or file
- Each detector test constructs a minimal DataFrame specifically shaped to trigger its pattern
- If you deliberately change behavior, update the test that pins the old contract in the same commit (e.g., `test_add_evidence` pins absolute-path storage; `test_balance_inconsistency` pins the `DATASET` account and description format)

### Database operations

The case database is SQLite (default `cases.db` in the repo root). Useful operations — save these as small `.py` scripts rather than shell one-liners (PowerShell mangles nested quotes):

**Findings breakdown per pattern:**

```python
import sqlite3
conn = sqlite3.connect("cases.db")
for row in conn.execute(
    "SELECT finding_type, COUNT(*), ROUND(AVG(confidence),2) FROM findings "
    "WHERE case_id=? GROUP BY finding_type ORDER BY COUNT(*) DESC",
    ("<CASE-UUID>",),
):
    print(row)
```

**Clear a case's findings (before re-running analyze):**

```python
import sqlite3
conn = sqlite3.connect("cases.db")
conn.execute("DELETE FROM findings WHERE case_id=?", ("<CASE-UUID>",))
conn.commit()
print("cleared")
```

**Back up the case database:** copy `cases.db` while no MOFFIT command is running. For evidentiary soundness, hash the backup (`certutil -hashfile cases.db SHA256` on Windows) and record the hash.

### Performance characteristics & tuning

Benchmarked behavior (see `docs/build_log.md` for full history):

| Dataset | analyze runtime | Findings |
|---|---|---|
| 500K rows | ~2m 08s | ~310K |
| 6.36M rows (full PaySim) | ~74m | ~3.8M |

Design decisions that keep it this fast — do not regress them:

1. **Vectorized candidate pre-filters** in `rapid_drain`, `fan_out`, `fan_in`: a cheap pandas pass first computes which accounts could possibly fire; the detailed window loop runs only on those. The pre-filter must remain a strict superset of accounts that can fire, or detections will be silently lost.
2. **`dormant_activation`** uses a vectorized cumcount over the interleaved sender/receiver event sequence — no `iterrows` over the full dataset.
3. **`add_findings_bulk`** persists all findings in one transaction. Never revert to per-finding commits: at 300K+ findings that alone took the pipeline from minutes to unusable.

**Tuning detector thresholds:** thresholds live in each detector method in `moffit/detection/pattern_detector.py` (window sizes, uniqueness counts, multipliers) and confidence weights in the finding dicts. If you change either: update `FRAMEWORK.md`'s detection table to match (the two must never disagree — it's cited in the project report), adjust the detector's test fixture, and re-run the detection-rate evaluation (`detection_rate.py`) to re-measure recall.

### Extending MOFFIT

**Adding a new detector:**

1. Add a method to `FraudPatternDetector` returning the standard finding dict: `{pattern, account_id, step_start, step_end, amount, confidence, description}`
2. Register it in `analyze()`'s `findings.extend(...)` chain
3. Add a pre-filter if it iterates accounts (see above)
4. Add a triggering-fixture test in `tests/test_pattern_detector.py`
5. Document pattern, rationale, and confidence in `FRAMEWORK.md`

**Adding a CLI command:** follow the established loading pattern — `manager.get_evidence(case_id)` → filter `.csv` paths → `PaySimLoader().load_csv` → `.normalize()`. Never load files from paths supplied outside the evidence table; the custody chain depends on analysis running against registered, hashed evidence.

**Timeline annotations:** when passing findings to `annotate_events`, always pre-filter to the target account (`account in f.account_ids`). The annotator matches by step range only; unfiltered findings cross-contaminate annotations.

### Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `moffit: command not recognized` | venv not activated or install missing | `venv\Scripts\activate`, then `pip install -e .` |
| `ModuleNotFoundError` on a new dependency | dependency added to code but not `pyproject.toml` | add it to `dependencies`, `pip install -e .` (this happened with matplotlib in PR #4) |
| `analyze` finishes suspiciously fast with 0 findings | evidence path unresolvable (file moved/renamed) | check `get_evidence` paths exist; re-ingest if the file moved |
| Findings count doubles | `analyze` re-run without clearing | clear the case's findings first (script above) |
| Timeline shows no events for a flagged account | account only appears in the *other* role, or evidence file differs from the analyzed one | verify with the findings query; confirm evidence path |
| HMAC verification fails | `SECRET_KEY` changed since signing, or record tampered | restore the original key; if the key is correct, treat as an integrity incident |
| Two `.db` files appear | a script used a different default path than the CLI | the CLI uses `CASE_DB_PATH` (default `cases.db`); delete strays cautiously |
| PowerShell errors on `<` or quoted one-liners | shell parsing, not MOFFIT | never type `<placeholders>` literally; put multi-quote Python in a `.py` file |

### Maintenance log discipline

`docs/build_log.md` is the project's audit trail. Every merge, hand-fix, benchmark, and design change gets a dated entry: what changed, why, and the verification result. This record documents human oversight of AI-assisted development and doubles as the source for the project report's implementation chapter.

---

*MOFFIT v0.1 — B.Sc. Computer Science (Cybersecurity Forensics) final-year project, USIU-Africa, Nairobi. Evaluation dataset: PaySim (Lopez-Rojas, Elmir & Axelsson, 2016).*
