import os
from typing import Dict, Any, List
from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates

from moffit.custody.case_db import CaseManager
from moffit.ingestion.paysim_loader import PaySimLoader
from moffit.detection.pattern_detector import FraudPatternDetector
from moffit.timeline.reconstructor import TimelineReconstructor
from moffit.reporting.pdf_report import ForensicReportGenerator

app = FastAPI(title="MOFFIT Web Dashboard")

# Ensure templates directory exists and is registered
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Initialize CaseManager (assumes a default DB if not specified,
# for tests we might override this or use a test DB in environment variable)
DB_PATH = os.environ.get("MOFFIT_DB", "moffit.db")
manager = CaseManager(DB_PATH)

# Global dictionary to track analysis status
analysis_status: Dict[str, Dict[str, Any]] = {}

def get_db() -> CaseManager:
    # A simple way to inject dependency or use the global one.
    return manager

def run_analysis_task(case_id: str, db_manager: CaseManager):
    """Background task to run forensic analysis on a case."""
    try:
        evidence_list = db_manager.get_evidence(case_id)
        if not evidence_list:
            analysis_status[case_id] = {"analyzing": False, "findings_count": 0, "error": "No evidence found"}
            return

        loader = PaySimLoader()
        detector = FraudPatternDetector()

        all_findings = []

        for evidence in evidence_list:
            filepath = evidence.filename
            if not os.path.exists(filepath):
                continue

            df_raw = loader.load_csv(filepath)
            df = loader.normalize(df_raw)

            findings = detector.detect_all(df)
            all_findings.extend(findings)

        if all_findings:
            db_manager.add_findings_bulk(case_id, all_findings)

        # Update case summary findings count
        summary = db_manager.get_case_summary(case_id)
        findings_count = summary.get("findings_count", 0)

        analysis_status[case_id] = {"analyzing": False, "findings_count": findings_count}
    except Exception as e:
        print(f"Analysis error for case {case_id}: {e}")
        analysis_status[case_id] = {"analyzing": False, "findings_count": 0, "error": str(e)}

@app.get("/", response_class=HTMLResponse)
async def list_cases(request: Request):
    cases = manager.list_cases()
    summaries = []
    for case in cases:
        summaries.append(manager.get_case_summary(case.id))

    return templates.TemplateResponse(
        request=request, name="index.html", context={"case_summaries": summaries}
    )

@app.post("/case")
async def create_case(
    name: str = Form(...),
    investigator: str = Form(...),
    description: str = Form("")
):
    case = manager.create_case(name=name, description=description, investigator=investigator)
    return RedirectResponse(url=f"/case/{case.id}", status_code=303)

@app.get("/case/{id}", response_class=HTMLResponse)
async def case_detail(request: Request, id: str):
    summary = manager.get_case_summary(id)
    evidence = manager.get_evidence(id)
    findings = manager.get_findings(id)

    # Sort and cap findings (top 100 by severity, then confidence)
    sev_map = {"high": 3, "medium": 2, "low": 1}
    def sort_key(f):
        return (sev_map.get(f.severity.lower(), 0), f.confidence, f.amount if hasattr(f, 'amount') else 0)

    sorted_findings = sorted(findings, key=sort_key, reverse=True)
    top_findings = sorted_findings[:100]

    # Extract pattern counts for chart
    pattern_counts_dict = {}
    for f in findings:
        pattern_counts_dict[f.finding_type] = pattern_counts_dict.get(f.finding_type, 0) + 1

    pattern_labels = list(pattern_counts_dict.keys())
    pattern_counts = list(pattern_counts_dict.values())

    # Status
    status_info = analysis_status.get(id, {"analyzing": False})
    is_analyzing = status_info.get("analyzing", False)

    return templates.TemplateResponse(
        request=request, name="case.html", context={
            "summary": summary,
            "evidence": evidence,
            "top_findings": top_findings,
            "pattern_labels": pattern_labels,
            "pattern_counts": pattern_counts,
            "is_analyzing": is_analyzing
        }
    )

@app.post("/case/{id}/analyze")
async def analyze_case(id: str, background_tasks: BackgroundTasks):
    analysis_status[id] = {"analyzing": True, "findings_count": 0}
    background_tasks.add_task(run_analysis_task, id, manager)
    return {"status": "started"}

@app.get("/case/{id}/status")
async def case_status(id: str):
    status = analysis_status.get(id)
    if not status:
        # If not in dict, maybe it never started or we restarted the server. Check DB.
        summary = manager.get_case_summary(id)
        return {"analyzing": False, "findings_count": summary.get("findings_count", 0)}
    return status

@app.get("/case/{id}/timeline/{account}", response_class=HTMLResponse)
async def case_timeline(request: Request, id: str, account: str):
    # Retrieve evidence and load dataframe to get events
    evidence_list = manager.get_evidence(id)
    findings = manager.get_findings(id)

    loader = PaySimLoader()
    reconstructor = TimelineReconstructor()

    all_events = []

    for evidence in evidence_list:
        filepath = evidence.filename
        if os.path.exists(filepath):
            df_raw = loader.load_csv(filepath)
            df = loader.normalize(df_raw)
            # Filter findings to just this account
            acct_findings = [f for f in findings if account in f.account_ids]

            events = reconstructor.build_account_timeline(df, account)
            # Annotate with the specific findings for this account (need them as dicts)
            findings_dicts = [{"pattern": f.finding_type, "step_start": f.step_start, "step_end": f.step_end} for f in acct_findings]
            annotated_events = reconstructor.annotate_events(events, findings_dicts)
            all_events.extend(annotated_events)

    # Generate narrative
    acct_findings_all = [f for f in findings if account in f.account_ids]
    findings_dicts_all = [{"pattern": f.finding_type, "step_start": f.step_start, "step_end": f.step_end} for f in acct_findings_all]
    narrative = reconstructor.generate_narrative(all_events, account, findings_dicts_all)

    return templates.TemplateResponse(
        request=request, name="timeline.html", context={
            "case_id": id,
            "account_id": account,
            "events": all_events,
            "narrative": narrative
        }
    )

@app.get("/case/{id}/report")
async def generate_report(id: str):
    summary = manager.get_case_summary(id)
    evidence = manager.get_evidence(id)
    findings = manager.get_findings(id)

    generator = ForensicReportGenerator()
    report_path = f"report_{id}.pdf"

    # We need to construct timelines for findings that are severe to add to report.
    # The generator expects timelines as a mapping account_id -> list of events dicts.
    loader = PaySimLoader()
    reconstructor = TimelineReconstructor()

    # Build dictionary for custody
    custody_items = []
    for ev in evidence:
        custody_items.append({
            "type": "PaySim CSV",
            "filename": ev.filename,
            "sha256": ev.sha256_hash,
            "acquired_at": ev.acquired_at.isoformat()
        })

    custody = {
        "items": custody_items,
        "manifest_hash": "N/A" # Ideally computed
    }

    # Format findings as expected by PDF report
    findings_dicts = []
    accounts_to_timeline = set()
    for f in findings:
        findings_dicts.append({
            "severity": f.severity,
            "pattern": f.finding_type,
            "finding_type": f.finding_type,
            "account_ids": f.account_ids,
            "step_start": f.step_start,
            "step_end": f.step_end,
            "confidence": f.confidence,
            "description": f.description
        })
        if f.severity.lower() == "high":
            for acc in f.account_ids:
                if acc != "DATASET":
                    accounts_to_timeline.add(acc)

    timeline_map = {}

    # Cap timelines: top accounts by finding amount-relevance (report is capped
    # at top-100 findings anyway; timelines for a handful of accounts suffice).
    MAX_TIMELINE_ACCOUNTS = 5
    top_accounts = list(accounts_to_timeline)[:MAX_TIMELINE_ACCOUNTS]

    # Load evidence CSV ONCE, reuse for all accounts
    df = None
    for ev in evidence:
        if os.path.exists(ev.filename) and str(ev.filename).lower().endswith(".csv"):
            df = loader.normalize(loader.load_csv(ev.filename))
            break

    if df is not None:
        for acc in top_accounts:
            acct_findings = [fd for fd in findings_dicts if acc in fd["account_ids"]]
            events = reconstructor.build_account_timeline(df, acc)
            annotated = reconstructor.annotate_events(events, acct_findings)
            if annotated:
                timeline_map[acc] = reconstructor.to_dict_list(annotated)

    # Narrative: use the reconstructor's generator for the first timeline account,
    # falling back to a generic line for cases with no timelines.
    overall_narrative = f"This report covers the forensic investigation of case '{summary['case']['name']}'."
    if timeline_map and df is not None:
        first_acc = next(iter(timeline_map))
        acct_findings = [fd for fd in findings_dicts if first_acc in fd["account_ids"]]
        events = reconstructor.build_account_timeline(df, first_acc)
        events = reconstructor.annotate_events(events, acct_findings)
        overall_narrative = reconstructor.generate_narrative(events, first_acc, acct_findings)

    generator.generate(
        case=summary["case"],
        findings=findings_dicts,
        timeline_map=timeline_map,
        custody=custody,
        narrative=overall_narrative,
        output_path=report_path,
    )

    return FileResponse(report_path, media_type="application/pdf", filename=f"MOFFIT_report_{id}.pdf")