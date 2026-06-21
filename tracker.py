"""Business logic layer for the expense tracker.

Data layer: **Google Sheets** (migrated from CSV). The spreadsheet schema is
fixed: ``date, amount, category, subcategory, notes``.

Authentication uses a Google service-account key read from Streamlit secrets:
- On Streamlit Community Cloud: the app's **Secrets** settings.
- Locally: ``.streamlit/secrets.toml`` (see the template committed to the repo).

The public function interface is unchanged from the CSV version so the
Streamlit UI (``expense_app.py``) needs no edits.
"""

from collections import defaultdict
from datetime import datetime

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

# Category definitions (moved verbatim from the CLI)
CATEGORIES = {
    'food': ['groceries', 'lunch', 'cafe', 'takeout'],
    'books_learning': ['books', 'ebooks', 'online_courses', 'stationery'],
    'fixed_costs': ['rent', 'utilities', 'phone', 'household_items'],
    'entertainment_social': ['travel', 'dining_out', 'clothing', 'salon', 'hobbies', 'subscriptions'],
    'others': ['medical', 'transportation', 'misc'],
}

FIELDNAMES = ['date', 'amount', 'category', 'subcategory', 'notes']

# ID of the Google Sheets document (the long token in the sheet's URL:
# docs.google.com/spreadsheets/d/<THIS>/edit). Opening by key uses only the
# Sheets API, so the Drive API does not need to be enabled.
SPREADSHEET_ID = "1A37-Nn7DcWNtzgWbBdYE2KS90lzEYSTW6kgcKxdS3Ak"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# --------------------------------------------------------------------------- #
# Connection
# --------------------------------------------------------------------------- #
@st.cache_resource
def get_sheet():
    """Return the first worksheet of the expense spreadsheet.

    Cached as a *resource* so the authorised gspread client is created once per
    session and reused (the connection object is not serialisable, so it must
    not be cached with ``st.cache_data``).
    """
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1


@st.cache_data(ttl=30)
def _fetch_all_rows():
    """Fetch every data row as a list of dicts, keyed by header.

    Cached for 30s so the repeated ``load_expenses`` / ``available_years`` calls
    that happen on a single page render hit the Google Sheets API only once.
    The cache is cleared explicitly after a write (see :func:`add_expense`).
    """
    return get_sheet().get_all_records()


def initialize_sheet():
    """Write the header row if the sheet has no header yet.

    Mirrors the old ``initialize_csv``: a no-op once the header exists.
    """
    sheet = get_sheet()
    first_row = sheet.row_values(1)
    if first_row != FIELDNAMES:
        # Empty sheet (or missing header) — seed row 1 with the schema.
        if not first_row:
            sheet.update([FIELDNAMES], "A1")
            _fetch_all_rows.clear()


# Backwards-compatible alias: ``expense_app.py`` still calls
# ``tracker.initialize_csv()``. Keep both names pointing at the same function.
initialize_csv = initialize_sheet


def validate_date(date_str: str) -> str:
    """Validate and normalise a date string.

    Accepts ``YYMMDD`` (e.g. ``251130``) or ``YYYY-MM-DD`` and always returns
    ``YYYY-MM-DD``. Raises ``ValueError`` on invalid input.
    """
    date_str = date_str.strip()

    # 6-digit YYMMDD -> YYYY-MM-DD
    if len(date_str) == 6 and date_str.isdigit():
        try:
            year = 2000 + int(date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"Invalid date. Got: {date_str}. Use YYMMDD (e.g., 251130) or YYYY-MM-DD format"
            )

    # YYYY-MM-DD
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise ValueError(
            f"Invalid date format. Use YYMMDD (e.g., 251130) or YYYY-MM-DD format. Got: {date_str}"
        )


def add_expense(date, amount, category, subcategory=None, notes=''):
    """Validate inputs and append a single expense row to the sheet.

    ``date`` accepts either accepted format (validated via :func:`validate_date`).
    Raises ``ValueError`` if any field is invalid. Returns the normalised
    ``(date, amount, category, subcategory, notes)`` tuple that was written.
    """
    # Normalise / validate date
    date = validate_date(date)

    # Validate amount
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        raise ValueError("Invalid amount format. Should be a number.")
    if amount <= 0:
        raise ValueError("Invalid amount. Should be positive.")

    # Validate category
    if category not in CATEGORIES:
        raise ValueError(f"Invalid category. Choose from: {', '.join(CATEGORIES.keys())}")

    # Validate subcategory if provided
    if subcategory and subcategory not in CATEGORIES[category]:
        raise ValueError(
            f"Invalid subcategory for {category}. Choose from: {', '.join(CATEGORIES[category])}"
        )

    initialize_sheet()
    get_sheet().append_row([date, amount, category, subcategory or '', notes or ''])

    # New row won't show until the 30s data cache is refreshed; clear it now so
    # the UI reflects the addition on the immediate rerun.
    _fetch_all_rows.clear()

    return (date, amount, category, subcategory or '', notes or '')


def load_expenses(year=None, categories=None):
    """Read the sheet and return a list of expense dicts.

    Each dict has keys ``date, amount, category, subcategory, notes`` with
    ``amount`` cast to ``float``. Optionally filter by ``year`` (int) and/or
    ``categories`` (list of category names). Returns ``[]`` if the sheet is empty.
    """
    expenses = []
    for record in _fetch_all_rows():
        row = {key: record.get(key, '') for key in FIELDNAMES}

        # Skip malformed rows defensively.
        try:
            row['amount'] = float(row['amount'])
        except (ValueError, TypeError):
            continue

        if year is not None and not str(row.get('date', '')).startswith(f"{year}-"):
            continue
        if categories is not None and row.get('category') not in categories:
            continue

        expenses.append(row)

    return expenses


def monthly_totals_by_category(expenses):
    """Aggregate to ``{month: {category: amount}}`` (month is ``YYYY-MM``).

    Suitable for a stacked bar chart.
    """
    totals = defaultdict(lambda: defaultdict(float))
    for expense in expenses:
        month = expense['date'][:7]
        totals[month][expense['category']] += expense['amount']
    # Convert to plain dicts for predictable downstream behaviour.
    return {month: dict(cats) for month, cats in totals.items()}


def daily_totals(expenses):
    """Aggregate to ``{date_str: amount}`` (date is ``YYYY-MM-DD``).

    Suitable for a calendar heatmap.
    """
    totals = defaultdict(float)
    for expense in expenses:
        totals[expense['date']] += expense['amount']
    return dict(totals)


def available_years():
    """Return a sorted list of years (int) present in the sheet."""
    years = set()
    for record in _fetch_all_rows():
        try:
            years.add(int(str(record.get('date', ''))[:4]))
        except (ValueError, IndexError):
            continue
    return sorted(years)
