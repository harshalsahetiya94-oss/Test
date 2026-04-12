"""Flask web app for BOI Expense Tracker."""

import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for

from src.categorize import categorize_transactions
from src.extract import SUPPORTED_EXTENSIONS, extract_transactions
from src.ledger import append_transactions, load_ledger, save_ledger
from src.summary import generate_monthly_summary, get_months_in_ledger

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
LEDGER_PATH = OUTPUT_DIR / "expenses.csv"

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "boi-expense-tracker-dev-key")


@app.route("/")
def dashboard():
    """Main dashboard showing expense overview."""
    df = load_ledger(LEDGER_PATH)

    if df.empty:
        return render_template(
            "dashboard.html",
            has_data=False,
            months=[],
        )

    df["date"] = pd.to_datetime(df["date"])
    months = get_months_in_ledger(df)
    selected_month = request.args.get("month", months[-1] if months else None)

    if selected_month:
        month_df = df[df["date"].dt.strftime("%Y-%m") == selected_month]
    else:
        month_df = df

    # Compute stats
    total_txns = len(month_df)
    total_income = month_df[month_df["amount"] > 0]["amount"].sum()
    total_spend = month_df[month_df["amount"] < 0]["amount"].sum()
    net = total_income + total_spend

    # Category breakdown (debits only)
    spend_df = month_df[month_df["amount"] < 0].copy()
    category_data = []
    if not spend_df.empty:
        cat_spend = spend_df.groupby("category")["amount"].sum().abs().sort_values(ascending=False)
        for cat, amt in cat_spend.items():
            pct = (amt / cat_spend.sum()) * 100 if cat_spend.sum() > 0 else 0
            category_data.append({"name": cat, "amount": amt, "percent": pct})

    # Recent transactions
    recent = month_df.sort_values("date", ascending=False).head(20)
    recent_list = recent.to_dict("records")

    return render_template(
        "dashboard.html",
        has_data=True,
        months=months,
        selected_month=selected_month,
        total_txns=total_txns,
        total_income=total_income,
        total_spend=abs(total_spend),
        net=net,
        categories=category_data,
        recent=recent_list,
    )


@app.route("/upload", methods=["GET", "POST"])
def upload():
    """Upload and process statement PDFs or expense screenshots."""
    if request.method == "GET":
        return render_template("upload.html")

    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        flash("No files selected.", "error")
        return redirect(url_for("upload"))

    total_added = 0
    total_dupes = 0
    total_errors = 0
    processed_files = []

    for file in files:
        if not file.filename:
            continue

        ext = Path(file.filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            flash(f"Skipped {file.filename}: unsupported file type ({ext}).", "warning")
            total_errors += 1
            continue

        # Save uploaded file
        INPUT_DIR.mkdir(parents=True, exist_ok=True)
        save_path = INPUT_DIR / file.filename
        file.save(str(save_path))

        try:
            # Extract transactions
            transactions = extract_transactions(save_path)

            # Categorize
            transactions = categorize_transactions(transactions)

            # Load ledger and append
            df = load_ledger(LEDGER_PATH)
            df, added, dupes = append_transactions(df, transactions, file.filename)
            save_ledger(df, LEDGER_PATH)

            total_added += added
            total_dupes += dupes
            processed_files.append(file.filename)

        except Exception as e:
            flash(f"Error processing {file.filename}: {str(e)}", "error")
            total_errors += 1

    if processed_files:
        msg = f"Processed {len(processed_files)} file(s): {total_added} new transactions added"
        if total_dupes > 0:
            msg += f", {total_dupes} duplicates skipped"
        flash(msg, "success")

    return redirect(url_for("dashboard"))


@app.route("/transactions")
def transactions():
    """View all transactions with filtering."""
    df = load_ledger(LEDGER_PATH)

    if df.empty:
        return render_template("transactions.html", has_data=False, transactions=[], categories=[], months=[])

    df["date"] = pd.to_datetime(df["date"])

    # Filters
    month_filter = request.args.get("month", "")
    category_filter = request.args.get("category", "")
    search_filter = request.args.get("search", "")

    months = get_months_in_ledger(df)
    categories = sorted(df["category"].dropna().unique())

    filtered = df.copy()
    if month_filter:
        filtered = filtered[filtered["date"].dt.strftime("%Y-%m") == month_filter]
    if category_filter:
        filtered = filtered[filtered["category"] == category_filter]
    if search_filter:
        filtered = filtered[
            filtered["description"].str.contains(search_filter, case=False, na=False)
        ]

    filtered = filtered.sort_values("date", ascending=False)
    txn_list = filtered.to_dict("records")

    return render_template(
        "transactions.html",
        has_data=True,
        transactions=txn_list,
        categories=categories,
        months=months,
        month_filter=month_filter,
        category_filter=category_filter,
        search_filter=search_filter,
    )


@app.route("/summary")
def summary():
    """View monthly summary."""
    df = load_ledger(LEDGER_PATH)

    if df.empty:
        return render_template("summary.html", has_data=False, months=[])

    df["date"] = pd.to_datetime(df["date"])
    months = get_months_in_ledger(df)
    selected_month = request.args.get("month", months[-1] if months else None)

    md_content = ""
    if selected_month:
        md_content = generate_monthly_summary(df, selected_month)
        # Save it too
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / f"summary_{selected_month}.md").write_text(md_content)

    return render_template(
        "summary.html",
        has_data=True,
        months=months,
        selected_month=selected_month,
        summary_md=md_content,
    )


@app.route("/recategorize", methods=["POST"])
def recategorize():
    """Re-run categorization on the entire ledger."""
    df = load_ledger(LEDGER_PATH)
    if df.empty:
        flash("No transactions to recategorize.", "warning")
        return redirect(url_for("dashboard"))

    txns = df.to_dict("records")
    txns = categorize_transactions(txns)
    df = pd.DataFrame(txns)
    save_ledger(df, LEDGER_PATH)

    flash(f"Recategorized {len(txns)} transactions.", "success")
    return redirect(url_for("transactions"))


def main():
    """Run the Flask development server."""
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
