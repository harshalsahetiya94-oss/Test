"""Generate monthly expense summaries in markdown."""

from pathlib import Path

import pandas as pd


def generate_monthly_summary(df: pd.DataFrame, year_month: str) -> str:
    """Generate a markdown summary for a given YYYY-MM month.

    Args:
        df: The full ledger DataFrame.
        year_month: Month string like "2026-03".

    Returns:
        Markdown string with the monthly summary.
    """
    df["date"] = pd.to_datetime(df["date"])
    month_df = df[df["date"].dt.strftime("%Y-%m") == year_month].copy()

    if month_df.empty:
        return f"# Expense Summary — {year_month}\n\nNo transactions found for this month.\n"

    total_txns = len(month_df)
    credits = month_df[month_df["amount"] > 0]["amount"].sum()
    debits = month_df[month_df["amount"] < 0]["amount"].sum()
    net = credits + debits

    start_date = month_df["date"].min().strftime("%d %b %Y")
    end_date = month_df["date"].max().strftime("%d %b %Y")

    lines = [
        f"# Expense Summary — {year_month}",
        "",
        f"**Period:** {start_date} to {end_date}",
        f"**Total transactions:** {total_txns}",
        "",
        "## Overview",
        "",
        f"| Metric | Amount |",
        f"|--------|--------|",
        f"| Total Income | €{credits:,.2f} |",
        f"| Total Spend | €{abs(debits):,.2f} |",
        f"| Net | €{net:,.2f} |",
        "",
    ]

    # Spend by category (debits only)
    spend_df = month_df[month_df["amount"] < 0].copy()
    if not spend_df.empty:
        cat_spend = (
            spend_df.groupby("category")["amount"]
            .sum()
            .abs()
            .sort_values(ascending=False)
        )
        lines.append("## Spend by Category")
        lines.append("")
        lines.append("| Category | Amount |")
        lines.append("|----------|--------|")
        for cat, amt in cat_spend.items():
            lines.append(f"| {cat} | €{amt:,.2f} |")
        lines.append("")

    # Top 10 merchants by total spend
    if not spend_df.empty:
        merchant_spend = (
            spend_df.groupby("description")["amount"]
            .sum()
            .abs()
            .sort_values(ascending=False)
            .head(10)
        )
        lines.append("## Top 10 Merchants by Spend")
        lines.append("")
        lines.append("| Merchant | Total |")
        lines.append("|----------|-------|")
        for merchant, amt in merchant_spend.items():
            lines.append(f"| {merchant} | €{amt:,.2f} |")
        lines.append("")

    # Recurring subscriptions detection (same description in 2+ months)
    full_df = df.copy()
    full_df["ym"] = full_df["date"].dt.to_period("M")
    debit_full = full_df[full_df["amount"] < 0]
    if not debit_full.empty:
        monthly_counts = debit_full.groupby("description")["ym"].nunique()
        recurring = monthly_counts[monthly_counts >= 2]
        if not recurring.empty:
            lines.append(f"## Recurring Charges ({len(recurring)} detected)")
            lines.append("")
            for desc in recurring.index:
                lines.append(f"- {desc}")
            lines.append("")

    # Needs review section
    review_df = month_df[month_df["category"].isin(["Other", "Transfers"])]
    if not review_df.empty:
        lines.append("## Needs Review")
        lines.append("")
        lines.append("| Date | Description | Amount | Category |")
        lines.append("|------|-------------|--------|----------|")
        for _, row in review_df.iterrows():
            lines.append(
                f"| {row['date'].strftime('%Y-%m-%d')} | {row['description']} "
                f"| €{abs(row['amount']):,.2f} | {row['category']} |"
            )
        lines.append("")

    return "\n".join(lines)


def save_summary(df: pd.DataFrame, year_month: str, output_dir: Path) -> Path:
    """Generate and save a monthly summary markdown file.

    Returns the path to the saved file.
    """
    md = generate_monthly_summary(df, year_month)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"summary_{year_month}.md"
    path.write_text(md)
    return path


def get_months_in_ledger(df: pd.DataFrame) -> list[str]:
    """Return sorted list of YYYY-MM strings present in the ledger."""
    if df.empty:
        return []
    dates = pd.to_datetime(df["date"])
    months = sorted(dates.dt.strftime("%Y-%m").unique())
    return list(months)
