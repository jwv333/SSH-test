"""
Rule-based business insights, with an optional Claude-written narrative on
top. The rules run with no API key required -- they're plain pandas/threshold
logic over the mart tables. If an Anthropic API key is configured, the
"Generate narrative" button turns the same rule outputs into a short,
plain-English write-up; without a key, the rule cards still work standalone.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

SEVERITY_ORDER = {"critical": 0, "serious": 1, "warning": 2, "good": 3, "info": 4}


@dataclass
class Insight:
    severity: str  # good | warning | serious | critical | info
    title: str
    detail: str


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _money(x: float) -> str:
    return f"${x:,.0f}"


def generate_insights(
    product_perf: pd.DataFrame,
    channel_perf: pd.DataFrame,
    customer_ltv: pd.DataFrame,
    monthly_pnl: pd.DataFrame,
    cash_flow: pd.DataFrame,
) -> list[Insight]:
    out: list[Insight] = []

    # --- Product margin outliers -------------------------------------------------
    if not product_perf.empty and "estimated_margin_rate" in product_perf:
        pp = product_perf.dropna(subset=["estimated_margin_rate"])
        if not pp.empty:
            worst = pp.sort_values("estimated_margin_rate").iloc[0]
            best = pp.sort_values("estimated_margin_rate", ascending=False).iloc[0]
            if worst["estimated_margin_rate"] < 0.25:
                out.append(Insight(
                    "warning" if worst["estimated_margin_rate"] > 0 else "serious",
                    f"Thin margin on {worst['product_name']}",
                    f"Estimated margin is {_pct(worst['estimated_margin_rate'])} on "
                    f"{worst['sku']}, well below the catalog average of "
                    f"{_pct(pp['estimated_margin_rate'].mean())}. Worth a price or "
                    f"cost review if volume is meaningful ({int(worst['units_sold'])} units sold).",
                ))
            out.append(Insight(
                "good",
                f"{best['product_name']} is your best margin performer",
                f"{_pct(best['estimated_margin_rate'])} estimated margin, "
                f"{_money(best['gross_revenue'])} in revenue. Consider featuring it "
                f"more prominently or bundling it with lower-margin items.",
            ))
            top_rev = pp.sort_values("gross_revenue", ascending=False).head(3)
            share = top_rev["gross_revenue"].sum() / pp["gross_revenue"].sum() if pp["gross_revenue"].sum() else 0
            if share > 0.5:
                out.append(Insight(
                    "warning",
                    "Revenue is concentrated in a few SKUs",
                    f"Your top 3 products ({', '.join(top_rev['product_name'].tolist())}) "
                    f"make up {_pct(share)} of catalog revenue. A slowdown in any one "
                    f"of them will show up in overall revenue quickly.",
                ))

    # --- Channel fee comparison ----------------------------------------------------
    if not channel_perf.empty and "effective_fee_rate" in channel_perf:
        latest_month = channel_perf["order_month"].max()
        cur = channel_perf[channel_perf["order_month"] == latest_month]
        for _, row in cur.iterrows():
            if pd.notna(row.get("effective_fee_rate")) and row["effective_fee_rate"] > 0.07:
                out.append(Insight(
                    "warning",
                    f"{row['sales_channel']} effective fee rate is high",
                    f"{_pct(row['effective_fee_rate'])} of gross revenue went to fees "
                    f"on {row['sales_channel']} last month"
                    + (" (partly estimated)" if row.get("has_estimated_fees") else "")
                    + ". Compare against the other channel to see if pricing needs to "
                    "absorb more of that, or if it's within normal range for that platform.",
                ))
        if set(cur["sales_channel"]) >= {"Shopify", "Etsy"}:
            shop = cur[cur["sales_channel"] == "Shopify"]["gross_revenue"].sum()
            etsy = cur[cur["sales_channel"] == "Etsy"]["gross_revenue"].sum()
            total = shop + etsy
            if total > 0 and etsy / total > 0.5:
                out.append(Insight(
                    "info",
                    "Etsy is your larger channel this month",
                    f"Etsy: {_money(etsy)} vs Shopify: {_money(shop)}. Etsy typically "
                    f"carries higher effective fees, so growth there costs more per "
                    f"dollar than the same growth on Shopify.",
                ))

    # --- Customer concentration / repeat rate --------------------------------------
    if not customer_ltv.empty:
        repeat_rate = customer_ltv["is_repeat_customer"].mean()
        out.append(Insight(
            "good" if repeat_rate > 0.2 else "info",
            "Repeat customer rate",
            f"{_pct(repeat_rate)} of customers have ordered more than once. "
            + ("Solid repeat behavior for a gift/monogramming business."
               if repeat_rate > 0.2 else
               "Consider a post-purchase email or loyalty nudge to lift repeat orders."),
        ))
        stale = customer_ltv[customer_ltv["days_since_last_order"] > 180]
        if not stale.empty:
            stale_value = stale["lifetime_gross_revenue"].sum()
            out.append(Insight(
                "info",
                f"{len(stale)} customers haven't ordered in 6+ months",
                f"They represent {_money(stale_value)} of historical revenue -- a "
                f"reasonable win-back email or discount audience.",
            ))

    # --- P&L trend -------------------------------------------------------------------
    if not monthly_pnl.empty and len(monthly_pnl) >= 2:
        pnl = monthly_pnl.sort_values("month")
        last, prev = pnl.iloc[-1], pnl.iloc[-2]
        if pd.notna(last.get("net_margin")):
            delta = last["net_margin"] - prev["net_margin"]
            sev = "good" if delta >= 0 else ("warning" if delta > -0.05 else "serious")
            direction = "up" if delta >= 0 else "down"
            out.append(Insight(
                sev,
                f"Net margin {direction} {_pct(abs(delta))} month over month",
                f"Net margin was {_pct(last['net_margin'])} last month vs "
                f"{_pct(prev['net_margin'])} the month before "
                f"(revenue {_money(last['total_revenue'])}, expenses {_money(last['total_expenses'])}).",
            ))

    # --- Cash flow reconciliation ----------------------------------------------------
    if not cash_flow.empty:
        cf = cash_flow.sort_values("month")
        last = cf.iloc[-1]
        unmatched = last.get("unmatched_or_variance_deposits", 0) or 0
        total_dep = last.get("total_deposits", 0) or 0
        if total_dep and unmatched / total_dep > 0.05:
            out.append(Insight(
                "serious",
                "Meaningful unreconciled deposits last month",
                f"{_money(unmatched)} ({_pct(unmatched / total_dep)}) of deposits "
                f"didn't cleanly match a reported channel payout. Worth a manual "
                f"look in QuickBooks + the channel payout reports before it compounds.",
            ))
        elif total_dep:
            out.append(Insight(
                "good",
                "Deposits are reconciling cleanly",
                f"Only {_pct(unmatched / total_dep)} of last month's deposits are "
                f"unmatched -- reconciliation looks healthy.",
            ))

    out.sort(key=lambda i: SEVERITY_ORDER.get(i.severity, 9))
    return out


# ---------------------------------------------------------------------------
# Optional: turn the rule outputs into a short narrative with Claude.
# ---------------------------------------------------------------------------

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


def model_name() -> str:
    try:
        m = st.secrets.get("anthropic", {}).get("model")
    except Exception:
        m = None
    return m or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")


def narrative_from_insights(insights: list[Insight], business_context: str) -> str:
    """Ask Claude to turn the rule-based findings into a short owner-facing
    narrative. Raises if no API key is configured -- callers should check
    anthropic_configured() first and hide the button otherwise."""
    client = _client()
    bullets = "\n".join(f"- [{i.severity}] {i.title}: {i.detail}" for i in insights)
    prompt = (
        "You are writing a short weekly business note for the owner of a small "
        "monogramming/embroidery gift shop, based on pre-computed findings below. "
        "Do not invent numbers beyond what's given. Group related points, lead with "
        "the most important 1-2 things, keep it under 200 words, plain language, "
        "no bullet-point spam -- write it as 2-4 short paragraphs.\n\n"
        f"Business context:\n{business_context}\n\nFindings:\n{bullets}"
    )
    resp = client.messages.create(
        model=model_name(),
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in resp.content if hasattr(block, "text"))
