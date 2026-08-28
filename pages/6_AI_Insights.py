"""AI Insights and Recommendations.

Rule-based findings (no API key required) computed from the mart tables,
with an optional Claude-written narrative on top when an Anthropic API key
is configured in .streamlit/secrets.toml.
"""

from __future__ import annotations

import streamlit as st

from utils import bq
from utils.insights import anthropic_configured, generate_insights, model_name, narrative_from_insights
from utils.ui import page_header, sample_banner, status_badge

st.set_page_config(page_title="AI Insights | Saul Stitch House", page_icon="🧵", layout="wide")

page_header("AI Insights & Recommendations", "Automated findings from your sales, margin, and cash-flow data.")

product_perf, live_pp = bq.get_product_performance()
channel_perf, live_cp = bq.get_channel_performance()
customer_ltv, live_ltv = bq.get_customer_ltv()
monthly_pnl, live_pnl = bq.get_monthly_pnl()
cash_flow, live_cf = bq.get_cash_flow_reconciliation()

sample_banner(all([live_pp, live_cp, live_ltv, live_pnl, live_cf]))

insights = generate_insights(product_perf, channel_perf, customer_ltv, monthly_pnl, cash_flow)

if not insights:
    st.caption("Not enough data yet to generate insights.")
    st.stop()

st.markdown("### Findings")
st.caption("Plain rule-based checks over your current numbers -- margin outliers, fee rates, retention, and reconciliation health. No API key required for this section.")

for ins in insights:
    with st.container(border=True):
        st.markdown(f"{status_badge(ins.severity)} &nbsp; **{ins.title}**", unsafe_allow_html=True)
        st.write(ins.detail)

st.markdown("---")
st.markdown("### AI-written summary")

if anthropic_configured():
    st.caption(f"Powered by Claude ({model_name()}) -- turns the findings above into a short owner-facing note. Doesn't invent numbers beyond what's shown above.")
    if st.button("Generate narrative", type="primary"):
        with st.spinner("Writing your summary..."):
            try:
                narrative = narrative_from_insights(
                    insights,
                    business_context=(
                        "Saul Stitch House is a monogramming/embroidery gift business selling "
                        "through Shopify and Etsy, with QuickBooks Online as the books of record."
                    ),
                )
                st.session_state["_insights_narrative"] = narrative
            except Exception as e:
                st.error(f"Couldn't generate a narrative right now: {e}")
    if st.session_state.get("_insights_narrative"):
        st.info(st.session_state["_insights_narrative"], icon="✨")
else:
    st.info(
        "Add an Anthropic API key to `.streamlit/secrets.toml` (see `README.md`) to turn "
        "these findings into a short written narrative. The rule-based findings above work "
        "without any API key.",
        icon="🔑",
    )
