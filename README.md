# Expense Tracker

A simple SGD expense tracker with two front-ends sharing one data file
(`expenses.csv`, schema: `date, amount, category, subcategory, notes`).

## Files

| File | Role |
| --- | --- |
| `tracker.py` | Business logic (validation, CSV I/O, aggregation). No side effects — safe to import. |
| `app.py` | Streamlit UI. |
| `_interactive_expense_tracker.py` | Original CLI (still works as before). |

## Run the Streamlit app

```bash
pip install streamlit plotly pandas
streamlit run app.py
```

### Features

- **Sidebar** — year filter, category filter, and an "Add expense" form
  (subcategory options follow the selected category).
- **📊 Overview** — current-month / vs-previous-month / year-total metric cards
  (spending increases show red, decreases green) plus a monthly stacked bar
  chart by category.
- **📅 Heatmap** — GitHub-style calendar heatmap of daily spending, with a
  date picker to inspect a single day's transactions.
- **📋 Details** — full filtered table with a CSV download button.

## Run the CLI

```bash
python _interactive_expense_tracker.py
```
