# MOFFIT — Mobile Money Fraud Forensic Investigation Toolkit

A Python-based digital forensics toolkit for investigating mobile money fraud. MOFFIT treats mobile money transaction logs (M-Pesa-style) as forensic evidence: it ingests transaction data, detects fraud patterns using graph and statistical analysis, reconstructs attack timelines, maintains a cryptographic chain of custody, and generates court-ready PDF forensic reports aligned with ISO/IEC 27037.

Built as a final-year Computer Science project (cybersecurity forensics concentration) at USIU-Africa, Nairobi.

## Why MOFFIT

Mobile money is the dominant financial rail in Kenya and much of the Global South, and mobile money fraud (SIM-swap drains, mule networks, laundering loops) is a growing investigative burden. Existing open-source forensic tools focus on disk, memory, and network artifacts — none treat mobile money transaction records as first-class forensic evidence with integrity guarantees and standards-aligned reporting. MOFFIT fills that gap.

The toolkit is developed and validated against **PaySim** (Lopez-Rojas, Elmir & Axelsson, 2016), a peer-reviewed synthetic dataset that models real African mobile money transactions, which makes the work reproducible without access to protected financial data.

## Features

- **Ingestion** — load and normalize PaySim-format CSV transaction logs into a typed pandas schema
- **Detection** — six fraud pattern detectors over a NetworkX transaction graph:
  | Pattern | Signal | Confidence |
  |---|---|---|
  | Rapid drain | >80% balance drained in <5 steps | 0.90 |
  | Round trip | A→B→A within 10 steps, ±5% amount | 0.85 |
  | Fan-out | >5 unique receivers in 10 steps | 0.75 |
  | Fan-in | >5 unique senders in 10 steps | 0.70 |
  | Dormant activation | Inactive account suddenly moves large funds | 0.80 |
  | Balance inconsistency | Arithmetic mismatch in balances | 1.00 |
- **Timeline** — per-account chronological event reconstruction with automatic pattern annotations and a plain-English attack narrative
- **Custody** — SHA-256/MD5 evidence hashing, HMAC-SHA256 signed records, verifiable evidence manifests, SQLite case database
- **Reporting** — ISO/IEC 27037-aligned PDF forensic report (cover page, executive summary, methodology, evidence integrity table, findings, timelines, chain-of-custody appendix)
- **CLI** — full investigation workflow via `moffit` command (Typer + Rich)
- **Web dashboard** — optional FastAPI case management UI (stretch goal)

## Architecture

```
PaySim CSV → [ingestion] → [detection] → [timeline] → [custody] → [reporting] → PDF report
                                                           ↕
                                                     SQLite case DB
```

Each module is a bounded context with a typed input/output contract:

| Module | Input | Output |
|---|---|---|
| `moffit/ingestion` | PaySim CSV | normalized DataFrame |
| `moffit/detection` | DataFrame | transaction graph + `List[Finding]` |
| `moffit/timeline` | DataFrame + findings | `List[TimelineEvent]` + narrative |
| `moffit/custody` | files + findings + events | HMAC manifest + SQLite records |
| `moffit/reporting` | case + findings + timeline + manifest | PDF report |

## Installation

Requires Python 3.11+.

```bash
git clone https://github.com/Sapien100/moffit.git
cd moffit
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -e .
```

Verify:

```bash
moffit --help
pytest
```

## Dataset

Download PaySim from Kaggle: https://www.kaggle.com/datasets/ealaxi/paysim1

Place the CSV in `data/samples/`. The full dataset is ~6.3M rows; a 100K-row sample is sufficient for development and demo.

## Usage

A complete investigation workflow:

```bash
# 1. Create a case
moffit case new --name "OP-SIMSWAP-001" --investigator "F. Investigator"

# 2. Ingest the transaction log as evidence (auto-hashed)
moffit ingest --case-id <CASE_ID> --file data/samples/paysim_sample.csv

# 3. Run fraud pattern analysis
moffit analyze --case-id <CASE_ID>

# 4. Inspect a suspect account's timeline
moffit timeline --case-id <CASE_ID> --account C1234567890

# 5. Generate the forensic report
moffit report --case-id <CASE_ID> --output reports/OP-SIMSWAP-001.pdf
```

## Project Structure

```
moffit/
  ingestion/    PaySim loading + normalization
  detection/    graph builder + 6 pattern detectors
  timeline/     attack timeline reconstruction
  custody/      hashing, HMAC signing, case DB (SQLAlchemy)
  reporting/    ReportLab PDF generation
  cli/          Typer entry point
  api/          FastAPI dashboard (stretch)
tests/          pytest suite
data/samples/   PaySim sample data (not committed)
docs/           methodology + design docs
```

## Standards & Legal Alignment

- **ISO/IEC 27037:2012** — evidence identification, collection, and preservation fields in every report
- **NIST SP 800-86** — forensic process model (collection → examination → analysis → reporting)
- **Kenya Computer Misuse and Cybercrimes Act (2018)** — admissibility context for electronic evidence
- **Kenya Data Protection Act (2019)** — synthetic data used precisely to avoid processing real personal financial data

## Development Approach

MOFFIT is built in a 3-week sprint using [Jules](https://jules.google/) (Google's async coding agent) against a set of 10 scoped GitHub issues — see [`JULES_PROMPTS.md`](JULES_PROMPTS.md). Every PR is human-reviewed before merge; architecture, fraud-pattern logic, and forensic methodology are the author's own. See [`FRAMEWORK.md`](FRAMEWORK.md) for the research and design framework.

## Success Criteria

- ≥90% detection rate on PaySim's labelled fraud rows (held-out test)
- Full case run (ingest → PDF) in <5 minutes for 100K rows
- Every report contains all ISO/IEC 27037 evidence-handling fields

## Key References

- Lopez-Rojas, E. A., Elmir, A., & Axelsson, S. (2016). *PaySim: A financial mobile money simulator for fraud detection.* 28th European Modeling and Simulation Symposium (EMSS).
- Kent, K., Chevalier, S., Grance, T., & Dang, H. (2006). *Guide to Integrating Forensic Techniques into Incident Response* (NIST SP 800-86).
- ISO/IEC 27037:2012. *Guidelines for identification, collection, acquisition and preservation of digital evidence.*
- Pourhabibi, T., Ong, K.-L., Kam, B. H., & Boo, Y. L. (2020). Fraud detection: A systematic literature review of graph-based anomaly detection approaches. *Decision Support Systems, 133*.

## License

MIT — see [LICENSE](LICENSE).

## Author

Francis — B.Sc. Computer Science (Cybersecurity Forensics), USIU-Africa, Nairobi.
