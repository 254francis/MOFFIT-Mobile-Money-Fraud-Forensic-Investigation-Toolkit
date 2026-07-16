# MOFFIT User Guide

**Mobile Money Fraud Forensic Investigation Toolkit — complete step-by-step guide**

MOFFIT has three interfaces, all sharing one case database:

1. **CLI** — the full investigation workflow (create case → ingest → analyze → timeline → report)
2. **Web dashboard** — browse cases, run analysis, view charts, download reports from a browser
3. **ML module** — train fraud classifiers and rank accounts for triage

This guide walks through each, in the order you'd actually use them. For project background see [README.md](README.md); for the research framework see [FRAMEWORK.md](FRAMEWORK.md).

---

# Part 1 — First-Time Setup

Do this once. Every later session only needs Step 4 (activate the environment).

### Step 1 — Install prerequisites

You need:
- **Python 3.11 or newer** — from https://www.python.org/downloads/ (tick **"Add python.exe to PATH"** during install)
- **Git** — from https://git-scm.com/download/win (accept defaults)

Verify both (open a new terminal after installing):

```powershell
python --version
git --version
```

### Step 2 — Get the code

```powershell
git clone https://github.com/254francis/MOFFIT-Mobile-Money-Fraud-Forensic-Investigation-Toolkit.git
cd MOFFIT-Mobile-Money-Fraud-Forensic-Investigation-Toolkit
```

### Step 3 — Create the virtual environment and install

```powershell
python -m venv venv
venv\Scripts\activate
pip install -e .
```

You should see `(venv)` at the start of your prompt. The install takes a few minutes (it includes pandas, scikit-learn, xgboost, and more).

> **If activation is blocked** with an execution-policy error, run
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once, then retry.

Verify:

```powershell
moffit --help    # should list: info, ingest, analyze, timeline, report, case, ml
pytest           # full test suite should pass
```

### Step 4 — (Every session) Activate the environment

Whenever you open a new terminal:

```powershell
cd MOFFIT-Mobile-Money-Fraud-Forensic-Investigation-Toolkit
venv\Scripts\activate
```

### Step 5 — Get the dataset

1. Download PaySim from Kaggle: https://www.kaggle.com/datasets/ealaxi/paysim1 (free account required)
2. Extract the zip — inside is one large CSV
3. Move it into the repo as:

```
data\samples\paysim.csv
```

The full file is ~470MB / 6.36M rows. For faster runs and demos, also create a 500K-row sample:

```powershell
python -c "import pandas as pd; pd.read_csv('data/samples/paysim.csv', nrows=500000).to_csv('data/samples/paysim_500k.csv', index=False)"
```

Dataset files are gitignored — they are never committed.

### Step 6 — Configure (optional)

Copy `.env.example` to `.env` and set:

| Variable | Purpose | Default |
|---|---|---|
| `CASE_DB_PATH` | The shared case database (CLI **and** web use this) | `sqlite:///cases.db` |
| `SECRET_KEY` | HMAC key that signs custody records | — |

> **`SECRET_KEY` matters forensically.** It signs evidence manifests and report signatures. Set it to a long random value, never commit it, and never change it mid-case — records signed under the old key will fail verification under the new one.

---

# Part 2 — Running an Investigation (CLI)

A complete investigation is five commands. Quick vocabulary: a **case** contains one investigation; **evidence** is an ingested transaction log (hashed at acquisition); **findings** are detector outputs; a **step** is PaySim's time unit (1 step ≈ 1 hour).

### Step 1 — Create a case

```powershell
moffit case new --name "OP-SIMSWAP-001" --investigator "Your Name" --desc "Suspected SIM-swap drain"
```

This prints a **Case ID** (a UUID like `b346e603-...`). **Copy it** — every following command needs it.

To see all cases at any time:

```powershell
moffit case list
```

### Step 2 — Ingest evidence

```powershell
moffit ingest --case-id <CASE-ID> --file data/samples/paysim_500k.csv
```

> Replace `<CASE-ID>` with the actual UUID — never type the angle brackets themselves.

