"""Tests for ledger.py dedupe and load/save logic."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.ledger import append_transactions, load_ledger, save_ledger


@pytest.fixture
def tmp_csv(tmp_path):
    return tmp_path / "test_expenses.csv"


def make_txn(date, description, amount, raw_details=None):
    return {
        "date": date,
        "description": description,
        "amount": amount,
        "type": "debit" if amount < 0 else "credit",
        "raw_details": raw_details or description,
    }


class TestLoadLedger:
    def test_returns_empty_df_when_file_missing(self, tmp_csv):
        df = load_ledger(tmp_csv)
        assert df.empty
        assert "date" in df.columns
        assert "category" in df.columns

    def test_loads_existing_csv(self, tmp_csv):
        # Write a small CSV
        data = pd.DataFrame([{
            "date": "2026-03-01",
            "description": "TESCO",
            "raw_details": "POS TESCO",
            "amount": -50.00,
            "type": "debit",
            "category": "Groceries",
            "source_file": "test.pdf",
            "ingested_at": "2026-03-01T00:00:00",
        }])
        data.to_csv(tmp_csv, index=False)

        df = load_ledger(tmp_csv)
        assert len(df) == 1
        assert df.iloc[0]["description"] == "TESCO"


class TestAppendTransactions:
    def test_appends_new_transactions(self, tmp_csv):
        df = load_ledger(tmp_csv)
        txns = [
            make_txn("2026-03-01", "TESCO", -50.00, "POS TESCO LIMERICK"),
            make_txn("2026-03-02", "LIDL", -30.00, "POS LIDL"),
        ]

        df, added, dupes = append_transactions(df, txns, "test.pdf")
        assert added == 2
        assert dupes == 0
        assert len(df) == 2

    def test_deduplicates_exact_matches(self, tmp_csv):
        df = load_ledger(tmp_csv)
        txns = [make_txn("2026-03-01", "TESCO", -50.00, "POS TESCO LIMERICK")]
        df, _, _ = append_transactions(df, txns, "test.pdf")

        # Append the same transaction again
        same_txns = [make_txn("2026-03-01", "TESCO", -50.00, "POS TESCO LIMERICK")]
        df, added, dupes = append_transactions(df, same_txns, "test.pdf")

        assert added == 0
        assert dupes == 1
        assert len(df) == 1

    def test_allows_different_amounts_same_date(self, tmp_csv):
        df = load_ledger(tmp_csv)
        txns = [
            make_txn("2026-03-01", "TESCO", -50.00, "POS TESCO LIMERICK"),
        ]
        df, _, _ = append_transactions(df, txns, "test.pdf")

        # Different amount = not a duplicate
        diff_txns = [make_txn("2026-03-01", "TESCO", -75.00, "POS TESCO LIMERICK")]
        df, added, dupes = append_transactions(df, diff_txns, "test.pdf")

        assert added == 1
        assert dupes == 0
        assert len(df) == 2

    def test_allows_different_details_same_date_amount(self, tmp_csv):
        df = load_ledger(tmp_csv)
        txns = [make_txn("2026-03-01", "TESCO", -50.00, "POS TESCO LIMERICK")]
        df, _, _ = append_transactions(df, txns, "test.pdf")

        # Different raw_details = not a duplicate
        diff_txns = [make_txn("2026-03-01", "TESCO", -50.00, "POS TESCO DUBLIN")]
        df, added, dupes = append_transactions(df, diff_txns, "test.pdf")

        assert added == 1
        assert dupes == 0

    def test_handles_empty_input(self, tmp_csv):
        df = load_ledger(tmp_csv)
        df, added, dupes = append_transactions(df, [], "test.pdf")
        assert added == 0
        assert dupes == 0


class TestSaveLedger:
    def test_saves_and_reloads(self, tmp_csv):
        df = load_ledger(tmp_csv)
        txns = [
            make_txn("2026-03-01", "TESCO", -50.00, "POS TESCO"),
            make_txn("2026-03-15", "SALARY", 3250.00, "SALARY DELL"),
        ]
        df, _, _ = append_transactions(df, txns, "stmt.pdf")
        save_ledger(df, tmp_csv)

        reloaded = load_ledger(tmp_csv)
        assert len(reloaded) == 2
        assert reloaded.iloc[0]["amount"] == -50.00
