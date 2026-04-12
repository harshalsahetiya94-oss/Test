"""CLI entrypoint — alternative to the web interface."""

from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
LEDGER_PATH = OUTPUT_DIR / "expenses.csv"


@click.group()
def cli():
    """BOI Expense Tracker — Bank of Ireland statement parser and expense categorizer."""
    pass


@cli.command()
def serve():
    """Start the web interface."""
    from src.app import main
    main()


@cli.command()
def ingest():
    """Process all PDFs/images in input/ and add to ledger."""
    from rich.console import Console
    from rich.progress import Progress

    from src.categorize import categorize_transactions
    from src.extract import SUPPORTED_EXTENSIONS, extract_transactions
    from src.ledger import append_transactions, load_ledger, save_ledger

    console = Console()
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = [f for f in INPUT_DIR.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS]

    if not files:
        console.print("[yellow]No supported files found in input/[/yellow]")
        return

    total_added = 0
    total_dupes = 0
    total_claude = 0

    with Progress() as progress:
        task = progress.add_task("Processing files...", total=len(files))
        for f in files:
            try:
                txns = extract_transactions(f)
                txns = categorize_transactions(txns)
                claude_cats = sum(1 for t in txns if t.get("_claude_categorized"))
                total_claude += claude_cats

                df = load_ledger(LEDGER_PATH)
                df, added, dupes = append_transactions(df, txns, f.name)
                save_ledger(df, LEDGER_PATH)
                total_added += added
                total_dupes += dupes

                console.print(f"  [green]✓[/green] {f.name}: {added} new, {dupes} dupes")
            except Exception as e:
                console.print(f"  [red]✗[/red] {f.name}: {e}")
            progress.advance(task)

    console.print(
        f"\n[bold]{total_added}[/bold] new transactions added, "
        f"[bold]{total_dupes}[/bold] duplicates skipped"
    )


@cli.command()
@click.option("--month", required=True, help="Month in YYYY-MM format")
def summary(month):
    """Print monthly summary to terminal."""
    from rich.console import Console

    from src.ledger import load_ledger
    from src.summary import generate_monthly_summary

    console = Console()
    df = load_ledger(LEDGER_PATH)

    if df.empty:
        console.print("[yellow]No transactions in ledger.[/yellow]")
        return

    md = generate_monthly_summary(df, month)
    console.print(md)


if __name__ == "__main__":
    cli()
