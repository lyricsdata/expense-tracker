"""One-off migration: bulk-upload expenses.csv rows into the Google Sheet.

Reads the local ``expenses.csv`` (the old CSV data layer) and appends every
row to the spreadsheet backing the live app. Run once after the Sheets cutover:

    python migrate_csv_to_sheet.py            # migrate
    python migrate_csv_to_sheet.py --force    # migrate even if sheet has data

Safety: by default it refuses to run when the sheet already contains data rows,
so re-running won't silently create duplicates.
"""

import csv
import os
import sys

import tracker

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.csv")


def main():
    force = "--force" in sys.argv

    if not os.path.exists(CSV_PATH):
        print(f"No CSV found at {CSV_PATH} — nothing to migrate.")
        return

    sheet = tracker.get_sheet()
    tracker.initialize_sheet()  # make sure the header row exists

    existing = tracker._fetch_all_rows()
    if existing and not force:
        print(
            f"Sheet already has {len(existing)} data row(s). "
            "Refusing to migrate to avoid duplicates. Re-run with --force to override."
        )
        return

    # Read CSV rows in the canonical column order.
    rows = []
    skipped = 0
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                amount = float(row["amount"])
            except (ValueError, TypeError, KeyError):
                skipped += 1
                continue
            rows.append([
                row.get("date", ""),
                amount,
                row.get("category", ""),
                row.get("subcategory", "") or "",
                row.get("notes", "") or "",
            ])

    if not rows:
        print("No valid rows to migrate.")
        return

    print(f"Uploading {len(rows)} row(s) to the sheet ...")
    # Single batched call (USER_ENTERED so dates/numbers are typed naturally).
    sheet.append_rows(rows, value_input_option="USER_ENTERED")
    tracker._fetch_all_rows.clear()  # drop the cached (pre-migration) snapshot

    total = len(tracker._fetch_all_rows())
    print(f"Done. Migrated {len(rows)} row(s) ({skipped} skipped). "
          f"Sheet now has {total} data row(s).")


if __name__ == "__main__":
    main()
