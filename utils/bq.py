"""
Data access layer for the Saul Stitch House dashboard.

Every page reads through the functions in this module rather than writing
its own SQL. Each function:

  1. Tries BigQuery first (using st.secrets["bigquery"] / GOOGLE_APPLICATION_CREDENTIALS).
  2. Falls back to realistic **sample data** if BigQuery isn't configured yet,
     or the query fails (e.g. the Fivetran syncs haven't landed a table yet).

The sample data exists so the dashboard is fully click-through-able before
QuickBooks/Shopify/Etsy are actually flowing into BigQuery. Every page that
renders sample data shows a clearly labeled banner -- nothing here is meant
to be mistaken for real numbers.

Table names mirror the dbt project's generate_schema_name macro:
  {dataset}_marts_commerce.<model>
  {dataset}_marts_finance.<model>
  {dataset}_marts_reporting.<model>
where `dataset` is the dbt `dataset:` target (default "analytics").
"""

from __future__ import annotations

import datetime as dt
import functools
import os

import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _cfg(key: str, default: str | None = None) -> str | None:
    try:
        bq_secrets = st.secrets.get("bigquery", {})
    except Exception:
        bq_secrets = {}
    return bq_secrets.get(key, os.environ.get(f"BIGQUERY_{key.upper()}", default))


PROJECT_ID = _cfg("project_id")
DATASET = _cfg("dataset", "analytics")

SCHEMA_COMMERCE = f"{DATASET}_marts_commerce"
SCHEMA_FINANCE = f"{DATASET}_marts_finance"
SCHEMA_REPORTING = f"{DATASET}_marts_reporting"


@st.cache_resource(show_spinner=False)
def _client():
    """Return a BigQuery client, or None if not configured. Cached per session
    so we don't re-authenticate on every rerun."""
    if not PROJECT_ID:
        return None
    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account

        if "bigquery" in st.secrets and "service_account" in st.secrets["bigquery"]:
            creds = service_account.Credentials.from_service_account_info(
                dict(st.secrets["bigquery"]["service_account"])
            )
            return bigquery.Client(project=PROJECT_ID, credentials=creds)
        # Falls back to GOOGLE_APPLICATION_CREDENTIALS / ADC if no explicit key given.
        return bigquery.Client(project=PROJECT_ID)
    except Exception:
        return None


def is_live() -> bool:
    """Whether we're actually able to reach BigQuery right now."""
    return _client() is not None


@st.cache_data(show_spinner=False, ttl=600)
def run_query(sql: str) -> pd.DataFrame | None:
    """Run a query against BigQuery. Returns None (not an empty frame) on any
    failure so callers can tell "no client / query failed" apart from "ran
    fine, zero rows" and fall back to sample data only in the former case."""
    client = _client()
    if client is None:
        return None
    try:
        return client.query(sql).to_dataframe()
    except Exception as e:
        st.session_state.setdefault("_bq_errors", []).append(str(e))
        return None


def table(schema: str, name: str) -> str:
    return f"`{PROJECT_ID}.{schema}.{name}`"


# ---------------------------------------------------------------------------
# Sample data (fallback only) -- shapes match the real mart schemas exactly,
# column for column, so pages don't need branching logic downstream.
# ---------------------------------------------------------------------------

_RNG = np.random.default_rng(7)