What happens: the CSV is loaded, hashed (SHA-256 + MD5), and registered as evidence with its absolute path. **Record the printed hashes** — they are your acquisition fingerprint and appear in the final report.

Rules after ingestion:
- **Do not move, rename, or edit the evidence file.** Analysis locates it by the stored path, and any change breaks hash verification.
- Evidence can only enter through this command — the web dashboard deliberately has no upload (custody design: all evidence passes through the hashing path).

### Step 3 — Run fraud analysis

```powershell
moffit analyze --case-id <CASE-ID>
```

Runs all six detectors and saves findings in one bulk transaction. Expected runtime: **~2 minutes** for the 500K sample, **~75 minutes** for the full dataset.

The six detectors:

| Pattern | Fires when | Confidence |
|---|---|---|
| `rapid_drain` | >90% of balance drained within a 5-step window | 0.90 |
| `round_trip` | A→B→A within 10 steps, amount ±5% | 0.85 |
| `fan_out` | >5 unique receivers within 10 steps | 0.75 |
| `fan_in` | >5 unique senders within 10 steps | 0.70 |
| `dormant_activation` | <3 prior transactions, then amount >2× global median | 0.80 |
| `balance_inconsistency` | Balance arithmetic fails — ONE dataset-level finding | 1.00 |

**How to read the results:** expect very large finding counts (hundreds of thousands on PaySim). This is by design — the rule layer maximizes recall (~99.7% of labelled fraud is covered) at low precision. Findings are a triage candidate set, not verdicts. Use the ML module (Part 4) to rank them. The `balance_inconsistency` finding with account `DATASET` is a data-quality flag about the evidence itself, not a suspect account.

**Important:** `analyze` **appends**. Running it twice doubles the findings. To re-run cleanly, clear the case's findings first (see Part 5 → Database operations).

### Step 4 — Inspect a suspect's timeline

```powershell
moffit timeline --case-id <CASE-ID> --account C1000022742
```

Prints the account's chronological transactions with annotations (`[RAPID DRAIN]`, `[ACCOUNT DRAINED]`, `[DORMANT ACTIVATION]`, `[FLAGGED BY PAYSIM]`) followed by an auto-generated plain-English narrative — the same narrative used in the report's executive summary.

To find account IDs worth inspecting, take them from the `analyze` output table, the web dashboard, or `moffit ml rank` (Part 4).

### Step 5 — Generate the forensic report

```powershell
moffit report --case-id <CASE-ID> --output reports/OP-SIMSWAP-001.pdf
```

Produces an ISO/IEC 27037-aligned PDF with 8 sections: cover page (CONFIDENTIAL marking), executive summary, methodology, evidence integrity table, findings table (top 100 with total count stated), annotated account timelines, chain-of-custody appendix, and an HMAC-SHA256 integrity signature.

Reports are gitignored — archive them per evidence-handling procedure, not in the repo.

### CLI quick-reference card

```
moffit case new --name NAME --investigator NAME [--desc TEXT]   create case
moffit case list                                                list all cases
moffit ingest  --case-id ID --file PATH                         hash + register evidence
moffit analyze --case-id ID [--account ACC]                     run 6 detectors
moffit timeline --case-id ID --account ACC                      annotated history + narrative
moffit report  --case-id ID --output PATH.pdf                   ISO 27037 PDF
moffit ml train --case-id ID                                    train 3 classifiers
moffit ml rank  --case-id ID [--top N]                          rank accounts by fraud probability
```

---

# Part 3 — The Web Dashboard

The dashboard is a browser view over the **same database** as the CLI — cases created in one appear instantly in the other.

### Step 1 — Start the server

```powershell
uvicorn moffit.api.main:app --reload --port 8000
```

Leave this terminal running. Open a browser to:

```
http://localhost:8000
```

To stop the server later: `Ctrl+C` in that terminal.

### Step 2 — Browse cases

The home page shows every case as a card with its finding counts by severity. Click a case to open its detail page: findings table (capped for display — the full set stays in the database), severity and pattern charts, evidence list, and action buttons.

### Step 3 — Create a case from the browser

