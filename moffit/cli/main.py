import typer

app = typer.Typer(help="MOFFIT (Mobile Money Fraud Forensic Investigation Toolkit) CLI")

@app.command()
def info():
    """Prints basic info about MOFFIT."""
    typer.echo("MOFFIT: Mobile Money Fraud Forensic Investigation Toolkit")

if __name__ == "__main__":
    app()