_PRODUCT_CATALOG = [
    # sku, name, type, base_unit_cost, base_price
    ("HKF-MONO-01", "Monogrammed Linen Handkerchief", "Wedding", 4.75, 18.00),
    ("HKF-MONO-02", "Embroidered Cotton Handkerchief Set", "Wedding", 6.10, 24.00),
    ("TWL-HOME-01", "Monogrammed Guest Towel", "Home", 5.40, 22.00),
    ("TWL-HOME-02", "Embroidered Kitchen Towel Set", "Home", 7.20, 28.00),
    ("BIB-BABY-01", "Personalized Baby Bib", "Baby", 3.10, 16.00),
    ("BLK-BABY-02", "Embroidered Baby Blanket", "Baby", 8.90, 42.00),
    ("BAG-ACC-01", "Monogrammed Canvas Tote", "Accessories", 6.50, 32.00),
    ("POU-ACC-02", "Embroidered Zip Pouch", "Accessories", 3.80, 19.00),
    ("STK-HOL-01", "Personalized Holiday Stocking", "Holiday", 7.75, 36.00),
    ("ORN-HOL-02", "Embroidered Ornament", "Holiday", 2.60, 14.00),
    ("VEIL-WED-03", "Monogrammed Bridal Veil Clip", "Wedding", 5.90, 26.00),
    ("NAPK-HOME-03", "Embroidered Napkin Set (4)", "Home", 9.10, 34.00),
]

_MATERIAL_COMPONENTS = {
    # sku -> [(material, unit_qty, unit_cost)]
    "HKF-MONO-01": [("Linen fabric (yd)", 0.15, 3.20), ("Embroidery thread (spool)", 0.05, 4.50), ("Packaging", 1, 0.75)],
    "HKF-MONO-02": [("Cotton fabric (yd)", 0.20, 2.10), ("Embroidery thread (spool)", 0.08, 4.50), ("Gift box", 1, 1.60)],
    "TWL-HOME-01": [("Turkish cotton towel (blank)", 1, 3.80), ("Embroidery thread (spool)", 0.06, 4.50), ("Packaging", 1, 0.75)],
    "TWL-HOME-02": [("Turkish cotton towel (blank)", 2, 3.80), ("Embroidery thread (spool)", 0.10, 4.50), ("Gift box", 1, 1.60)],
    "BIB-BABY-01": [("Organic cotton bib (blank)", 1, 1.90), ("Embroidery thread (spool)", 0.03, 4.50), ("Packaging", 1, 0.60)],
    "BLK-BABY-02": [("Minky fabric (yd)", 0.60, 5.40), ("Embroidery thread (spool)", 0.12, 4.50), ("Satin trim (yd)", 0.80, 1.10)],
    "BAG-ACC-01": [("Canvas tote (blank)", 1, 3.90), ("Embroidery thread (spool)", 0.07, 4.50), ("Packaging", 1, 0.60)],
    "POU-ACC-02": [("Canvas panel (yd)", 0.20, 2.60), ("Zipper", 1, 0.45), ("Embroidery thread (spool)", 0.04, 4.50)],
    "STK-HOL-01": [("Velvet fabric (yd)", 0.45, 4.80), ("Faux fur cuff", 1, 1.30), ("Embroidery thread (spool)", 0.09, 4.50)],
    "ORN-HOL-02": [("Felt (sheet)", 1, 0.90), ("Embroidery thread (spool)", 0.03, 4.50), ("Ribbon (yd)", 0.30, 0.35)],
    "VEIL-WED-03": [("Tulle (yd)", 0.50, 2.80), ("Embroidery thread (spool)", 0.05, 4.50), ("Hair clip hardware", 1, 0.95)],
    "NAPK-HOME-03": [("Linen fabric (yd)", 0.70, 3.20), ("Embroidery thread (spool)", 0.18, 4.50), ("Packaging", 1, 0.75)],
}

_CHANNELS = ["Shopify", "Etsy"]
_FIRST_NAMES = ["Emma", "Olivia", "Ava", "Sophia", "Isabella", "Mia", "Charlotte", "Amelia", "Harper", "Evelyn", "James", "Liam", "Noah"]
_LAST_NAMES = ["Bennett", "Carter", "Diaz", "Ellis", "Foster", "Grant", "Hayes", "Irving", "Jensen", "Kelly"]


