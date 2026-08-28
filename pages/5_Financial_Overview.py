"""Financial Overview -- monthly P&L snapshot and cash-flow reconciliation."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from utils import bq
from utils.theme import DIVERGING, STATUS, plotly_template
from utils.ui import money, page_header, pct, sample_banner, theme_mode

st.set_page_config(page_title="Financial Overview | Saul Stitch House", page_icon="🧵", layout="wide")

MODE = theme_mode()
TEMPLATE = plotly_template(MODE)

page_header("Financial Overview", "A lightweight P&L and cash-flow reconciliation from QuickBooks.")
st.caption(
    "⚠️ This is a directional snapshot, not a substitute for your accountant's official "
    "financial statements -- no accruals, depreciation, or owner's equity handling."
)

monthly_pnl, live_pnl = bq.get_monthly_pnl()
cash_flow, live_cf = bq.get_cash_flow_reconciliation()
sample_banner(live_pnl and live_cf)

if monthly_pnl.empty:
    st.caption("No P&L data available yet.")
    st.stop()

pnl = monthly_pnl.sort_values("month")
last = pnl.iloc[-1]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Revenue (last month)", money(last["total_revenue"]))
c2.metric("Expenses (last month)", money(last["total_expenses"]))
c3.metric("Net income (last month)", money(last["net_income"]))
c4.metric("Net margin (last month)", pct(last["net_margin"]))

st.markdown("---")

left, right = st.columns(2)

with left:
    st.subheader("Revenue vs. expenses")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=pnl["month"], y=pnl["total_revenue"], name="Revenue", marker_color=DIVERGING[MODE]["pos"]))
    fig.add_trace(go.Bar(x=pnl["month"], y=pnl["total_expenses"], name="Expenses", marker_color=DIVERGING[MODE]["neg"]))
    fig.update_layout(template=TEMPLATE, barmode="group", height=360, yaxis_title="Amount", legend_title_text="Series")
    st.plotly_chart(fig)

with right:
    st.subheader("Net margin trend")
    fig2 = go.Figure(go.Scatter(
        x=pnl["month"], y=pnl["net_margin"] * 100, mode="lines+markers",
        line=dict(width=2, color=DIVERGING[MODE]["pos"]), marker=dict(size=6),
    ))
    fig2.add_hline(y=0, line_width=1, line_color="#898781")
    fig2.update_layout(template=TEMPLATE, height=360, yaxis_title="Net margin (%)")
    st.plotly_chart(fig2)

st.markdown("---")
st.subheader("Cash flow reconciliation")
st.caption("Do the payouts channels reported actually match the deposits that hit the bank?")

if not cash_flow.empty:
    cf = cash_flow.sort_values("month")
    last_cf = cf.iloc[-1]
    unmatched_rate = (last_cf["unmatched_or_variance_deposits"] / last_cf["total_deposits"]) if last_cf["total_deposits"] else 0

    c5, c6, c7 = st.columns(3)
    c5.metric("Total deposits (last month)", money(last_cf["total_deposits"]))
    c6.metric("Matched", money(last_cf["matched_deposits"]))
    badge_color = STATUS["good"] if unmatched_rate <= 0.05 else (STATUS["warning"] if unmatched_rate <= 0.1 else STATUS["serious"])
    c7.markdown(
        f"<div style='font-size:0.8rem;color:#898781;'>Unmatched / variance</div>"
        f"<div style='font-size:1.6rem;font-weight:600;color:{badge_color};'>{money(last_cf['unmatched_or_variance_deposits'])} ({pct(unmatched_rate)})</div>",
        unsafe_allow_html=True,
    )

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(x=cf["month"], y=cf["matched_deposits"], name="Matched", marker_color=STATUS["good"]))
    fig3.add_trace(go.Bar(x=cf["month"], y=cf["unmatched_or_variance_deposits"], name="Unmatched / variance", marker_color=STATUS["warning"]))
    fig3.update_layout(template=TEMPLATE, barmode="stack", height=340, yaxis_title="Deposits", legend_title_text="Match status")
    st.plotly_chart(fig3)

    st.dataframe(
        cf[["month", "total_channel_payouts_reported", "total_deposits", "matched_deposits", "unmatched_or_variance_deposits"]],
        width="stretch", hide_index=True,
        column_config={
            "total_channel_payouts_reported": st.column_config.NumberColumn("Reported payouts", format="$%.2f"),
            "total_deposits": st.column_config.NumberColumn("Deposits", format="$%.2f"),
            "matched_deposits": st.column_config.NumberColumn("Matched", format="$%.2f"),
            "unmatched_or_variance_deposits": st.column_config.NumberColumn("Unmatched", format="$%.2f"),
        },
    )
    st.caption("Matching is best-effort (amount + date proximity), especially for Shopify -- see Talk to Your Data for details.")
else:
    st.caption("No cash flow reconciliation data available yet.")

st.markdown("---")
st.subheader("Monthly P&L detail")
st.dataframe(
    pnl[["month", "total_revenue", "total_expenses", "net_income", "net_margin"]].sort_values("month", ascending=False),
    width="stretch", hide_index=True,
    column_config={
        "total_revenue": st.column_config.NumberColumn("Revenue", format="$%.2f"),
        "total_expenses": st.column_config.NumberColumn("Expenses", format="$%.2f"),
        "net_income": st.column_config.NumberColumn("Net income", format="$%.2f"),
        "net_margin": st.column_config.NumberColumn("Net margin", format="%.1f%%"),
    },
)
