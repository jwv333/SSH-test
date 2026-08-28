"""
Saul Stitch House -- Analytics Dashboard
Entry point / Overview page. Run with: streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import bq
from utils.theme import channel_color, plotly_template
from utils.ui import money, page_header, pct, sample_banner, theme_mode

st.set_page_config(
    page_title="Saul Stitch House Analytics",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded",
)

MODE = theme_mode()
TEMPLATE = plotly_template(MODE)

with st.sidebar:
    st.markdown("### 🧵 Saul Stitch House")
    st.caption("Monogramming & embroidery gifts -- Shopify + Etsy + QuickBooks")
    st.markdown("---")
    st.markdown(
        "**Pages**\n\n"
        "Use the navigation above to jump to Product Catalog, Materials, "
        "Channel Performance, Customer LTV, Financial Overview, AI Insights, "
        "or Talk to Your Data."
    )
    st.markdown("---")
    if bq.is_live():
        st.success(f"Connected to BigQuery\n\n`{bq.PROJECT_ID}`", icon="✅")
    else:
        st.warning(
            "Not connected to BigQuery yet -- showing sample data everywhere. "
            "Add your service account to `.streamlit/secrets.toml` once the "
            "Fivetran syncs are live.",
            icon="🔌",
        )

page_header(
    "Overview",
    "Executive snapshot across Shopify, Etsy, and QuickBooks.",
)

product_perf, live_pp = bq.get_product_performance()
channel_perf, live_cp = bq.get_channel_performance()
customer_ltv, live_ltv = bq.get_customer_ltv()
monthly_pnl, live_pnl = bq.get_monthly_pnl()
cash_flow, live_cf = bq.get_cash_flow_reconciliation()

overall_live = all([live_pp, live_cp, live_ltv, live_pnl, live_cf])
sample_banner(
    overall_live,
    detail="" if overall_live else "Once QuickBooks, Shopify, and Etsy finish syncing in Fivetran, this page switches to live numbers automatically.",
)

# --- KPI row -----------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

if not channel_perf.empty:
    latest_month = channel_perf["order_month"].max()
    trailing = channel_perf[channel_perf["order_month"] >= (pd.Timestamp(latest_month) - pd.DateOffset(months=11))]
    total_gross_12mo = trailing["gross_revenue"].sum()
    total_net_12mo = trailing["net_revenue"].sum()
else:
    total_gross_12mo = total_net_12mo = 0

if not monthly_pnl.empty:
    pnl_sorted = monthly_pnl.sort_values("month")
    last_pnl = pnl_sorted.iloc[-1]
    net_income_last = last_pnl.get("net_income", None)
    net_margin_last = last_pnl.get("net_margin", None)
else:
    net_income_last = net_margin_last = None

repeat_rate = customer_ltv["is_repeat_customer"].mean() if not customer_ltv.empty else None

col1.metric("Gross revenue (trailing 12 mo)", money(total_gross_12mo))
col2.metric("Net revenue (trailing 12 mo)", money(total_net_12mo))
col3.metric("Net income (last month)", money(net_income_last) if net_income_last is not None else "--",
            delta=pct(net_margin_last) + " margin" if net_margin_last is not None else None)
col4.metric("Repeat customer rate", pct(repeat_rate) if repeat_rate is not None else "--")

st.markdown("---")

left, right = st.columns([3, 2])

with left:
    st.subheader("Revenue by channel, by month")
    if not channel_perf.empty:
        fig = go.Figure()
        for ch in sorted(channel_perf["sales_channel"].unique()):
            sub = channel_perf[channel_perf["sales_channel"] == ch].sort_values("order_month")
            fig.add_trace(go.Scatter(
                x=sub["order_month"], y=sub["gross_revenue"],
                mode="lines", name=ch, line=dict(width=2, color=channel_color(ch, MODE)),
            ))
        fig.update_layout(template=TEMPLATE, height=340, legend_title_text="Channel",
                           yaxis_title="Gross revenue", xaxis_title=None)
        st.plotly_chart(fig)
    else:
        st.caption("No channel performance data available yet.")

with right:
    st.subheader("Net margin trend")
    if not monthly_pnl.empty:
        pnl_sorted = monthly_pnl.sort_values("month")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=pnl_sorted["month"], y=pnl_sorted["net_margin"] * 100,
            mode="lines+markers", name="Net margin",
            line=dict(width=2, color=channel_color("Shopify", MODE)),
            marker=dict(size=6),
        ))
        fig2.update_layout(template=TEMPLATE, height=340, yaxis_title="Net margin (%)", xaxis_title=None, showlegend=False)
        st.plotly_chart(fig2)
        st.caption("Directional P&L from QuickBooks -- not a substitute for your accountant's financials.")
    else:
        st.caption("No P&L data available yet.")

st.markdown("---")
st.subheader("Top products by revenue")
if not product_perf.empty:
    top = product_perf.sort_values("gross_revenue", ascending=False).head(8)
    fig3 = go.Figure(go.Bar(
        x=top["gross_revenue"], y=top["product_name"], orientation="h",
        marker_color=channel_color("Shopify", MODE),
    ))
    fig3.update_layout(template=TEMPLATE, height=320, xaxis_title="Gross revenue", yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig3)
else:
    st.caption("No product performance data available yet.")

st.caption(
    "Data model: dbt marts on Fivetran-synced QuickBooks, Shopify, and Etsy data. "
    "See the Talk to Your Data page for definitions and known caveats."
)
