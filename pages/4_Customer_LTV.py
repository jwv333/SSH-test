"""Customer LTV -- lifetime value and repeat-purchase behavior."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from utils import bq
from utils.theme import CATEGORICAL, SEQUENTIAL_BLUE, plotly_template
from utils.ui import money, page_header, pct, sample_banner, theme_mode

st.set_page_config(page_title="Customer LTV | Saul Stitch House", page_icon="🧵", layout="wide")

MODE = theme_mode()
TEMPLATE = plotly_template(MODE)

page_header("Customer Lifetime Value", "Who your customers are, how much they're worth, and who's gone quiet.")

customer_ltv, live = bq.get_customer_ltv()
sample_banner(live)

if customer_ltv.empty:
    st.caption("No customer data available yet.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total customers", f"{len(customer_ltv):,}")
c2.metric("Repeat customer rate", pct(customer_ltv["is_repeat_customer"].mean()))
c3.metric("Avg lifetime revenue", money(customer_ltv["lifetime_gross_revenue"].mean()))
stale = customer_ltv[customer_ltv["days_since_last_order"] > 180]
c4.metric("Customers quiet 180+ days", f"{len(stale):,}")

st.markdown("---")

left, right = st.columns(2)

with left:
    st.subheader("Lifetime revenue distribution")
    fig = go.Figure(go.Histogram(
        x=customer_ltv["lifetime_gross_revenue"], nbinsx=25,
        marker_color=SEQUENTIAL_BLUE[7],
    ))
    fig.update_layout(template=TEMPLATE, height=340, xaxis_title="Lifetime gross revenue", yaxis_title="Customers")
    st.plotly_chart(fig)

with right:
    st.subheader("New vs. repeat customers")
    counts = customer_ltv["is_repeat_customer"].value_counts().rename({True: "Repeat", False: "One-time"})
    fig2 = go.Figure(go.Pie(
        labels=counts.index, values=counts.values, hole=0.55,
        marker=dict(colors=[CATEGORICAL[MODE][0], CATEGORICAL[MODE][2]]),
        textinfo="label+percent",
    ))
    fig2.update_layout(template=TEMPLATE, height=340, showlegend=False)
    st.plotly_chart(fig2)

st.markdown("---")
st.subheader("Recency: days since last order")
fig3 = go.Figure(go.Histogram(
    x=customer_ltv["days_since_last_order"], nbinsx=30,
    marker_color=SEQUENTIAL_BLUE[9],
))
fig3.add_vline(x=180, line_width=1, line_dash="dash", line_color="#898781",
                annotation_text="180 days", annotation_position="top")
fig3.update_layout(template=TEMPLATE, height=300, xaxis_title="Days since last order", yaxis_title="Customers")
st.plotly_chart(fig3)

st.markdown("---")
t1, t2 = st.tabs(["Top customers by lifetime value", "Customers quiet 180+ days"])

with t1:
    top = customer_ltv.sort_values("lifetime_gross_revenue", ascending=False).head(25)
    cols = ["email", "total_orders", "channels_used", "lifetime_gross_revenue", "average_order_value", "days_since_last_order"]
    cols = [c for c in cols if c in top.columns]
    st.dataframe(
        top[cols], hide_index=True,
        column_config={
            "lifetime_gross_revenue": st.column_config.NumberColumn("Lifetime revenue", format="$%.2f"),
            "average_order_value": st.column_config.NumberColumn("AOV", format="$%.2f"),
        },
    )

with t2:
    if stale.empty:
        st.caption("No customers past 180 days since their last order -- nice.")
    else:
        cols = ["email", "total_orders", "lifetime_gross_revenue", "most_recent_order_date", "days_since_last_order"]
        cols = [c for c in cols if c in stale.columns]
        st.dataframe(
            stale.sort_values("lifetime_gross_revenue", ascending=False)[cols],
            width="stretch", hide_index=True,
            column_config={"lifetime_gross_revenue": st.column_config.NumberColumn("Lifetime revenue", format="$%.2f")},
        )
        st.caption(f"Combined, these {len(stale):,} customers represent {money(stale['lifetime_gross_revenue'].sum())} of historical revenue -- a reasonable win-back audience.")
