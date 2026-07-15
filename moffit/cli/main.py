from moffit.reporting.pdf_report import ForensicReportGenerator
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
import os
from typing import Optional

from moffit.custody.case_db import CaseManager
from moffit.ingestion.paysim_loader import PaySimLoader
from moffit.detection.pattern_detector import FraudPatternDetector
from moffit.timeline.reconstructor import TimelineReconstructor

app = typer.Typer(help="MOFFIT (Mobile Money Fraud Forensic Investigation Toolkit) CLI")
case_app = typer.Typer(help="Manage investigation cases")
app.add_typer(case_app, name="case")
ml_app = typer.Typer(help="ML fraud classification")
app.add_typer(ml_app, name="ml")

console = Console()

def get_case_manager() -> CaseManager:
    """
    Helper to get CaseManager instance.

    Returns:
        CaseManager: An initialized CaseManager.
    """
    db_path = os.getenv("CASE_DB_PATH", "sqlite:///cases.db")
    # if string starts with sqlite:///, remove it for CaseManager which expects just the path
    if db_path.startswith("sqlite:///"):
        db_path = db_path[10:]
    elif db_path.startswith("sqlite://"):
        db_path = db_path[9:]
    return CaseManager(db_path)

@app.command()
def info() -> None:
    """
    Prints basic info about MOFFIT.
    """
    console.print(Panel.fit("MOFFIT: Mobile Money Fraud Forensic Investigation Toolkit", title="MOFFIT", border_style="blue"))

@case_app.command("new")
def case_new(
    name: str = typer.Option(..., "--name", help="Name of the case"),
    investigator: str = typer.Option(..., "--investigator", help="Name of the investigator"),
    desc: Optional[str] = typer.Option(None, "--desc", help="Description of the case")
) -> None:
    """
    Creates a new case and prints the case ID.

    Args:
        name (str): The name of the case.
        investigator (str): The name of the investigator.
        desc (Optional[str]): A description of the case.
    """
    manager = get_case_manager()
    case = manager.create_case(name=name, description=desc or "", investigator=investigator)
    console.print(Panel.fit(f"[green]Case created successfully![/green]\nCase ID: [bold]{case.id}[/bold]", title="Success", border_style="green"))