Use the new-case form (name, investigator, description). The case appears immediately in `moffit case list` too — one shared database.

### Step 4 — Register evidence (CLI step)

The dashboard intentionally has **no file upload** — evidence must enter through the hashing ingest path:

```powershell
moffit ingest --case-id <CASE-ID-from-the-URL> --file data/samples/paysim_500k.csv
```

(The case ID is the UUID in the browser's address bar.) Refresh the case page — the Evidence panel now shows the file and its hash.

### Step 5 — Analyze from the browser

Click **Analyze Evidence**. Analysis runs as a background task (~2 minutes on the 500K sample) — the page polls status and updates when done. Refresh to see findings and charts populate.

> Use the 500K sample for dashboard work. The full dataset takes ~75 minutes, which is fine for the CLI but tedious behind a browser spinner.

### Step 6 — Download the report

Click **Download Forensic Report** — the same 8-section PDF as the CLI, generated on demand.

> Don't download the report while analysis is still running — you'll get a snapshot with zero findings. Wait for the findings count to appear first.

---

# Part 4 — ML Triage

The ML module trains classifiers that rank accounts by fraud probability, solving the rule layer's precision problem: rules find everything (~99.7% recall) but flag far too much; the classifier orders that haystack so investigators start at the top. Benchmark on PaySim: Random Forest reached **100% precision at 91.4% recall** on the held-out test set.

### Step 1 — Train

The case must already have ingested evidence (Part 2, Step 2). Then:

```powershell
moffit ml train --case-id <CASE-ID>
```

Takes several minutes: feature engineering, three models (Logistic Regression baseline, Random Forest, XGBoost) trained on a stratified 70/15/15 split with class-imbalance handling, then evaluation. Prints a metrics table (precision, recall, F1, AUPRC, ROC-AUC per model — never plain accuracy, which is meaningless at 0.13% fraud prevalence).

Artifacts are saved to `reports/ml/<case-id>/`:

| File | What it is |
|---|---|
| `metrics.json` | All metrics for all three models |
| `pr_curves.png` | Precision-recall curves compared |
| `feature_importance.png` | XGBoost's most predictive features |
| `shap_summary.png` | Per-feature SHAP attributions (explainability) |
| `*_model.joblib` | The trained models |

### Step 2 — Rank accounts

```powershell
moffit ml rank --case-id <CASE-ID> --top 20
```

Prints the top accounts by fraud probability — your investigation priority list. Feed the top IDs into `moffit timeline` to inspect each.

### How the two layers fit together

Rules first (forensic completeness — nothing is missed), ML second (triage — start where fraud probability is highest), timeline third (human inspection), report last (court-format documentation). ML scores are triage aids; the rule-based findings and hashed evidence remain the forensic record. SHAP plots make every score explainable.

---

# Part 5 — Maintenance

### Repository hygiene

The `.gitignore` protects these — keep it that way:

```
__pycache__/  *.pyc      Python bytecode (caused a real merge conflict once)
venv/                    virtual environment
data/samples/*.csv       datasets (GitHub rejects >100MB)
*.db                     case databases — case data is evidence, not source
.env                     contains SECRET_KEY
reports/  report_*.pdf   generated case reports and ML artifacts
```

### Testing

After any change:

```powershell
pytest                                      # everything (38 tests)
pytest tests/test_pattern_detector.py -v    # one module, verbose
```

Conventions when adding tests: use `tmp_path` for anything needing files/DBs; each detector test builds a minimal DataFrame shaped to trigger its pattern; if you deliberately change behavior, update the test that pins the old contract in the same commit.

### Database operations

The shared database is SQLite (`cases.db` by default, via `CASE_DB_PATH`). For queries, write small `.py` scripts — **not** PowerShell one-liners, which mangle nested quotes.

**Clear a case's findings** (required before re-running analyze):

```python
# clear_findings.py
import sqlite3
conn = sqlite3.connect("cases.db")
conn.execute("DELETE FROM findings WHERE case_id=?", ("<CASE-ID>",))
conn.commit()
print("cleared")
```

**Findings breakdown by pattern:**

```python
# breakdown.py
import sqlite3
conn = sqlite3.connect("cases.db")
for row in conn.execute(
    "SELECT finding_type, COUNT(*), ROUND(AVG(confidence),2) FROM findings "
    "WHERE case_id=? GROUP BY finding_type ORDER BY COUNT(*) DESC", ("<CASE-ID>",)):
    print(row)
```

**Back up the database:** copy `cases.db` while nothing is running; hash the copy (`certutil -hashfile cases.db SHA256`) and record the hash for evidentiary soundness.

### Performance — do not regress these

Benchmarks: 500K rows analyze in ~2m08s; full 6.36M in ~74m (superlinear — windowed detectors scale with per-account history depth). Three design decisions keep it this fast:

1. **Vectorized pre-filters** (`rapid_drain`, `fan_out`, `fan_in`): a cheap pandas pass finds which accounts *could* fire before any Python loop runs. The pre-filter must stay a strict superset or detections are silently lost.
2. **No `iterrows` over full data** — `dormant_activation` uses a vectorized cumcount.
3. **`add_findings_bulk`** — one transaction for all findings. Per-finding commits made the pipeline unusable (>20min, aborted) before this fix.

**Tuning thresholds:** window sizes and confidence weights live in `moffit/detection/pattern_detector.py`. If you change any: update FRAMEWORK.md's table to match, fix the detector's test fixture, and re-measure recall with `detection_rate.py`.

### Extending MOFFIT

**New detector:** add a method to `FraudPatternDetector` returning the standard dict (`pattern, account_id, step_start, step_end, amount, confidence, description`); register it in `analyze()`; add a pre-filter if it iterates accounts; add a triggering-fixture test; document it in FRAMEWORK.md.

**New CLI command or web route:** always load data through the established pattern — `manager.get_evidence(case_id)` → first `.csv` path → `PaySimLoader().load_csv` → `.normalize()`. Never accept file paths from user input or web requests; the custody chain requires analysis to run only against registered, hashed evidence.

**Two contracts that bit us before — respect them:**
- `annotate_events` matches findings by step range only: **filter findings to the target account first** or annotations cross-contaminate.
- `add_findings_bulk` takes `{finding_type, severity, account_ids, ...}`, while detectors emit `{pattern, account_id, ...}` — the severity-mapping payload loop in `cli/main.py` is the reference translation.

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `moffit` not recognized | venv not activated | `venv\Scripts\activate`, then `pip install -e .` |
| `ModuleNotFoundError` | dependency used but not declared in `pyproject.toml` | add it, `pip install -e .` (happened with matplotlib) |
| `analyze` instantly returns 0 findings | evidence file moved/renamed — stored path unresolvable | check paths from `get_evidence`; re-ingest if moved |
| Findings count doubled | `analyze` re-run without clearing | run `clear_findings.py` first |
| Web shows a case the CLI can't find (or vice versa) | the two are reading different DB files | both must resolve via `CASE_DB_PATH`; check for stray `.db` files in the repo root |
| Web report has 0 findings | downloaded while analysis was still running | wait for the findings count, re-download |
| HMAC verification fails | `SECRET_KEY` changed since signing, or tampering | restore the key; if correct, treat as an integrity incident |
| PowerShell errors on `<` or quoted one-liners | shell parsing | never type `<placeholders>` literally; put quoted Python in a `.py` file |
| Terminal stuck at `(END)` | output opened in the pager | press `q` |

### The build log

`docs/build_log.md` is the audit trail: every merge, hand-fix, benchmark, and design decision, dated. Keep adding to it — one line per change, what and why. It documents human oversight of the AI-assisted build and is the source material for the implementation chapter.

---

*MOFFIT v0.1 — B.Sc. Computer Science (Cybersecurity Forensics) final-year project, USIU-Africa, Nairobi. Evaluation dataset: PaySim (Lopez-Rojas, Elmir & Axelsson, 2016). Benchmarks: 99.7% detection rate on labelled fraud; ~70s per 100K rows; RF triage 100% precision at 91.4% recall.*
