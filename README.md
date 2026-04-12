# BOI Expense Tracker

A web-based expense tracker for Bank of Ireland personal current account holders. Upload your BOI PDF statements or expense screenshots and get automatic transaction extraction, categorization, and monthly summaries — powered by Claude AI.

## Features

- **PDF & Image Upload** — Drop in BOI PDF statements or photos/screenshots of receipts
- **AI Extraction** — Claude reads your documents and extracts every transaction automatically
- **Smart Categorization** — Two-tier system: instant rule-based matching for common Irish merchants, Claude AI fallback for the rest
- **Deduplication** — Re-uploading the same statement won't create duplicate entries
- **Dashboard** — At-a-glance view of income, spend, and net by month with category breakdown
- **Transaction Browser** — Filter and search all transactions by month, category, or keyword
- **Monthly Summaries** — Detailed markdown reports with spend by category, top merchants, and items needing review

## Categories

Groceries, Dining, Transport, Bills/Utilities, Subscriptions, Shopping, Health, Cash, Transfers, Income, Banking Fees, Other

## Install

```bash
# Clone the repo
git clone https://github.com/harshalsahetiya94-oss/test.git
cd test

# Install dependencies
pip install -r requirements.txt

# Set up your API key
cp .env.example .env
# Edit .env and add your Anthropic API key
```

### Getting an Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Go to API Keys and create a new key
4. Paste it into your `.env` file

## Usage

```bash
# Start the web app
python -m src.app
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.

### Upload a Statement

1. Click **Upload** in the sidebar
2. Drag and drop your BOI PDF statement or expense screenshot, or click to browse
3. Click **Process Files** — Claude will extract and categorize all transactions
4. View results on the **Dashboard**

### Browse Transactions

- Go to **Transactions** to see all your expenses
- Filter by month, category, or search by description
- Click **Recategorize All** to re-run categorization (useful after the keyword rules are updated)

### Monthly Summary

- Go to **Summary** and select a month
- View total income, spend, net, category breakdown, top merchants, and items needing review

## Cost Estimate

Each statement upload costs roughly **1-3 cents** in API usage (one call for extraction + optionally one for categorizing unknown merchants). Claude Sonnet is used for both extraction and categorization.

## Privacy

- Your PDF/image files are saved locally in `input/`
- Only the document content is sent to the Anthropic API for extraction
- Your expense ledger stays local in `output/expenses.csv`
- No data is stored on any external server beyond the API call

## Project Structure

```
├── input/              # Uploaded PDFs and screenshots
├── output/
│   ├── expenses.csv    # Running deduplicated ledger
│   └── summary_*.md    # Monthly summary files
├── src/
│   ├── app.py          # Flask web application
│   ├── extract.py      # Claude API document extraction
│   ├── categorize.py   # Rule-based + Claude categorization
│   ├── ledger.py       # CSV ledger read/write/dedupe
│   └── summary.py      # Monthly summary generator
├── templates/          # HTML templates
├── static/             # CSS and JS
├── tests/
│   └── test_ledger.py  # Dedupe logic tests
├── .env.example
├── requirements.txt
└── README.md
```

## How to Extend

- **Add categories**: Edit `CATEGORY_KEYWORDS` in `src/categorize.py` to add new categories or keywords
- **Custom rules**: Add merchant-specific matching logic in `categorize_rule_based()`
- **Export formats**: Extend `src/summary.py` to generate other output formats
- **Additional file types**: The extraction supports PDF, PNG, JPG, WebP, and GIF — add new media types in `src/extract.py`
