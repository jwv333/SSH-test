"""
"Talk to Your Data" chatbot.

Powered by Claude + the markdown files in docs/ (data_dictionary.md,
business_glossary.md, known_gaps.md) as its knowledge base, per the owner's
explicit request: "a talk to my data chatbot powered by claude and .md files
that we will create."

Design: this is a context-stuffing / RAG-lite pattern, not a live text-to-SQL
agent. The three docs files are small enough to pass in full as system
context every turn, along with a compact statistical summary of the current
mart tables (row counts, date ranges, top-line aggregates) computed fresh
each session so answers can reference real current numbers without giving
the model raw row-level data or SQL execution access. This keeps answers
grounded, keeps the docs as the single source of truth for definitions and
caveats, and avoids the cost/complexity of a full agentic SQL loop for what
is, for now, a small single-store business.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

SYSTEM_PREAMBLE = """You are the "Talk to Your Data" assistant embedded in the Saul Stitch House
analytics dashboard. Saul Stitch House is a monogramming/embroidery gift business selling through
Shopify and Etsy, with QuickBooks Online as the accounting system of record.

You answer questions from the business owner about their own sales, product, customer, and
financial data. You are given (1) reference docs describing the data model, glossary, and known
gaps, and (2) a snapshot of current summary statistics computed from the live (or sample) data.

Rules:
- Only use the numbers given to you in the data snapshot below. Never invent or estimate a number
  that isn't present in the snapshot -- if the owner asks something the snapshot can't answer,
  say so plainly and suggest which dashboard page might have it (Product Catalog, Materials,
  Channel Performance, Customer LTV, Financial Overview, AI Insights).
- Always check known_gaps.md before answering -- if the question touches something documented
  there as a gap or estimate (materials/BOM, Shopify fee estimates, deposit matching, P&L
  limitations, or sample-data mode), say so and flag the caveat rather than answering as if the
  number were precise or complete.
- Write like you're talking to a small business owner, not a data analyst: plain English, lead
  with the answer, short. Use numbers/currency formatting like "$1,234" and "12.3%".
- If asked to do something outside this data (e.g. place an order, change a price, send an
  email), say that's outside what this chatbot can do.
"""


@st.cache_data(show_spinner=False)
def load_docs_context() -> str:
    """Concatenate the docs/*.md files into one context blob. Cached for the
    process lifetime since these files only change when someone edits the repo."""
    parts = []
    for fname in ["data_dictionary.md", "business_glossary.md", "known_gaps.md"]:
        fpath = DOCS_DIR / fname
        if fpath.exists():
            parts.append(f"### {fname}\n\n{fpath.read_text()}")
    return "\n\n---\n\n".join(parts)


def _safe_stats(df: pd.DataFrame, label: str, cols: list[str]) -> str:
    if df is None or df.empty:
        return f"{label}: no data available.\n"
    lines = [f"{label} ({len(df)} rows):"]
    for c in cols:
        if c not in df.columns:
            continue
        series = df[c].dropna()
        if series.empty:
            continue
        if pd.api.types.is_numeric_dtype(series):
            lines.append(
                f"  - {c}: sum={series.sum():,.2f}, mean={series.mean():,.2f}, "
                f"min={series.min():,.2f}, max={series.max():,.2f}"
            )
        elif pd.api.types.is_datetime64_any_dtype(series):
            lines.append(f"  - {c}: range {series.min()} to {series.max()}")
        else:
            top = series.value_counts().head(5)
            lines.append(f"  - {c} top values: {dict(top)}")
    return "\n".join(lines) + "\n"


def build_data_snapshot(
    product_perf: pd.DataFrame,
    channel_perf: pd.DataFrame,
    customer_ltv: pd.DataFrame,
    monthly_pnl: pd.DataFrame,
    cash_flow: pd.DataFrame,
    materials: pd.DataFrame,
    is_live: bool,
) -> str:
    """Compact statistical summary of current mart data -- refreshed each
    session, passed to Claude as grounding context instead of raw rows."""
    mode = "LIVE BigQuery data" if is_live else "SAMPLE data (BigQuery not yet connected / synced)"
    parts = [f"Data mode: {mode}\n"]
    parts.append(_safe_stats(
        product_perf, "Product performance",
        ["gross_revenue", "estimated_total_margin", "estimated_margin_rate", "units_sold"],
    ))
    parts.append(_safe_stats(
        channel_perf, "Channel performance (monthly)",
        ["gross_revenue", "net_revenue", "effective_fee_rate", "order_count", "average_order_value"],
    ))
    parts.append(_safe_stats(
        customer_ltv, "Customer LTV",
        ["lifetime_gross_revenue", "total_orders", "is_repeat_customer", "days_since_last_order"],
    ))
    parts.append(_safe_stats(
        monthly_pnl, "Monthly P&L",
        ["total_revenue", "total_expenses", "net_income", "net_margin"],
    ))
    parts.append(_safe_stats(
        cash_flow, "Cash flow reconciliation",
        ["total_deposits", "matched_deposits", "unmatched_or_variance_deposits"],
    ))
    parts.append(_safe_stats(
        materials, "Materials (SAMPLE / illustrative -- see known_gaps.md)",
        ["material_unit_cost", "qty_per_unit", "cost_per_unit"],
    ))
    return "\n".join(parts)


def anthropic_configured() -> bool:
    try:
        key = st.secrets.get("anthropic", {}).get("api_key")
    except Exception:
        key = None
    return bool(key or os.environ.get("ANTHROPIC_API_KEY"))


def _client():
    import anthropic
    key = None
    try:
        key = st.secrets.get("anthropic", {}).get("api_key")
    except Exception:
        pass
    key = key or os.environ.get("ANTHROPIC_API_KEY")
    return anthropic.Anthropic(api_key=key)


def _model_name() -> str:
    try:
        m = st.secrets.get("anthropic", {}).get("model")
    except Exception:
        m = None
    return m or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")


def ask(question: str, data_snapshot: str, chat_history: list[dict]) -> str:
    """Ask Claude a question grounded in the docs + data snapshot. chat_history
    is a list of {"role": "user"|"assistant", "content": str} from prior turns
    in this session (excluding the current question)."""
    client = _client()
    system = (
        SYSTEM_PREAMBLE
        + "\n\n## Reference docs\n\n"
        + load_docs_context()
        + "\n\n## Current data snapshot\n\n"
        + data_snapshot
    )
    messages = list(chat_history) + [{"role": "user", "content": question}]
    resp = client.messages.create(
        model=_model_name(),
        max_tokens=800,
        system=system,
        messages=messages,
    )
    return "".join(block.text for block in resp.content if hasattr(block, "text"))