@case_app.command("list")
def case_list() -> None:
    """
    Displays a Rich table listing all investigation cases.
    """
    manager = get_case_manager()
    cases = manager.list_cases()

    table = Table(title="Forensic Cases")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="magenta")
    table.add_column("Investigator", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Created")
    table.add_column("Findings", justify="right")

    for case in cases:
        summary = manager.get_case_summary(case.id)
        findings_count = summary.get("findings_count", 0)
        table.add_row(
            str(case.id),
            str(case.name),
            str(case.investigator),
            str(case.status),
            str(case.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            str(findings_count)
        )

    console.print(table)

@app.command()
def ingest(
    case_id: str = typer.Option(..., "--case-id", help="UUID of the case"),
    file_path: str = typer.Option(..., "--file", help="Path to the PaySim CSV file")
) -> None:
    """
    Loads a PaySim CSV, registers it as Evidence, and prints ingestion stats.

    Args:
        case_id (str): The UUID of the case.
        file_path (str): The path to the CSV file to ingest.
    """
    manager = get_case_manager()
    loader = PaySimLoader()

    if not os.path.exists(file_path):
        console.print(f"[red]Error: File {file_path} not found.[/red]")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Ingesting evidence...", total=100)

        # Simulate progress for loading
        progress.update(task, advance=30, description="[cyan]Loading CSV data...")
        df = loader.load_csv(file_path)
        row_count = len(df)

        progress.update(task, advance=30, description="[cyan]Normalizing data...")
        normalized_df = loader.normalize(df)

        progress.update(task, advance=30, description="[cyan]Hashing and registering evidence...")
        evidence = manager.add_evidence(case_id=case_id, filepath=file_path)

        progress.update(task, advance=10, description="[green]Ingestion complete!")

    success_msg = (
        f"[green]Successfully ingested and registered evidence![/green]\n"
        f"Row Count: [bold]{row_count}[/bold]\n"
        f"SHA-256 Hash: [bold]{evidence.sha256_hash}[/bold]\n"
        f"MD5 Hash: [bold]{evidence.md5_hash}[/bold]\n"
        f"Evidence ID: [bold]{evidence.id}[/bold]"
    )
    console.print(Panel.fit(success_msg, title="Success", border_style="green"))


def get_severity_badge(severity: str) -> str:
    """
    Returns a colored Rich markup string based on finding severity.

    Args:
        severity (str): The severity level (e.g., 'high', 'medium', 'low').

    Returns:
        str: A Rich markup string representing the badge.
    """
    severity = severity.lower()
    if severity == "high":
        return "[white on red] HIGH [/white on red]"
    elif severity == "medium":
        return "[white on yellow] MEDIUM [/white on yellow]"
    elif severity == "low":
        return "[white on green] LOW [/white on green]"
    return severity

@app.command()
def analyze(
    case_id: str = typer.Option(..., "--case-id", help="UUID of the case"),
    account: Optional[str] = typer.Option(None, "--account", help="Optional account ID to filter by")
) -> None:
    """
    Runs FraudPatternDetector, saves findings to the DB, and prints a Rich table.

    Args:
        case_id (str): The UUID of the case to analyze.
        account (Optional[str]): An optional account ID to focus the analysis on.
    """
    manager = get_case_manager()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Running fraud pattern detection...", total=100)

        # Stub data loading
        progress.update(task, advance=10, description="[cyan]Locating case evidence...")
        evidence_items = manager.get_evidence(case_id)
        csv_paths = [e.filename for e in evidence_items if str(e.filename).lower().endswith(".csv")]
        if not csv_paths:
            console.print("[red]No CSV evidence registered for this case. Run 'moffit ingest' first.[/red]")
            raise typer.Exit(1)

        progress.update(task, advance=10, description="[cyan]Loading case data...")
        loader = PaySimLoader()
        dummy_df = loader.normalize(loader.load_csv(csv_paths[0]))

        progress.update(task, advance=40, description="[cyan]Analyzing patterns...")
        detector = FraudPatternDetector()
        if account is not None and not dummy_df.empty:
            filtered_df = dummy_df[(dummy_df["sender_id"] == account) | (dummy_df["receiver_id"] == account)]
            findings = detector.analyze(filtered_df)
        else:
            findings = detector.analyze(dummy_df)

        progress.update(task, advance=30, description="[cyan]Saving findings to DB...")
        
        payload = []
        for f in findings:
            severity = "high" if f["confidence"] >= 0.9 else ("medium" if f["confidence"] >= 0.75 else "low")
            payload.append({
                "finding_type": f["pattern"],
                "severity": severity,
                "description": f["description"],
                "account_ids": [f["account_id"]],
                "step_start": f["step_start"],
                "step_end": f["step_end"],
                "confidence": f["confidence"],
            })
        manager.add_findings_bulk(case_id, payload)

        progress.update(task, advance=10, description="[green]Analysis complete!")

    # Print rich table
    table = Table(title=f"Fraud Analysis Findings (Case: {case_id})")
    table.add_column("Severity", justify="center")
    table.add_column("Pattern", style="cyan")
    table.add_column("Account(s)", style="magenta")
    table.add_column("Steps")
    table.add_column("Confidence%", justify="right")

    for f in findings:
        table.add_row(
            get_severity_badge("high" if f["confidence"] >= 0.9 else ("medium" if f["confidence"] >= 0.75 else "low")),
            f["pattern"],
            f["account_id"],
            f"{f['step_start']}-{f['step_end']}",
            f"{f['confidence'] * 100:.0f}%"
        )

    console.print(table)
    console.print(Panel.fit("[green]Successfully saved findings to database.[/green]", title="Success", border_style="green"))


@app.command()
def timeline(
    case_id: str = typer.Option(..., "--case-id", help="UUID of the case"),
    account: str = typer.Option(..., "--account", help="Account ID to generate timeline for")
) -> None:
    """
    Prints a chronological Rich table of events for a specific account.

    Args:
        case_id (str): The UUID of the case.
        account (str): The account ID to generate the timeline for.
    """

    manager = get_case_manager()
    evidence_items = manager.get_evidence(case_id)
    csv_paths = [e.filename for e in evidence_items if str(e.filename).lower().endswith(".csv")]
    if not csv_paths:
            console.print("[red]No CSV evidence registered for this case. Run 'moffit ingest' first.[/red]")
            raise typer.Exit(1)

    loader = PaySimLoader()
    try:
            df = loader.normalize(loader.load_csv(csv_paths[0]))
    except Exception as e:
            console.print(f"[red]Failed to load CSV evidence: {str(e)}[/red]")
            raise typer.Exit(1)

        # Findings for THIS account only: annotate_events matches by step range,
        # so unfiltered findings would cross-contaminate annotations (and loop
        # over the full findings table per event).
    findings_dicts = [
            {"pattern": f.finding_type, "step_start": f.step_start, "step_end": f.step_end}
            for f in manager.get_findings(case_id)
            if account in (f.account_ids or [])
        ]

    reconstructor = TimelineReconstructor()
    events = reconstructor.build_account_timeline(df, account_id=account)
    events = reconstructor.annotate_events(events, findings_dicts)

    if not events:
            console.print(f"[yellow]No transactions found for account {account} in this case's evidence.[/yellow]")
            raise typer.Exit(0)

    table = Table(title=f"Transaction Timeline: {account}")
    table.add_column("Step", justify="right", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Amount", justify="right", style="green")
    table.add_column("Balance Before", justify="right")
    table.add_column("Balance After", justify="right")
    table.add_column("Annotation", style="yellow")

    for e in events:
            table.add_row(
                str(e.step),
                e.event_type,
                f"{e.amount:.2f}",
                f"{e.balance_before:.2f}",
                f"{e.balance_after:.2f}",
                e.annotation,
            )

    console.print(table)

    narrative = reconstructor.generate_narrative(events, account, findings_dicts)
    console.print(Panel.fit(narrative, title="Narrative", border_style="blue"))

@app.command()
def report(
    case_id: str = typer.Option(..., "--case-id", help="UUID of the case"),
    output: str = typer.Option(..., "--output", help="Output path for the PDF report")
) -> None:
    """
    Generates a PDF report for the given case.

    Args:
        case_id (str): The UUID of the case.
        output (str): The output file path for the PDF report.
    """
    manager = get_case_manager()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Generating PDF report...", total=100)

        progress.update(task, advance=10, description="[cyan]Loading case summary...")
        try:
            summary = manager.get_case_summary(case_id)
            case_info = summary.get("case", {"id": case_id})
        except Exception as e:
            console.print(f"[red]Failed to load case {case_id}: {str(e)}[/red]")
            raise typer.Exit(1)

        progress.update(task, advance=10, description="[cyan]Loading evidence and custody manifest...")
        evidence_items = manager.get_evidence(case_id)

        # Build custody manifest
        from moffit.custody.integrity import EvidenceManifest
        manifest = EvidenceManifest()
        for e in evidence_items:
            # We don't want to re-hash the files as they might not exist anymore,
            # we just construct the custody dict from the db.
            manifest.items.append({
                "type": "file",
                "filepath": e.filename,
                "filename": e.filename.split('/')[-1] if e.filename else '',
                "file_size": e.file_size,
                "sha256": e.sha256_hash,
                "md5": e.md5_hash,
                "acquired_at": e.acquired_at.isoformat() if e.acquired_at else '',
                "notes": e.notes or ""
            })
        custody = manifest.finalize(case_id, case_info.get("investigator", "Unknown"))

        progress.update(task, advance=10, description="[cyan]Loading findings...")
        findings_objs = manager.get_findings(case_id)
        findings = []
        for f in findings_objs:
            findings.append({
                "id": f.id,
                "finding_type": f.finding_type,
                "severity": f.severity,
                "description": f.description,
                "account_ids": f.account_ids,
                "step_start": f.step_start,
                "step_end": f.step_end,
                "confidence": f.confidence,
                "created_at": f.created_at.isoformat() if f.created_at else ''
            })

        progress.update(task, advance=20, description="[cyan]Reconstructing timelines...")

        # Get CSV evidence for timelines
        csv_paths = [e.filename for e in evidence_items if str(e.filename).lower().endswith(".csv")]

        timeline_map = {}
        narrative = ""

        if csv_paths and findings:
            loader = PaySimLoader()
            try:
                df = loader.normalize(loader.load_csv(csv_paths[0]))

                # Get top flagged accounts
                # Sort findings by severity then confidence
                sev_map = {"high": 3, "medium": 2, "low": 1}
                sorted_f = sorted(findings, key=lambda x: (sev_map.get(x.get('severity', 'low').lower(), 0), x.get('confidence', 0)), reverse=True)

                top_accounts = []
                for f in sorted_f:
                    accs = f.get('account_ids', [])
                    for a in accs:
                        if a not in top_accounts:
                            top_accounts.append(a)
                    if len(top_accounts) >= 5: # Limit to top 5 accounts to prevent massive reports
                        break

                top_accounts = top_accounts[:5]
                reconstructor = TimelineReconstructor()

                first_account_narrative = ""

                for account in top_accounts:
                    events = reconstructor.build_account_timeline(df, account_id=account)

                    acc_findings = [f for f in findings if account in (f.get('account_ids') or [])]
                    events = reconstructor.annotate_events(events, acc_findings)

                    timeline_map[account] = reconstructor.to_dict_list(events)

                    if not first_account_narrative and events:
                        first_account_narrative = reconstructor.generate_narrative(events, account, acc_findings)

                narrative = first_account_narrative

            except Exception as e:
                console.print(f"[yellow]Failed to load CSV for timeline reconstruction: {str(e)}[/yellow]")
        else:
            if not findings:
                narrative = "No findings were recorded for this case."
            else:
                narrative = "Timeline data could not be reconstructed because no CSV evidence is registered for this case."

        progress.update(task, advance=40, description="[cyan]Rendering PDF report...")
        generator = ForensicReportGenerator()
        generator.generate(
            case=case_info,
            findings=findings,
            timeline_map=timeline_map,
            custody=custody,
            narrative=narrative,
            output_path=output
        )

        progress.update(task, advance=10, description="[green]Report generation complete!")

    console.print(Panel.fit(f"[green]Successfully generated report at {output}[/green]", title="Success", border_style="green"))

@ml_app.command("train")
def ml_train(
    case_id: str = typer.Option(..., "--case-id", help="UUID of the case")
) -> None:
    """
    Trains ML models on the case evidence and produces evaluation artifacts.
    """
    from moffit.ml.evaluate import evaluate_all
    import json

    manager = get_case_manager()
    evidence_items = manager.get_evidence(case_id)
    csv_paths = [e.filename for e in evidence_items if str(e.filename).lower().endswith(".csv")]
    if not csv_paths:
        console.print("[red]No CSV evidence registered for this case.[/red]")
        raise typer.Exit(1)

    loader = PaySimLoader()
    df = loader.normalize(loader.load_csv(csv_paths[0]))

    output_dir = os.path.join("reports", "ml", case_id)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Training models...", total=100)

        progress.update(task, advance=50, description="[cyan]Extracting features and training...")
        metrics = evaluate_all(df, output_dir)

        progress.update(task, advance=50, description="[green]Training complete!")

    table = Table(title="Model Evaluation Metrics")
    table.add_column("Model", style="cyan")
    table.add_column("Precision", justify="right")
    table.add_column("Recall", justify="right")
    table.add_column("F1-Score", justify="right")
    table.add_column("AUPRC", justify="right")
    table.add_column("ROC-AUC", justify="right")

    for model_name, m in metrics.items():
        table.add_row(
            model_name,
            f"{m['precision']:.3f}",
            f"{m['recall']:.3f}",
            f"{m['f1']:.3f}",
            f"{m['auprc']:.3f}",
            f"{m['roc_auc']:.3f}"
        )

    console.print(table)
    console.print(Panel.fit(f"[green]Artifacts saved to {output_dir}[/green]", title="Success", border_style="green"))


@ml_app.command("rank")
def ml_rank(
    case_id: str = typer.Option(..., "--case-id", help="UUID of the case"),
    top: int = typer.Option(20, "--top", help="Number of top accounts to display")
) -> None:
    """
    Ranks accounts by fraud probability using the trained XGBoost model.
    """
    from moffit.ml.features import FeatureEngineer
    from moffit.ml.classifier import FraudClassifier

    manager = get_case_manager()
    evidence_items = manager.get_evidence(case_id)
    csv_paths = [e.filename for e in evidence_items if str(e.filename).lower().endswith(".csv")]
    if not csv_paths:
        console.print("[red]No CSV evidence registered for this case.[/red]")
        raise typer.Exit(1)

    output_dir = os.path.join("reports", "ml", case_id)
    model_path = os.path.join(output_dir, "xgboost_model.joblib")
    if not os.path.exists(model_path):
        console.print("[red]No trained XGBoost model found. Run 'moffit ml train' first.[/red]")
        raise typer.Exit(1)

    loader = PaySimLoader()
    df = loader.normalize(loader.load_csv(csv_paths[0]))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Ranking accounts...", total=None)

        fe = FeatureEngineer()
        X = fe.transform(df)

        clf = FraudClassifier.load(model_path)
        ranked_df = clf.rank_accounts(df, X)

        progress.update(task, completed=100)

    table = Table(title=f"Top {top} Accounts by Fraud Probability")
    table.add_column("Rank", justify="right", style="cyan")
    table.add_column("Account ID", style="magenta")
    table.add_column("Max Fraud Probability", justify="right", style="yellow")
    table.add_column("Transaction Count", justify="right")

    top_df = ranked_df.head(top)
    for i, row in top_df.iterrows():
        table.add_row(
            str(i + 1),
            str(row["account_id"]),
            f"{row['max_fraud_probability']:.4f}",
            str(row["tx_count"])
        )

    console.print(table)


if __name__ == "__main__":
    app()