def _sample_order_lines(n_orders: int = 420) -> pd.DataFrame:
    rows = []
    start = dt.date.today() - dt.timedelta(days=365)
    for oid in range(1, n_orders + 1):
        channel = _RNG.choice(_CHANNELS, p=[0.62, 0.38])
        order_date = start + dt.timedelta(days=int(_RNG.integers(0, 365)))
        customer_id = f"CUST-{int(_RNG.integers(1, 140)):04d}"
        n_lines = int(_RNG.integers(1, 4))
        chosen = _RNG.choice(len(_PRODUCT_CATALOG), size=n_lines, replace=True)
        for li, pi in enumerate(chosen):
            sku, name, ptype, unit_cost, base_price = _PRODUCT_CATALOG[pi]
            qty = int(_RNG.integers(1, 4))
            price_noise = _RNG.normal(1.0, 0.05)
            unit_price = round(base_price * max(price_noise, 0.85), 2)
            line_amount = round(unit_price * qty, 2)
            est_cost = round(unit_cost * qty, 2)
            rows.append(dict(
                order_line_id=f"OL-{oid:05d}-{li}",
                order_id=f"ORD-{oid:05d}",
                sales_channel=channel,
                order_date=order_date,
                customer_id=customer_id,
                sku=sku,
                product_name=name,
                product_type=ptype,
                quantity=qty,
                unit_price=unit_price,
                line_amount=line_amount,
                unit_cost=unit_cost,
                estimated_line_cost=est_cost,
                estimated_line_margin=round(line_amount - est_cost, 2),
            ))
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def sample_order_lines() -> pd.DataFrame:
    return _sample_order_lines()


