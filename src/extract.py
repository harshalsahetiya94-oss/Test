"""Extract transactions from BOI PDF statements or expense screenshots using Claude API."""

import base64
import json
import re
from pathlib import Path

import anthropic

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

SYSTEM_PROMPT = """\
You are a financial document parser specializing in Bank of Ireland (BOI) personal \
current account statements and general expense receipts/screenshots.

Your job is to extract every transaction from the provided document and return them \
as a JSON array. Return ONLY the JSON array — no preamble, no markdown fences, no \
explanation.

## For BOI PDF statements

BOI statements have these characteristics:
- Header: account holder name, IBAN, BIC, statement period (e.g. "01 Mar 2026 to 31 Mar 2026"), opening/closing balance
- Transaction table columns: Date | Details | Debit (€) | Credit (€) | Balance (€)
- Date format is DD MMM or DD/MM/YYYY — normalize to ISO YYYY-MM-DD using the statement period to infer the year
- Common transaction types: POS (point of sale), D/D (direct debit), S/O (standing order), ATM, 365 ONLINE, MOBI, CONTACTLESS, INWARD PAYMENT
- A single transaction can wrap onto two lines in the Details column — merge them into one description
- Ignore the running Balance column

## For expense screenshots / receipts

Extract each line item or expense visible. Use the date shown on the receipt, or \
today's date if none is visible. Use the merchant/store name as the description.

## Output schema

Each transaction object must have exactly these fields:

{
  "date": "YYYY-MM-DD",
  "description": "cleaned up description of the transaction",
  "amount": -47.32,
  "type": "debit",
  "raw_details": "original text exactly as it appears in the document"
}

Rules:
- "amount": negative for debits/expenses, positive for credits/income
- "type": "debit" or "credit"
- Merge multi-line descriptions into a single string
- Normalize dates to ISO YYYY-MM-DD format
- Strip leading/trailing whitespace from all string fields
"""


def _read_file_as_base64(file_path: Path) -> str:
    """Read a file and return its base64-encoded content."""
    with open(file_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def _get_media_type(file_path: Path) -> str:
    """Return the appropriate media type for the file."""
    ext = file_path.suffix.lower()
    media_types = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    return media_types[ext]


def _build_content_block(file_path: Path) -> dict:
    """Build the appropriate content block for Claude API based on file type."""
    ext = file_path.suffix.lower()
    data = _read_file_as_base64(file_path)
    media_type = _get_media_type(file_path)

    if ext == ".pdf":
        return {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": data,
            },
        }
    else:
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": data,
            },
        }


def _parse_json_response(text: str) -> list[dict]:
    """Parse JSON from Claude's response, stripping any accidental code fences."""
    cleaned = text.strip()
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()
    return json.loads(cleaned)


def extract_transactions(file_path: Path, client: anthropic.Anthropic | None = None) -> list[dict]:
    """Extract transactions from a BOI PDF statement or expense screenshot.

    Args:
        file_path: Path to the PDF or image file.
        client: Optional Anthropic client (created from env if not provided).

    Returns:
        List of transaction dicts with keys: date, description, amount, type, raw_details.
    """
    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {file_path.suffix}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if client is None:
        client = anthropic.Anthropic()

    content_block = _build_content_block(file_path)

    message = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    content_block,
                    {
                        "type": "text",
                        "text": "Extract all transactions from this document. Return ONLY a JSON array.",
                    },
                ],
            }
        ],
    )

    response_text = message.content[0].text

    # First attempt to parse
    try:
        transactions = _parse_json_response(response_text)
    except json.JSONDecodeError:
        # Retry with a stricter reminder
        retry_message = client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        content_block,
                        {
                            "type": "text",
                            "text": "Extract all transactions from this document. Return ONLY a JSON array.",
                        },
                    ],
                },
                {
                    "role": "assistant",
                    "content": response_text,
                },
                {
                    "role": "user",
                    "content": (
                        "Your response was not valid JSON. Please return ONLY a raw JSON "
                        "array with no markdown fences, no explanation — just [ ... ]."
                    ),
                },
            ],
        )
        transactions = _parse_json_response(retry_message.content[0].text)

    return transactions
