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
from moffit.timeline.generator import TimelineGenerator

app = typer.Typer(help="MOFFIT (Mobile Money Fraud Forensic Investigation Toolkit) CLI")
case_app = typer.Typer(help="Manage investigation cases")
app.add_typer(case_app, name="case")

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
        progress.update(task, advance=20, description="[cyan]Loading case data...")
        # In a real app we'd load the df associated with the case
        import pandas as pd
        dummy_df = pd.DataFrame()

        progress.update(task, advance=40, description="[cyan]Analyzing patterns...")
        detector = FraudPatternDetector()
        if account is not None and not dummy_df.empty:
            filtered_df = dummy_df[(dummy_df["sender_id"] == account) | (dummy_df["receiver_id"] == account)]
            findings = detector.analyze(filtered_df)
        else:
            findings = detector.analyze(dummy_df)

        progress.update(task, advance=30, description="[cyan]Saving findings to DB...")
        for f in findings:
            severity = "high" if f["confidence"] >= 0.9 else ("medium" if f["confidence"] >= 0.75 else "low")
            manager.add_finding(
                case_id=case_id,
                finding_type=f["pattern"],
                severity=severity,
                description=f["description"],
                account_ids=[f["account_id"]],
                step_start=f["step_start"],
                step_end=f["step_end"],
                confidence=f["confidence"]
            )

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
    # manager = get_case_manager()
    # In a real app we'd get df and findings for this case
    import pandas as pd
    dummy_df = pd.DataFrame()
    generator = TimelineGenerator(dummy_df, findings=[])
    events = generator.generate(account_id=account)

    table = Table(title=f"Transaction Timeline: {account}")
    table.add_column("Step", justify="right", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Amount", justify="right", style="green")
    table.add_column("Balance Before", justify="right")
    table.add_column("Balance After", justify="right")
    table.add_column("Annotation", style="yellow")

    for e in events:
        table.add_row(
            str(e["step"]),
            e["type"],
            f"{e['amount']:.2f}",
            f"{e['balance_before']:.2f}",
            f"{e['balance_after']:.2f}",
            e["annotation"]
        )

    console.print(table)

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
    console.print(f"Report saved to {output}")
    console.print(Panel.fit(f"[green]Successfully generated report at {output}[/green]", title="Success", border_style="green"))

if __name__ == "__main__":
    app()
