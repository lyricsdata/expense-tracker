"""Streamlit UI for the expense tracker.

Run from this folder with:
streamlit run expense_app.py
"""

import calendar
from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import tracker
from tracker import CATEGORIES

# Shared category colour palette (used across every tab).
CATEGORY_COLORS = {
    'food':                 '#FF6B6B',
    'books_learning':       '#4ECDC4',
    'fixed_costs':          '#45B7D1',
    'entertainment_social': '#96CEB4',
    'others':               '#FFEAA7',
}

MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

st.set_page_config(page_title="Expense Tracker", page_icon="💰", layout="wide")

tracker.initialize_csv()


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
st.sidebar.title("💰 Expense Tracker")

years = tracker.available_years()
current_year = date.today().year
if current_year not in years:
    years = sorted(set(years) | {current_year})
default_year_index = years.index(current_year)

selected_year = st.sidebar.selectbox(
    "Year", years, index=default_year_index, format_func=str
)

all_categories = list(CATEGORIES.keys())
selected_categories = st.sidebar.multiselect(
    "Categories", all_categories, default=all_categories
)

st.sidebar.divider()
st.sidebar.subheader("➕ Add expense")

# Category drives the subcategory options, so it lives outside the form to
# allow the subcategory selectbox to react to the chosen category.
form_category = st.sidebar.selectbox("Category", all_categories, key="form_category")

with st.sidebar.form("add_expense_form", clear_on_submit=True):
    form_date = st.date_input("Date", value=date.today())
    form_amount = st.number_input("Amount (SGD)", min_value=0.01, step=0.01, value=0.01)
    form_subcategory = st.selectbox("Subcategory", CATEGORIES[form_category])
    form_notes = st.text_input("Notes (optional)")
    submitted = st.form_submit_button("Add expense")

    if submitted:
        try:
            tracker.add_expense(
                form_date.strftime("%Y-%m-%d"),
                form_amount,
                form_category,
                form_subcategory,
                form_notes,
            )
            st.success(f"Added SGD {form_amount:,.2f} to {form_category}/{form_subcategory}")
            st.rerun()
        except ValueError as e:
            st.error(str(e))


# --------------------------------------------------------------------------- #
# Data (filtered by sidebar selections)
# --------------------------------------------------------------------------- #
expenses = tracker.load_expenses(year=selected_year, categories=selected_categories)

tab_overview, tab_heatmap, tab_details = st.tabs(
    ["📊 Overview", "📅 Heatmap", "📋 Details"]
)


