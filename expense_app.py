"""家計簿アプリ — Streamlit UI
3ページ構成: Overview / Heatmap / Details
tracker.py の公開インターフェースを使用。
"""

import calendar
from datetime import datetime, date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import tracker

# ─────────────────────────────────────────────
# 定数
# ─────────────────────────────────────────────
CAT_CONFIG = {
    "food":                  {"label": "食費",      "icon": "🛒", "color": "#5DCAA5"},
    "fixed_costs":           {"label": "固定費",    "icon": "🏠", "color": "#7F77DD"},
    "entertainment_social":  {"label": "娯楽・交際", "icon": "🎵", "color": "#F0997B"},
    "books_learning":        {"label": "本・学習",  "icon": "📚", "color": "#EF9F27"},
    "others":                {"label": "その他",    "icon": "🏥", "color": "#B4B2A9"},
}

# ─────────────────────────────────────────────
# ページ設定
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="家計簿",
    page_icon="💴",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# カスタム CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI',
                 'Segoe UI', sans-serif !important;
}
.stApp { background: #FAFAF8; }
.block-container {
    max-width: 720px !important;
    padding: 4rem 1rem 3rem !important;
    margin: 0 auto;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #E8E7E2;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    font-size: 14px;
    font-weight: 500;
    color: #888780;
    padding: 0.6rem 1.2rem;
    border-radius: 0;
    border-bottom: 2px solid transparent;
    background: transparent;
}
.stTabs [aria-selected="true"] {
    color: #2C2C2A !important;
    border-bottom: 2px solid #5DCAA5 !important;
    background: transparent !important;
}
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 0.5px solid #E8E7E2;
    border-radius: 12px;
    padding: 1rem 1.25rem !important;
}
[data-testid="stMetricLabel"] { font-size: 12px !important; color: #888780 !important; font-weight: 400 !important; }
[data-testid="stMetricValue"] { font-size: 22px !important; font-weight: 500 !important; color: #2C2C2A !important; }
[data-testid="stMetricDelta"] { font-size: 12px !important; }
.section-title {
    font-size: 15px;
    font-weight: 500;
    color: #2C2C2A;
    margin: 1.5rem 0 0.75rem;
}
.tx-card {
    background: #FFFFFF;
    border: 0.5px solid #E8E7E2;
    border-radius: 12px;
    padding: 0;
    margin-bottom: 0.5rem;
    overflow: hidden;
}
.tx-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 16px;
    border-bottom: 0.5px solid #F1EFE8;
}
.tx-row:last-child { border-bottom: none; }
.tx-icon {
    width: 36px; height: 36px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; flex-shrink: 0;
}
.tx-info { flex: 1; min-width: 0; }
.tx-name {
    font-size: 13px; font-weight: 500;
    color: #2C2C2A;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.tx-meta { font-size: 11px; color: #B4B2A9; margin-top: 2px; }
.tx-amount { font-size: 13px; font-weight: 500; color: #D85A30; flex-shrink: 0; }
.stTextInput input, .stNumberInput input, .stSelectbox select, .stTextArea textarea {
    border: 0.5px solid #D3D1C7 !important;
    border-radius: 8px !important;
    background: #FFFFFF !important;
    font-size: 14px !important;
    color: #2C2C2A !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: #5DCAA5 !important;
    box-shadow: 0 0 0 2px rgba(93,202,165,0.15) !important;
}
.stButton > button {
    border: 0.5px solid #D3D1C7 !important;
    background: transparent !important;
    color: #5F5E5A !important;
    border-radius: 8px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 0.5rem 1.5rem !important;
    transition: background 0.15s;
}
.stButton > button:hover { background: #F7F6F3 !important; }
.stButton > button[kind="primary"] {
    background: #5DCAA5 !important;
    border-color: #5DCAA5 !important;
    color: #FFFFFF !important;
}
.stButton > button[kind="primary"]:hover {
    background: #1D9E75 !important;
    border-color: #1D9E75 !important;
}
hr { border: none; border-top: 0.5px solid #E8E7E2; margin: 1rem 0; }
.stSuccess { border-radius: 8px !important; }
.stError   { border-radius: 8px !important; }
[data-testid="collapsedControl"] { display: none; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ヘルパー
# ─────────────────────────────────────────────
def fmt_sgd(v: float) -> str:
    return f"SGD {int(v):,}"


def cat_label(cat: str) -> str:
    return CAT_CONFIG.get(cat, {}).get("label", cat)


def cat_icon(cat: str) -> str:
    return CAT_CONFIG.get(cat, {}).get("icon", "💴")


def cat_color(cat: str) -> str:
    return CAT_CONFIG.get(cat, {}).get("color", "#B4B2A9")


def icon_bg(cat: str) -> str:
    return {
        "food":                 "#E1F5EE",
        "fixed_costs":          "#EEEDFE",
        "entertainment_social": "#FAECE7",
        "books_learning":       "#FAEEDA",
        "others":               "#F1EFE8",
    }.get(cat, "#F1EFE8")


def load_df(year=None) -> pd.DataFrame:
    expenses = tracker.load_expenses(year=year)
    if not expenses:
        return pd.DataFrame(columns=tracker.FIELDNAMES)
    df = pd.DataFrame(expenses)
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = df["amount"].astype(float)
    df = df[df["category"].isin(tracker.CATEGORIES)]  # 不正カテゴリを除外
    return df


def tx_rows_html(df_rows) -> str:
    html = ""
    for _, row in df_rows.iterrows():
        bg    = icon_bg(row["category"])
        notes = row["notes"] if row["notes"] else cat_label(row["category"])
        sub   = row["subcategory"] if row["subcategory"] else cat_label(row["category"])
        meta  = f"{row['date'].strftime('%Y/%m/%d')}　{sub}"
        html += f"""
        <div class="tx-row">
          <div class="tx-icon" style="background:{bg};">{cat_icon(row['category'])}</div>
          <div class="tx-info">
            <div class="tx-name">{notes}</div>
            <div class="tx-meta">{meta}</div>
          </div>
          <div class="tx-amount">−{fmt_sgd(row['amount'])}</div>
        </div>"""
    return html


# ─────────────────────────────────────────────
# ページヘッダー
# ─────────────────────────────────────────────
tracker.initialize_sheet()
years = tracker.available_years() or [datetime.now().year]
current_year = datetime.now().year
current_month = datetime.now().month

col_title, col_year = st.columns([3, 1])
with col_title:
    st.markdown("## 家計簿")
with col_year:
    selected_year = st.selectbox(
        "年", years, index=len(years) - 1, label_visibility="collapsed"
    )

# ─────────────────────────────────────────────
# タブ
# ─────────────────────────────────────────────
tab_overview, tab_heatmap, tab_details, tab_add = st.tabs(
    ["Overview", "Heatmap", "Details", "+ 追加"]
)


# ═══════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════
with tab_overview:
    df = load_df(year=selected_year)

    df_month = df[
        (df["date"].dt.year == selected_year) &
        (df["date"].dt.month == current_month)
    ] if selected_year == current_year else df.iloc[0:0]

    total_month = df_month["amount"].sum()
    total_year  = df["amount"].sum()
    avg_monthly = df.groupby(df["date"].dt.month)["amount"].sum().mean() if not df.empty else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("今月の支出", fmt_sgd(total_month))
    with c2:
        st.metric(f"{selected_year}年 合計", fmt_sgd(total_year))
    with c3:
        st.metric("月平均", fmt_sgd(avg_monthly))

    if df.empty:
        st.info("まだデータがありません。「+ 追加」から記録を始めましょう。")
    else:
        st.markdown('<p class="section-title">月別支出</p>', unsafe_allow_html=True)

        monthly = (
            df.groupby([df["date"].dt.month, "category"])["amount"]
            .sum().reset_index()
        )
        monthly.columns = ["month", "category", "amount"]
        monthly["month_label"] = monthly["month"].apply(lambda m: f"{m}月")
        monthly["cat_label"]   = monthly["category"].apply(cat_label)

        cat_order = [cat_label(c) for c in CAT_CONFIG]
        color_map = {cat_label(k): v["color"] for k, v in CAT_CONFIG.items()}

        fig_bar = px.bar(
            monthly,
            x="month_label", y="amount",
            color="cat_label",
            color_discrete_map=color_map,
            category_orders={"cat_label": cat_order},
            labels={"amount": "支出 (SGD)", "month_label": "", "cat_label": "カテゴリ"},
            custom_data=["cat_label"],
        )
        fig_bar.update_traces(hovertemplate="%{customdata[0]}<br>SGD %{y:,.0f}<extra></extra>")
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="-apple-system, 'Hiragino Sans', sans-serif", color="#2C2C2A"),
            legend=dict(
                title="",
                orientation="h",
                yanchor="bottom", y=-0.45,
                xanchor="left", x=0,
                font=dict(color="#2C2C2A", size=12),
            ),
            margin=dict(l=0, r=0, t=10, b=90),
            xaxis=dict(
                showgrid=False,
                tickfont=dict(color="#2C2C2A", size=12),
            ),
            yaxis=dict(
                showgrid=True, gridcolor="#F1EFE8",
                tickformat=",.0f", tickprefix="SGD ",
                tickfont=dict(color="#2C2C2A", size=11),
            ),
            bargap=0.35,
            height=320,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        if not df_month.empty:
            st.markdown('<p class="section-title">カテゴリ別（今月）</p>', unsafe_allow_html=True)
            cat_month = (
                df_month.groupby("category")["amount"].sum()
                .reset_index().sort_values("amount", ascending=False)
            )
            rows_html = ""
            max_amt = cat_month["amount"].max()
            for _, row in cat_month.iterrows():
                pct = row["amount"] / max_amt * 100 if max_amt > 0 else 0
                bg  = icon_bg(row["category"])
                col = cat_color(row["category"])
                rows_html += f"""
                <div class="tx-row">
                  <div class="tx-icon" style="background:{bg};">{cat_icon(row['category'])}</div>
                  <div class="tx-info">
                    <div class="tx-name">{cat_label(row['category'])}</div>
                    <div style="height:4px;background:#F1EFE8;border-radius:99px;margin-top:6px;overflow:hidden;">
                      <div style="width:{pct:.0f}%;height:100%;background:{col};border-radius:99px;"></div>
                    </div>
                  </div>
                  <div class="tx-amount">{fmt_sgd(row['amount'])}</div>
                </div>"""
            st.markdown(f'<div class="tx-card">{rows_html}</div>', unsafe_allow_html=True)

        st.markdown('<p class="section-title">最近の取引</p>', unsafe_allow_html=True)
        recent = df.sort_values("date", ascending=False).head(8)
        rows_html = ""
        for _, row in recent.iterrows():
            bg         = icon_bg(row["category"])
            notes_text = row["notes"] if row["notes"] else cat_label(row["category"])
            sub        = row["subcategory"] if row["subcategory"] else ""
            meta       = f"{row['date'].strftime('%m/%d')}　{sub}" if sub else row["date"].strftime("%m/%d")
            rows_html += f"""
            <div class="tx-row">
              <div class="tx-icon" style="background:{bg};">{cat_icon(row['category'])}</div>
              <div class="tx-info">
                <div class="tx-name">{notes_text}</div>
                <div class="tx-meta">{meta}</div>
              </div>
              <div class="tx-amount">−{fmt_sgd(row['amount'])}</div>
            </div>"""
        st.markdown(f'<div class="tx-card">{rows_html}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# TAB 2 — HEATMAP
# ═══════════════════════════════════════════════════════════
@st.fragment
def render_heatmap(selected_year):
    df_h = load_df(year=selected_year)

    if df_h.empty:
        st.info("データがありません。")
        return

    st.markdown('<p class="section-title">日別支出ヒートマップ</p>', unsafe_allow_html=True)

    daily = (
        df_h.groupby(df_h["date"].dt.date)["amount"].sum().reset_index()
    )
    daily.columns = ["date", "amount"]
    daily["date"]  = pd.to_datetime(daily["date"])
    daily["month"] = daily["date"].dt.month
    daily["day"]   = daily["date"].dt.day

    months_in_data = sorted(daily["month"].unique())
    sel_month = st.selectbox(
        "月を選択", months_in_data,
        index=len(months_in_data) - 1,
        format_func=lambda m: f"{m}月",
        key="heatmap_month_sel",
    )

    dm = daily[daily["month"] == sel_month].copy()

    _, n_days  = calendar.monthrange(selected_year, int(sel_month))
    first_dow  = date(selected_year, int(sel_month), 1).weekday()

    cells = []
    col_idx, row_idx = first_dow, 0
    for d in range(1, n_days + 1):
        row = dm[dm["day"] == d]
        amt = float(row["amount"].values[0]) if len(row) > 0 else 0.0
        cells.append({"col": col_idx, "row": row_idx, "day": d, "amount": amt})
        col_idx += 1
        if col_idx > 6:
            col_idx = 0
            row_idx += 1

    cell_df = pd.DataFrame(cells)
    max_amt = cell_df["amount"].max() or 1.0

    # ── カレンダーを Scatter 四角マーカーで描画（クリック対応） ──
    fig_hm = go.Figure()
    fig_hm.add_trace(go.Scatter(
        x=cell_df["col"].tolist(),
        y=cell_df["row"].tolist(),
        mode="markers",
        marker=dict(
            symbol="square",
            size=34,
            color=cell_df["amount"].tolist(),
            colorscale=[
                [0,    "#F1EFE8"],
                [0.01, "#9FE1CB"],
                [0.3,  "#5DCAA5"],
                [0.7,  "#1D9E75"],
                [1,    "#085041"],
            ],
            cmin=0,
            cmax=max_amt,
            showscale=True,
            colorbar=dict(title="SGD", tickformat=",.0f", thickness=12, len=0.8),
            line=dict(width=2, color="white"),
        ),
        customdata=[
            [int(r["day"]), f"{selected_year}/{int(sel_month):02d}/{int(r['day']):02d}", r["amount"]]
            for _, r in cell_df.iterrows()
        ],
        hovertemplate="%{customdata[1]}<br>SGD %{customdata[2]:,.0f}<extra></extra>",
        unselected=dict(marker=dict(opacity=0.35)),
        selected=dict(marker=dict(color="#FF8C69", size=38)),
    ))

    # 日付数字をアノテーションで描画（色を金額に応じて切り替え）
    for _, r in cell_df.iterrows():
        txt_color = "#FFFFFF" if r["amount"] > max_amt * 0.4 else "#5F5E5A"
        fig_hm.add_annotation(
            x=r["col"], y=r["row"],
            text=str(int(r["day"])),
            showarrow=False,
            font=dict(size=11, color=txt_color, family="-apple-system, sans-serif"),
        )

    dow_labels = ["月", "火", "水", "木", "金", "土", "日"]
    fig_hm.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickvals=list(range(7)), ticktext=dow_labels,
                   tickfont_size=12, showgrid=False, side="top"),
        yaxis=dict(autorange="reversed", showgrid=False, showticklabels=False),
        margin=dict(l=0, r=50, t=40, b=10),
        height=280,
    )

    event = st.plotly_chart(
        fig_hm,
        use_container_width=True,
        on_select="rerun",
        selection_mode="points",
        key="heatmap_chart",
    )

    # ── 月集計 ──
    month_total = dm["amount"].sum()
    month_days  = len(dm[dm["amount"] > 0])
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(f"{int(sel_month)}月 合計", fmt_sgd(month_total))
    with c2:
        st.metric("支出日数", f"{month_days}日")
    with c3:
        avg_day = month_total / month_days if month_days > 0 else 0
        st.metric("1日平均", fmt_sgd(avg_day))

    # ── クリックした日の詳細 ──
    sel_points = (event or {}).get("selection", {}).get("points", [])
    if sel_points:
        clicked_day  = int(sel_points[0]["customdata"][0])
        clicked_date = date(selected_year, int(sel_month), clicked_day)
        clicked_str  = clicked_date.strftime("%Y-%m-%d")

        st.markdown(
            f'<p class="section-title">{clicked_date.strftime("%Y/%m/%d")} の支出</p>',
            unsafe_allow_html=True,
        )
        day_rows = df_h[df_h["date"].dt.strftime("%Y-%m-%d") == clicked_str]
        if day_rows.empty:
            st.info("この日の支出はありません。")
        else:
            st.markdown(
                f'<div class="tx-card">{tx_rows_html(day_rows)}</div>',
                unsafe_allow_html=True,
            )


with tab_heatmap:
    render_heatmap(selected_year)


# ═══════════════════════════════════════════════════════════
# TAB 3 — DETAILS
# ═══════════════════════════════════════════════════════════
@st.fragment
def render_details(selected_year):
    df_d = load_df(year=selected_year)

    if df_d.empty:
        st.info("データがありません。")
        return

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        month_opts = ["すべて"] + [f"{m}月" for m in sorted(df_d["date"].dt.month.unique())]
        sel_m = st.selectbox("月", month_opts, key="detail_month")
    with col_f2:
        cat_opts = ["すべて"] + [cat_label(c) for c in CAT_CONFIG]
        sel_c = st.selectbox("カテゴリ", cat_opts, key="detail_cat")

    df_filtered = df_d.copy()
    if sel_m != "すべて":
        m_num = int(sel_m.replace("月", ""))
        df_filtered = df_filtered[df_filtered["date"].dt.month == m_num]
    if sel_c != "すべて":
        cat_key = next((k for k, v in CAT_CONFIG.items() if v["label"] == sel_c), None)
        if cat_key:
            df_filtered = df_filtered[df_filtered["category"] == cat_key]

    df_filtered = df_filtered.sort_values("date", ascending=False)

    st.markdown(
        f'<p class="section-title">{len(df_filtered)}件　合計 {fmt_sgd(df_filtered["amount"].sum())}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="tx-card">{tx_rows_html(df_filtered)}</div>',
        unsafe_allow_html=True,
    )


with tab_details:
    render_details(selected_year)


# ═══════════════════════════════════════════════════════════
# TAB 4 — 追加フォーム
# ═══════════════════════════════════════════════════════════
@st.fragment
def render_add_form():
    st.markdown('<p class="section-title">支出を記録</p>', unsafe_allow_html=True)

    # フォーム外でカテゴリを選ぶことでサブカテゴリが連動して更新される
    cat_labels_map = {v["label"]: k for k, v in CAT_CONFIG.items()}
    cat_display    = list(cat_labels_map.keys())
    cat_sel_label  = st.selectbox("カテゴリ", cat_display, key="add_cat")
    cat_sel_key    = cat_labels_map[cat_sel_label]

    with st.form("add_expense_form", clear_on_submit=True):
        date_input = st.date_input("日付", value=datetime.now().date())
        amount_input = st.number_input(
            "金額 (SGD)",
            min_value=1,
            step=100,
            value=None,
            placeholder="例: 3000",
        )
        subcat_opts = ["（なし）"] + tracker.CATEGORIES[cat_sel_key]
        subcat_sel  = st.selectbox("サブカテゴリ", subcat_opts)
        subcat_val  = None if subcat_sel == "（なし）" else subcat_sel
        notes_input = st.text_input("メモ（任意）", placeholder="例: スーパー、カフェ…")
        submitted   = st.form_submit_button("記録する", type="primary", use_container_width=True)

    if submitted:
        if not amount_input:
            st.error("金額を入力してください。")
        else:
            try:
                tracker.add_expense(
                    date=date_input.strftime("%Y-%m-%d"),
                    amount=amount_input,
                    category=cat_sel_key,
                    subcategory=subcat_val,
                    notes=notes_input,
                )
                st.success(f"✓ 記録しました　{cat_sel_label}　{fmt_sgd(amount_input)}")
                st.balloons()
            except ValueError as e:
                st.error(str(e))


with tab_add:
    render_add_form()
