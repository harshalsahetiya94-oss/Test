"""CSV ledger: load, append with deduplication, and save."""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

LEDGER_COLUMNS = [
    "date",
    "description",
    "raw_details",
    "amount",
    "type",
    "category",
    "source_file",
    "ingested_at",
]


def load_ledger(path: Path) -> pd.DataFrame:
    """Load the ledger CSV. Returns an empty DataFrame with correct columns if file doesn't exist."""
    if path.exists() and path.stat().st_size > 0:
        df = pd.read_csv(path, parse_dates=["date"])
        # Ensure all columns exist
        for col in LEDGER_COLUMNS:
            if col not in df.columns:
                df[col] = None
        return df

    return pd.DataFrame(columns=LEDGER_COLUMNS)


def append_transactions(
    df: pd.DataFrame,
    new_txns: list[dict],
    source_file: str,
) -> tuple[pd.DataFrame, int, int]:
    """Append new transactions to the ledger, deduplicating by (date, raw_details, amount).

    Returns:
        Tuple of (updated DataFrame, num_added, num_duplicates).
    """
    if not new_txns:
        return df, 0, 0

    now = datetime.now(timezone.utc).isoformat()
    new_rows = []
    for txn in new_txns:
        new_rows.append({
            "date": txn["date"],
            "description": txn["description"],
            "raw_details": txn.get("raw_details", txn["description"]),
            "amount": txn["amount"],
            "type": txn["type"],
            "category": txn.get("category", ""),
            "source_file": source_file,
            "ingested_at": now,
        })

    new_df = pd.DataFrame(new_rows)

    if df.empty:
        return new_df, len(new_rows), 0

    # Deduplicate: a transaction is a duplicate if (date, raw_details, amount) already exists
    dedupe_keys = ["date", "raw_details", "amount"]

    # Normalize date columns for comparison
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    new_df["date"] = pd.to_datetime(new_df["date"]).dt.strftime("%Y-%m-%d")

    existing_keys = set(df[dedupe_keys].apply(lambda r: (str(r["date"]), str(r["raw_details"]), float(r["amount"])), axis=1))

    mask = new_df[dedupe_keys].apply(
        lambda r: (str(r["date"]), str(r["raw_details"]), float(r["amount"])) not in existing_keys,
        axis=1,
    )

    unique_new = new_df[mask]
    num_added = len(unique_new)
    num_dupes = len(new_df) - num_added

    if num_added > 0:
        result = pd.concat([df, unique_new], ignore_index=True)
    else:
        result = df

    return result, num_added, num_dupes


def save_ledger(df: pd.DataFrame, path: Path) -> None:
    """Save the ledger DataFrame to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