@st.cache_data(show_spinner=False)
def sample_dim_products() -> pd.DataFrame:
    rows = []
    for sku, name, ptype, unit_cost, price in _PRODUCT_CATALOG:
        rows.append(dict(
            sku=sku, product_name=name, product_type=ptype,
            shopify_variant_id=f"SV-{sku}", shopify_product_id=f"SP-{sku[:7]}",
            etsy_listing_id=f"EL-{sku}", quickbooks_item_id=f"QI-{sku}",
            list_price=price, unit_cost=unit_cost,
            sold_on_shopify=True, sold_on_etsy=bool(_RNG.random() > 0.25),
            tracked_in_quickbooks=bool(_RNG.random() > 0.1),
            is_active_on_shopify=True, is_active_on_etsy=bool(_RNG.random() > 0.15),
        ))
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def sample_materials() -> pd.DataFrame:
    rows = []
    for sku, name, ptype, unit_cost, price in _PRODUCT_CATALOG:
        for material, qty, mcost in _MATERIAL_COMPONENTS.get(sku, []):
            rows.append(dict(
                sku=sku, product_name=name, product_type=ptype,
                material=material, qty_per_unit=qty, material_unit_cost=mcost,
                cost_per_unit=round(qty * mcost, 4),
            ))
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def sample_product_performance() -> pd.DataFrame:
    lines = _sample_order_lines()
    g = lines.groupby("sku", as_index=False).agg(
        order_count=("order_id", "nunique"),
        units_sold=("quantity", "sum"),
        gross_revenue=("line_amount", "sum"),
        estimated_total_cost=("estimated_line_cost", "sum"),
        estimated_total_margin=("estimated_line_margin", "sum"),
        first_sold_date=("order_date", "min"),
        last_sold_date=("order_date", "max"),
    )
    meta = pd.DataFrame(_PRODUCT_CATALOG, columns=["sku", "product_name", "product_type", "unit_cost", "list_price"])
    g = g.merge(meta[["sku", "product_name", "product_type"]], on="sku", how="left")
    g["estimated_margin_rate"] = (g["estimated_total_margin"] / g["gross_revenue"]).round(3)
    by_channel = lines.pivot_table(index="sku", columns="sales_channel", values=["quantity", "line_amount"], aggfunc="sum", fill_value=0)
    g["shopify_units_sold"] = g["sku"].map(by_channel[("quantity", "Shopify")]) if ("quantity", "Shopify") in by_channel else 0
    g["shopify_gross_revenue"] = g["sku"].map(by_channel[("line_amount", "Shopify")]) if ("line_amount", "Shopify") in by_channel else 0
    g["etsy_units_sold"] = g["sku"].map(by_channel[("quantity", "Etsy")]) if ("quantity", "Etsy") in by_channel else 0
    g["etsy_gross_revenue"] = g["sku"].map(by_channel[("line_amount", "Etsy")]) if ("line_amount", "Etsy") in by_channel else 0
    return g.sort_values("gross_revenue", ascending=False).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def sample_channel_performance() -> pd.DataFrame:
    lines = _sample_order_lines()
    orders = lines.groupby(["order_id", "sales_channel", "order_date"], as_index=False)["line_amount"].sum()
    orders["order_month"] = pd.to_datetime(orders["order_date"]).values.astype("datetime64[M]")
    g = orders.groupby(["order_month", "sales_channel"], as_index=False).agg(
        order_count=("order_id", "nunique"), gross_sales=("line_amount", "sum"),
    )
    fee_rate = {"Shopify": 0.029, "Etsy": 0.065}
    g["total_discounts"] = (g["gross_sales"] * 0.03).round(2)
    g["total_shipping_collected"] = (g["gross_sales"] * 0.06).round(2)
    g["total_tax_collected"] = (g["gross_sales"] * 0.07).round(2)
    g["gross_revenue"] = (g["gross_sales"] + g["total_shipping_collected"] + g["total_tax_collected"] - g["total_discounts"]).round(2)
    g["total_channel_fees"] = g.apply(lambda r: round(r["gross_revenue"] * fee_rate.get(r["sales_channel"], 0.04), 2), axis=1)
    g["net_revenue"] = (g["gross_revenue"] - g["total_channel_fees"]).round(2)
    g["average_order_value"] = (g["gross_revenue"] / g["order_count"]).round(2)
    g["effective_fee_rate"] = (g["total_channel_fees"] / g["gross_revenue"]).round(4)
    g["refunded_order_count"] = (g["order_count"] * 0.04).round().astype(int)
    g["refund_rate"] = (g["refunded_order_count"] / g["order_count"]).round(3)
    g["total_units_sold"] = (g["order_count"] * 1.6).round().astype(int)
    g["has_estimated_fees"] = True
    return g.sort_values(["order_month", "sales_channel"], ascending=[False, True]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def sample_customer_ltv() -> pd.DataFrame:
    lines = _sample_order_lines()
    orders = lines.groupby(["order_id", "customer_id", "sales_channel", "order_date"], as_index=False)["line_amount"].sum()
    g = orders.groupby("customer_id").agg(
        total_orders=("order_id", "nunique"),
        channels_used=("sales_channel", "nunique"),
        lifetime_gross_revenue=("line_amount", "sum"),
        first_order_date=("order_date", "min"),
        most_recent_order_date=("order_date", "max"),
    ).reset_index()
    g["email"] = [f"{_FIRST_NAMES[i % len(_FIRST_NAMES)].lower()}.{_LAST_NAMES[i % len(_LAST_NAMES)].lower()}@example.com" for i in range(len(g))]
    g["lifetime_net_revenue"] = (g["lifetime_gross_revenue"] * 0.93).round(2)
    g["is_repeat_customer"] = g["total_orders"] > 1
    g["shops_multiple_channels"] = g["channels_used"] > 1
    g["average_order_value"] = (g["lifetime_gross_revenue"] / g["total_orders"]).round(2)
    g["days_since_last_order"] = (pd.Timestamp(dt.date.today()) - pd.to_datetime(g["most_recent_order_date"])).dt.days
    return g.sort_values("lifetime_gross_revenue", ascending=False).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def sample_monthly_pnl() -> pd.DataFrame:
    months = pd.date_range(end=dt.date.today().replace(day=1), periods=12, freq="MS")
    rows = []
    base_rev = 9500
    for i, m in enumerate(months):
        seasonal = 1.0 + 0.35 * np.sin((i / 12) * 2 * np.pi + 1.2) + (0.5 if m.month == 12 else 0)
        revenue = round(base_rev * seasonal * (1 + _RNG.normal(0, 0.05)), 2)
        expenses = round(revenue * (0.55 + _RNG.normal(0, 0.04)), 2)
        rows.append(dict(month=m, total_revenue=revenue, total_expenses=expenses,
                          net_income=round(revenue - expenses, 2),
                          net_margin=round((revenue - expenses) / revenue, 3)))
    return pd.DataFrame(rows).sort_values("month", ascending=False).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def sample_cash_flow_reconciliation() -> pd.DataFrame:
    months = pd.date_range(end=dt.date.today().replace(day=1), periods=12, freq="MS")
    rows = []
    for m in months:
        payouts = round(_RNG.normal(7200, 900), 2)
        variance = round(_RNG.normal(0, 120), 2)
        deposits = round(payouts + variance, 2)
        unmatched = round(abs(variance) if abs(variance) > 60 else 0, 2)
        matched = round(deposits - unmatched, 2)
        rows.append(dict(
            month=m, total_channel_payouts_reported=payouts, total_deposits=deposits,
            matched_deposits=matched, unmatched_or_variance_deposits=unmatched,
            unmatched_deposit_count=int(unmatched > 0),
            deposits_minus_reported_payouts=round(deposits - payouts, 2),
        ))
    return pd.DataFrame(rows).sort_values("month", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Public getters -- BigQuery first, sample fallback second. Each returns
# (dataframe, is_live_data: bool).
# ---------------------------------------------------------------------------

def get_order_lines() -> tuple[pd.DataFrame, bool]:
    df = run_query(f"select * from {table(SCHEMA_COMMERCE, 'fct_order_lines')}")
    if df is not None:
        return df, True
    return sample_order_lines(), False


def get_dim_products() -> tuple[pd.DataFrame, bool]:
    df = run_query(f"select * from {table(SCHEMA_COMMERCE, 'dim_products')}")
    if df is not None:
        return df, True
    return sample_dim_products(), False


def get_materials() -> tuple[pd.DataFrame, bool]:
    # No materials/BOM source exists in the current dbt project (see README /
    # docs/known_gaps.md) -- this always returns the sample bill-of-materials
    # until a real materials data source is modeled.
    return sample_materials(), False


def get_product_performance() -> tuple[pd.DataFrame, bool]:
    df = run_query(f"select * from {table(SCHEMA_REPORTING, 'mart_product_performance')}")
    if df is not None:
        return df, True
    return sample_product_performance(), False


def get_channel_performance() -> tuple[pd.DataFrame, bool]:
    df = run_query(f"select * from {table(SCHEMA_REPORTING, 'mart_channel_performance')}")
    if df is not None:
        return df, True
    return sample_channel_performance(), False


def get_customer_ltv() -> tuple[pd.DataFrame, bool]:
    df = run_query(f"select * from {table(SCHEMA_REPORTING, 'mart_customer_ltv')}")
    if df is not None:
        return df, True
    return sample_customer_ltv(), False


def get_monthly_pnl() -> tuple[pd.DataFrame, bool]:
    df = run_query(f"select * from {table(SCHEMA_REPORTING, 'mart_monthly_pnl_snapshot')}")
    if df is not None:
        return df, True
    return sample_monthly_pnl(), False


def get_cash_flow_reconciliation() -> tuple[pd.DataFrame, bool]:
    df = run_query(f"select * from {table(SCHEMA_REPORTING, 'mart_cash_flow_reconciliation')}")
    if df is not None:
        return df, True
    return sample_cash_flow_reconciliation(), False
