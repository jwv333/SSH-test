"""Channel Performance -- Shopify vs. Etsy, month over month."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from utils import bq
from utils.theme import channel_color, plotly_template
from utils.ui import money, page_header, pct, sample_banner, theme_mode

st.set_page_config(page_title="Channel Performance | Saul Stitch House", page_icon="🧵", layout="wide")

MODE = theme_mode()
TEMPLATE = plotly_template(MODE)

page_header("Channel Performance", "Monthly revenue, fees, and order economics by sales channel.")

channel_perf, live = bq.get_channel_performance()
sample_banner(live)

if channel_perf.empty:
    st.caption("No channel performance data available yet.")
    st.stop()

channels = sorted(channel_perf["sales_channel"].unique())
sel_channels = st.multiselect("Channels", channels, default=channels)
cp = channel_perf[channel_perf["sales_channel"].isin(sel_channels)].sort_values("order_month")

latest_month = cp["order_month"].max()
cur = cp[cp["order_month"] == latest_month]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Gross revenue (last month)", money(cur["gross_revenue"].sum()))
c2.metric("Net revenue (last month)", money(cur["net_revenue"].sum()))
c3.metric("Orders (last month)", f"{int(cur['order_count'].sum()):,}")
avg_fee = (cur["total_channel_fees"].sum() / cur["gross_revenue"].sum()) if cur["gross_revenue"].sum() else None
c4.metric("Blended fee rate (last month)", pct(avg_fee) if avg_fee is not None else "--")

if cur["has_estimated_fees"].any() if "has_estimated_fees" in cur.columns else False:
    st.caption("⚠️ Some fee figures above are estimated, not exact -- see Talk to Your Data for details.")

st.markdown("---")

left, right = st.columns(2)

with left:
    st.subheader("Gross vs. net revenue by month")
    fig = go.Figure()
    for ch in sel_channels:
        sub = cp[cp["sales_channel"] == ch]
        fig.add_trace(go.Scatter(x=sub["order_month"], y=sub["gross_revenue"], mode="lines",
                                  name=f"{ch} gross", line=dict(width=2, color=channel_color(ch, MODE))))
        fig.add_trace(go.Scatter(x=sub["order_month"], y=sub["net_revenue"], mode="lines",
                                  name=f"{ch} net", line=dict(width=2, color=channel_color(ch, MODE), dash="dot")))
    fig.update_layout(template=TEMPLATE, height=360, yaxis_title="Revenue", legend_title_text="Series")
    st.plotly_chart(fig)

with right:
    st.subheader("Effective fee rate by month")
    fig2 = go.Figure()
    for ch in sel_channels:
        sub = cp[cp["sales_channel"] == ch]
        fig2.add_trace(go.Scatter(x=sub["order_month"], y=sub["effective_fee_rate"] * 100, mode="lines+markers",
                                   name=ch, line=dict(width=2, color=channel_color(ch, MODE))))
    fig2.update_layout(template=TEMPLATE, height=360, yaxis_title="Effective fee rate (%)", legend_title_text="Channel")
    st.plotly_chart(fig2)

st.markdown("---")
c5, c6 = st.columns(2)

with c5:
    st.subheader("Average order value")
    fig3 = go.Figure()
    for ch in sel_channels:
        sub = cp[cp["sales_channel"] == ch]
        fig3.add_trace(go.Scatter(x=sub["order_month"], y=sub["average_order_value"], mode="lines+markers",
                                   name=ch, line=dict(width=2, color=channel_color(ch, MODE))))
    fig3.update_layout(template=TEMPLATE, height=320, yaxis_title="AOV", legend_title_text="Channel")
    st.plotly_chart(fig3)

with c6:
    st.subheader("Order volume")
    fig4 = go.Figure()
    for ch in sel_channels:
        sub = cp[cp["sales_channel"] == ch]
        fig4.add_trace(go.Bar(x=sub["order_month"], y=sub["order_count"], name=ch, marker_color=channel_color(ch, MODE)))
    fig4.update_layout(template=TEMPLATE, height=320, barmode="group", yaxis_title="Orders", legend_title_text="Channel")
    st.plotly_chart(fig4)

st.markdown("---")
st.subheader("Monthly detail")
show_cols = [
    "order_month", "sales_channel", "order_count", "gross_revenue", "total_channel_fees",
    "net_revenue", "average_order_value", "effective_fee_rate", "refund_rate",
]
show_cols = [c for c in show_cols if c in cp.columns]
st.dataframe(
    cp[show_cols].sort_values(["order_month", "sales_channel"], ascending=[False, True]),
    width="stretch", hide_index=True,
    column_config={
        "gross_revenue": st.column_config.NumberColumn("Gross revenue", format="$%.2f"),
        "total_channel_fees": st.column_config.NumberColumn("Fees", format="$%.2f"),
        "net_revenue": st.column_config.NumberColumn("Net revenue", format="$%.2f"),
        "average_order_value": st.column_config.NumberColumn("AOV", format="$%.2f"),
        "effective_fee_rate": st.column_config.NumberColumn("Fee rate", format="%.1f%%"),
        "refund_rate": st.column_config.NumberColumn("Refund rate", format="%.1f%%"),
    },
)
