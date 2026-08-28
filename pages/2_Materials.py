"""
Materials -- bill-of-materials used to make each product.

IMPORTANT: no materials/BOM data source exists in QuickBooks, Shopify, or
Etsy today (see docs/known_gaps.md). This page always runs on a clearly
labeled illustrative sample so the layout can be reviewed now; it will keep
showing the sample banner even after BigQuery is connected, until a real
materials source is modeled into the dbt project.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from utils import bq
from utils.theme import CATEGORICAL, plotly_template
from utils.ui import money2, page_header, theme_mode

st.set_page_config(page_title="Materials | Saul Stitch House", page_icon="🧵", layout="wide")

MODE = theme_mode()
TEMPLATE = plotly_template(MODE)

page_header("Materials", "What goes into each product -- bill of materials and per-unit material cost.")

materials, live = bq.get_materials()
dim_products, _ = bq.get_dim_products()

st.warning(
    "**This page is illustrative sample data, not real inventory or COGS data.** "
    "None of QuickBooks, Shopify, or Etsy currently track a bill-of-materials for "
    "these SKUs -- `dim_products.unit_cost` is a single blended cost, not a materials "
    "breakdown. See `docs/known_gaps.md` for the three ways to make this page real "
    "(a materials seed file, assembly/kit items in QuickBooks, or dedicated "
    "inventory/production software synced into BigQuery).",
    icon="🧵",
)

if materials.empty:
    st.caption("No sample materials data available.")
    st.stop()

skus = sorted(materials["sku"].unique())
sku_labels = {row["sku"]: f"{row['sku']} -- {row['product_name']}" for _, row in materials.drop_duplicates("sku").iterrows()}
sel_sku = st.selectbox("Choose a product", skus, format_func=lambda s: sku_labels.get(s, s))

sub = materials[materials["sku"] == sel_sku]
product_name = sub["product_name"].iloc[0] if not sub.empty else sel_sku
total_material_cost = sub["cost_per_unit"].sum()

c1, c2 = st.columns([2, 1])
with c1:
    st.subheader(product_name)
    st.dataframe(
        sub[["material", "qty_per_unit", "material_unit_cost", "cost_per_unit"]].rename(columns={
            "material": "Material", "qty_per_unit": "Qty per unit",
            "material_unit_cost": "Material unit cost", "cost_per_unit": "Cost per unit",
        }),
        width="stretch", hide_index=True,
        column_config={
            "Material unit cost": st.column_config.NumberColumn(format="$%.2f"),
            "Cost per unit": st.column_config.NumberColumn(format="$%.2f"),
        },
    )
with c2:
    st.metric("Total material cost / unit", money2(total_material_cost))
    listed_cost = None
    if not dim_products.empty and "sku" in dim_products.columns:
        match = dim_products[dim_products["sku"] == sel_sku]
        if not match.empty and "unit_cost" in match.columns:
            listed_cost = match["unit_cost"].iloc[0]
    if listed_cost is not None:
        st.metric("Blended unit_cost (dim_products)", money2(listed_cost),
                   delta=money2(listed_cost - total_material_cost) + " vs. materials sum")
        st.caption("The gap between these two numbers is labor, overhead, and packaging not captured in the materials list.")

st.markdown("---")
st.subheader("Material cost breakdown by product")
pivot = materials.pivot_table(index="product_name", columns="material", values="cost_per_unit", aggfunc="sum", fill_value=0)
materials_order = list(materials["material"].unique())
palette = CATEGORICAL[MODE]
fig = go.Figure()
for i, mat in enumerate(materials_order):
    if mat not in pivot.columns:
        continue
    fig.add_trace(go.Bar(
        name=mat, x=pivot.index, y=pivot[mat],
        marker_color=palette[i % len(palette)],
    ))
fig.update_layout(
    template=TEMPLATE, barmode="stack", height=420,
    yaxis_title="Material cost per unit", legend_title_text="Material",
    xaxis=dict(tickangle=-30),
)
st.plotly_chart(fig)

st.markdown("---")
st.subheader("All materials")
st.dataframe(
    materials[["sku", "product_name", "material", "qty_per_unit", "material_unit_cost", "cost_per_unit"]],
    width="stretch", hide_index=True,
    column_config={
        "material_unit_cost": st.column_config.NumberColumn("Material unit cost", format="$%.2f"),
        "cost_per_unit": st.column_config.NumberColumn("Cost per unit", format="$%.2f"),
    },
)
