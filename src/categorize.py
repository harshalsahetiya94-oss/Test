"""Two-tier transaction categorization: rule-based first, Claude fallback for unknowns."""

import json
import re

import anthropic

# Tier 1: Rule-based keyword matching (Irish context)
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Groceries": [
        "TESCO", "DUNNES", "LIDL", "ALDI", "SUPERVALU", "CENTRA", "SPAR",
        "MARKS AND SPENCER FOOD", "M&S FOOD",
    ],
    "Dining": [
        "JUST EAT", "DELIVEROO", "MCDONALDS", "MCDONALD'S", "STARBUCKS",
        "COSTA", "INSOMNIA", "BURGER KING", "KFC", "SUPERMACS", "NANDOS",
        "RESTAURANT", "CAFE", "BISTRO",
    ],
    "Transport": [
        "IRISH RAIL", "BUS EIREANN", "LEAP", "AIRCOACH", "FREENOW", "LYNK",
        "CIRCLE K", "APPLEGREEN", "MAXOL", "TOPAZ", "PETROL", "DIESEL",
        "TAXI", "UBER",
    ],
    "Bills/Utilities": [
        "ELECTRIC IRELAND", "BORD GAIS", "ENERGIA", "SSE AIRTRICITY",
        "EIR ", "VODAFONE", "THREE ", "VIRGIN MEDIA", "IRISH WATER", "UISCE",
        "RENT",
    ],
    "Subscriptions": [
        "NETFLIX", "SPOTIFY", "AMAZON PRIME", "DISNEY", "APPLE.COM",
        "GOOGLE ", "MICROSOFT", "OPENAI", "ANTHROPIC", "ADOBE", "LINKEDIN",
    ],
    "Shopping": [
        "AMAZON", "EBAY", "SHEIN", "ZARA", "PENNEYS", "PRIMARK",
        "HARVEY NORMAN", "IKEA", "ARGOS",
    ],
    "Health": [
        "BOOTS", "MCCABES", "LLOYDS PHARMACY", "HSE", "VHI", "LAYA",
        "IRISH LIFE HEALTH", "PHARMACY", "DENTAL", "DOCTOR",
    ],
    "Cash": ["ATM"],
    "Transfers": ["365 ONLINE", "MOBI ", "INWARD PAYMENT"],
    "Income": ["SALARY", "PAYROLL", "REVENUE", "WAGE"],
    "Banking Fees": [
        "MAINTENANCE FEE", "QUARTERLY FEE", "GOVT STAMP DUTY",
        "BOI FEE", "BOI QUARTERLY",
    ],
}

VALID_CATEGORIES = list(CATEGORY_KEYWORDS.keys()) + ["Other"]


def categorize_rule_based(description: str) -> str | None:
    """Try to categorize a transaction by keyword matching. Returns None if no match."""
    upper = description.upper()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in upper:
                return category
    return None


def categorize_batch_with_claude(
    descriptions: list[str],
    client: anthropic.Anthropic | None = None,
) -> dict[str, str]:
    """Use Claude to categorize a batch of unmatched transaction descriptions.

    Args:
        descriptions: List of transaction descriptions to categorize.
        client: Optional Anthropic client.

    Returns:
        Dict mapping description -> category.
    """
    if not descriptions:
        return {}

    if client is None:
        client = anthropic.Anthropic()

    categories_list = ", ".join(VALID_CATEGORIES)

    prompt = f"""\
Categorize each of the following bank transaction descriptions into exactly one \
of these categories: {categories_list}

Return a JSON object mapping each description to its category. No markdown fences, \
no explanation — just the JSON object.

Descriptions:
{json.dumps(descriptions, indent=2)}
"""

    message = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()
    # Strip code fences if present
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: assign "Other" to everything
        result = {d: "Other" for d in descriptions}

    return result


def categorize_transactions(
    transactions: list[dict],
    client: anthropic.Anthropic | None = None,
) -> list[dict]:
    """Categorize a list of transactions using rules first, then Claude for unknowns.

    Modifies transactions in-place and returns them.
    """
    unmatched = []
    unmatched_indices = []

    for i, txn in enumerate(transactions):
        category = categorize_rule_based(txn["description"])
        if category:
            txn["category"] = category
        else:
            unmatched.append(txn["description"])
            unmatched_indices.append(i)

    # Batch Claude calls in groups of 20
    if unmatched:
        all_results = {}
        for batch_start in range(0, len(unmatched), 20):
            batch = unmatched[batch_start:batch_start + 20]
            results = categorize_batch_with_claude(batch, client)
            all_results.update(results)

        for idx in unmatched_indices:
            desc = transactions[idx]["description"]
            transactions[idx]["category"] = all_results.get(desc, "Other")

    return transactions