# --------------------------------------------------------------------------- #
# Overview tab
# --------------------------------------------------------------------------- #
with tab_overview:
    st.subheader(f"{selected_year} Overview")

    monthly_cat = tracker.monthly_totals_by_category(expenses)
    # month index (1-12) -> total
    month_totals = {m: 0.0 for m in range(1, 13)}
    for month_key, cats in monthly_cat.items():
        m = int(month_key[5:7])
        month_totals[m] = sum(cats.values())

    today = date.today()
    # "Current month" is today's month when viewing the current year,
    # otherwise December of the selected (past) year.
    current_month = today.month if selected_year == today.year else 12
    prev_month = current_month - 1 if current_month > 1 else None

    this_month_total = month_totals.get(current_month, 0.0)
    prev_month_total = month_totals.get(prev_month, 0.0) if prev_month else 0.0
    year_total = sum(month_totals.values())

    delta = this_month_total - prev_month_total
    # Spending up = bad (red), down = good (green). Streamlit colours a
    # positive delta green by default, so invert it.
    delta_str = None if prev_month is None else f"{delta:,.2f} SGD"

    c1, c2, c3 = st.columns(3)
    c1.metric(
        f"{MONTH_LABELS[current_month - 1]} total",
        f"SGD {this_month_total:,.2f}",
    )
    c2.metric(
        "vs previous month",
        f"SGD {prev_month_total:,.2f}",
        delta=delta_str,
        delta_color="inverse",
    )
    c3.metric("Year total", f"SGD {year_total:,.2f}")

    st.divider()

    # Stacked bar: one bar per month, one trace per category.
    fig = go.Figure()
    for cat in all_categories:
        if cat not in selected_categories:
            continue
        y_values = [monthly_cat.get(f"{selected_year}-{m:02d}", {}).get(cat, 0.0)
                    for m in range(1, 13)]
        fig.add_trace(go.Bar(
            name=cat,
            x=MONTH_LABELS,
            y=y_values,
            marker_color=CATEGORY_COLORS.get(cat),
            hovertemplate=f"<b>{cat}</b><br>%{{x}}: SGD %{{y:,.2f}}<extra></extra>",
        ))

    fig.update_layout(
        barmode='stack',
        xaxis_title="Month",
        yaxis_title="Amount (SGD)",
        legend_title="Category",
        height=480,
        margin=dict(t=30, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------------------------------- #
# Heatmap tab
# --------------------------------------------------------------------------- #
with tab_heatmap:
    st.subheader(f"{selected_year} Daily Spending Heatmap")

    daily = tracker.daily_totals(expenses)

    year_dates = pd.date_range(f"{selected_year}-01-01", f"{selected_year}-12-31")
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    # Build a 7 x N grid. iso week can wrap (week 1 / 52-53); use a continuous
    # week index based on the offset from the first Monday so the calendar reads
    # left-to-right without gaps.
    jan1 = year_dates[0]
    # Days since the Monday of the week containing Jan 1.
    start_offset = jan1.isoweekday() - 1  # Mon=0 .. Sun=6
    n_weeks = ((len(year_dates) + start_offset - 1) // 7) + 1

    # Build one clickable square marker per day. A Plotly *Heatmap* trace does
    # not emit click events through Streamlit's on_select, so we render the
    # calendar as a Scatter of square markers instead — same look, but every
    # cell is individually clickable. The date is carried in customdata so the
    # click handler can read it back directly.
    xs, ys, colors, custom = [], [], [], []
    for d in year_dates:
        day_index = (d - jan1).days + start_offset
        week = day_index // 7
        weekday = d.isoweekday() - 1  # Mon=0 .. Sun=6
        date_str = d.strftime("%Y-%m-%d")
        amount = daily.get(date_str, 0.0)
        xs.append(week)
        ys.append(weekday)
        colors.append(amount)
        custom.append([date_str, amount])

    # Cap the colour scale at the 90th percentile of spending days so a few
    # large outliers (e.g. rent) don't wash every ordinary day out to near-white.
    # Days above the cap simply saturate at the deepest red.
    spending_days = [a for a in colors if a > 0]
    cmax = float(pd.Series(spending_days).quantile(0.90)) if spending_days else 1.0
    if cmax <= 0:
        cmax = max(spending_days) if spending_days else 1.0

    # --- Resolve the currently selected day BEFORE drawing, so it can be ringed.
    # Keep the picker's stored value valid for the current year (also clears a
    # stale date left over from another year).
    if (st.session_state.get("heatmap_date") is None
            or st.session_state["heatmap_date"].year != selected_year):
        st.session_state["heatmap_date"] = date(selected_year, 1, 1)

    # A click leaves its selection in st.session_state["hm_chart"] (the chart's
    # key), already available at the top of the rerun it triggered. Apply it only
    # when it's a *new* click, otherwise it would keep overriding the date picker.
    sel = st.session_state.get("hm_chart")
    sel_points = sel.get("selection", {}).get("points", []) if sel else []
    if sel_points:
        cd = sel_points[0].get("customdata")
        if cd and cd[0] != st.session_state.get("_last_click"):
            st.session_state["_last_click"] = cd[0]
            clicked = datetime.strptime(cd[0], "%Y-%m-%d").date()
            if clicked.year == selected_year:
                st.session_state["heatmap_date"] = clicked

    selected_date = st.session_state["heatmap_date"]

    # Pick a legend text colour that contrasts with the active Streamlit theme
    # (the legend sits on the dark app background in dark mode).
    try:
        _dark = st.context.theme.type == "dark"
    except Exception:
        _dark = (st.get_option("theme.base") or "dark") == "dark"
    legend_text_color = "#FAFAFA" if _dark else "#333333"

    fig_hm = go.Figure(go.Scatter(
        x=xs,
        y=ys,
        mode='markers',
        name="SGD",  # shown in the legend instead of the default "trace 0"
        marker=dict(
            symbol='square',
            size=16,
            color=colors,
            colorscale='YlOrRd',
            cmin=0,
            cmax=cmax,
            showscale=True,
            # No title on the colour bar — it rendered unreadably over its own
            # gradient. The "SGD" legend label names the scale instead.
            colorbar=dict(title=dict(text="")),
            line=dict(width=1, color='white'),
        ),
        customdata=custom,
        hovertemplate="%{customdata[0]}<br>SGD %{customdata[1]:,.2f}<extra></extra>",
        # Plotly dims unselected points to opacity ~0.2 after a click, washing
        # the rest of the calendar out to white. Keep them fully opaque instead.
        unselected=dict(marker=dict(opacity=1)),
    ))

    # Outline the selected day with a hollow square drawn on top.
    if date(selected_year, 1, 1) <= selected_date <= date(selected_year, 12, 31):
        sd_index = (pd.Timestamp(selected_date) - jan1).days + start_offset
        fig_hm.add_trace(go.Scatter(
            x=[sd_index // 7],
            y=[selected_date.isoweekday() - 1],
            mode='markers',
            # For "-open" symbols the outline colour comes from marker.color
            # (not marker.line); line.width controls how thick that ring is.
            marker=dict(symbol='square-open', size=22,
                        color='#1565C0',
                        line=dict(width=3, color='#1565C0')),
            hoverinfo='skip',
            showlegend=False,
            # Don't let a selection on the day-grid dim this highlight ring.
            unselected=dict(marker=dict(opacity=1)),
        ))

    fig_hm.update_layout(
        xaxis=dict(title="Week of year", showgrid=False, zeroline=False),
        yaxis=dict(
            tickmode='array',
            tickvals=list(range(7)),
            ticktext=weekdays,
            autorange='reversed',  # Mon at top
            showgrid=False,
            zeroline=False,
        ),
        height=320,
        margin=dict(t=30, b=30),
        plot_bgcolor='white',
        showlegend=True,
        legend=dict(font=dict(color=legend_text_color)),
    )
    # on_select="rerun" makes a click rerun the script; the selection is read
    # back from st.session_state["hm_chart"] at the top of that next run.
    st.plotly_chart(
        fig_hm,
        use_container_width=True,
        on_select="rerun",
        selection_mode="points",
        key="hm_chart",
    )

    st.divider()
    st.markdown("**Daily detail** — click a heatmap cell or pick a date")

    picked = st.date_input(
        "Pick a date",
        min_value=date(selected_year, 1, 1),
        max_value=date(selected_year, 12, 31),
        key="heatmap_date",
    )
    picked_str = picked.strftime("%Y-%m-%d")
    day_rows = [e for e in expenses if e['date'] == picked_str]
    if day_rows:
        df_day = pd.DataFrame(day_rows)[tracker.FIELDNAMES]
        st.dataframe(df_day, use_container_width=True, hide_index=True)
        st.caption(f"Total: SGD {sum(r['amount'] for r in day_rows):,.2f}")
    else:
        st.info(f"No expenses on {picked_str}.")


# --------------------------------------------------------------------------- #
# Details tab
# --------------------------------------------------------------------------- #
with tab_details:
    st.subheader("All filtered expenses")

    if expenses:
        df = pd.DataFrame(expenses)[tracker.FIELDNAMES]
        df = df.sort_values("date", ascending=False).reset_index(drop=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Total: SGD {df['amount'].sum():,.2f} ({len(df)} transactions)")

        csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "⬇ Download filtered CSV",
            data=csv_bytes,
            file_name=f"expenses_{selected_year}.csv",
            mime="text/csv",
        )
    else:
        st.info("No expenses match the current filters.")
