"""Product Catalog -- line-item grain, per the owner's request."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from utils import bq
from utils.theme import CATEGORICAL, channel_color, plotly_template
from utils.ui import money, page_header, pct, sample_banner, theme_mode

st.set_page_config(page_title="Product Catalog | Saul Stitch House", page_icon="🧵", layout="wide")

MODE = theme_mode()
TEMPLATE = plotly_template(MODE)

page_header("Product Catalog", "Line-item detail from every order, plus catalog and margin summaries.")

order_lines, live_lines = bq.get_order_lines()
dim_products, live_products = bq.get_dim_products()
product_perf, live_perf = bq.get_product_performance()

sample_banner(live_lines and live_products and live_perf)

# --- Filters -------------------------------------------------------------------
f1, f2, f3, f4 = st.columns(4)
product_types = sorted(order_lines["product_type"].dropna().unique()) if not order_lines.empty else []
channels = sorted(order_lines["sales_channel"].dropna().unique()) if not order_lines.empty else []

sel_types = f1.multiselect("Product line", product_types, default=product_types)
sel_channels = f2.multiselect("Sales channel", channels, default=channels)
sku_search = f3.text_input("Search SKU or product name")
if not order_lines.empty:
    min_d, max_d = order_lines["order_date"].min(), order_lines["order_date"].max()
    date_range = f4.date_input("Order date range", value=(min_d, max_d), min_value=min_d, max_value=max_d)
else:
    date_range = None

filtered = order_lines.copy()
if sel_types:
    filtered = filtered[filtered["product_type"].isin(sel_types)]
if sel_channels:
    filtered = filtered[filtered["sales_channel"].isin(sel_channels)]
if sku_search:
    q = sku_search.strip().lower()
    filtered = filtered[
        filtered["sku"].str.lower().str.contains(q, na=False)
        | filtered["product_name"].str.lower().str.contains(q, na=False)
    ]
if date_range and isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    filtered = filtered[(filtered["order_date"] >= start) & (filtered["order_date"] <= end)]

st.markdown("---")

# --- Summary row -----------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Line items (filtered)", f"{len(filtered):,}")
c2.metric("Units sold", f"{int(filtered['quantity'].sum()):,}" if not filtered.empty else "0")
c3.metric("Gross revenue", money(filtered["line_amount"].sum()) if not filtered.empty else "$0")
margin_rate = (
    filtered["estimated_line_margin"].sum() / filtered["line_amount"].sum()
    if not filtered.empty and filtered["line_amount"].sum() else None
)
c4.metric("Estimated margin rate", pct(margin_rate) if margin_rate is not None else "--")

st.markdown("---")

left, right = st.columns([3, 2])

with left:
    st.subheader("Revenue by product line")
    if not filtered.empty:
        by_type = filtered.groupby("product_type", as_index=False)["line_amount"].sum().sort_values("line_amount", ascending=False)
        fig = go.Figure(go.Bar(
            x=by_type["product_type"], y=by_type["line_amount"],
            marker_color=CATEGORICAL[MODE][0],
        ))
        fig.update_layout(template=TEMPLATE, height=320, yaxis_title="Gross revenue", xaxis_title=None)
        st.plotly_chart(fig)
    else:
        st.caption("No line items match the current filters.")

with right:
    st.subheader("Revenue split by channel")
    if not filtered.empty:
        by_ch = filtered.groupby("sales_channel", as_index=False)["line_amount"].sum()
        fig2 = go.Figure(go.Pie(
            labels=by_ch["sales_channel"], values=by_ch["line_amount"], hole=0.55,
            marker=dict(colors=[channel_color(c, MODE) for c in by_ch["sales_channel"]]),
            textinfo="label+percent",
        ))
        fig2.update_layout(template=TEMPLATE, height=320, showlegend=False)
        st.plotly_chart(fig2)
    else:
        st.caption("No line items match the current filters.")

st.markdown("---")
st.subheader("Product catalog summary")
st.caption("One row per SKU -- revenue, units, and estimated margin (mart_product_performance).")
if not product_perf.empty:
    show_cols = [
        "sku", "product_name", "product_type", "order_count", "units_sold",
        "gross_revenue", "estimated_total_margin", "estimated_margin_rate",
        "shopify_gross_revenue", "etsy_gross_revenue",
    ]
    show_cols = [c for c in show_cols if c in product_perf.columns]
    st.dataframe(
        product_perf[show_cols].sort_values("gross_revenue", ascending=False),
        width="stretch", hide_index=True,
        column_config={
            "gross_revenue": st.column_config.NumberColumn("Gross revenue", format="$%.2f"),
            "estimated_total_margin": st.column_config.NumberColumn("Est. margin", format="$%.2f"),
            "estimated_margin_rate": st.column_config.NumberColumn("Est. margin rate", format="%.1f%%"),
            "shopify_gross_revenue": st.column_config.NumberColumn("Shopify revenue", format="$%.2f"),
            "etsy_gross_revenue": st.column_config.NumberColumn("Etsy revenue", format="$%.2f"),
        },
    )
else:
    st.caption("No product performance data available yet.")

st.markdown("---")
st.subheader("Line items")
st.caption(f"Showing {len(filtered):,} of {len(order_lines):,} order lines (fct_order_lines).")
if not filtered.empty:
    line_cols = [
        "order_date", "order_id", "sales_channel", "sku", "product_name", "product_type",
        "quantity", "unit_price", "line_amount", "unit_cost", "estimated_line_margin",
    ]
    line_cols = [c for c in line_cols if c in filtered.columns]
    st.dataframe(
        filtered[line_cols].sort_values("order_date", ascending=False),
        width="stretch", hide_index=True, height=420,
        column_config={
            "unit_price": st.column_config.NumberColumn("Unit price", format="$%.2f"),
            "line_amount": st.column_config.NumberColumn("Line amount", format="$%.2f"),
            "unit_cost": st.column_config.NumberColumn("Unit cost", format="$%.2f"),
            "estimated_line_margin": st.column_config.NumberColumn("Est. margin", format="$%.2f"),
        },
    )
else:
    st.caption("No line items match the current filters.")
