"""Talk to Your Data -- a Claude-powered chatbot grounded in docs/*.md and a
live snapshot of the current mart data. See utils/chat.py for the design
notes on why this is context-stuffing rather than a live text-to-SQL agent."""

from __future__ import annotations

import streamlit as st

from utils import bq
from utils.chat import anthropic_configured, ask, build_data_snapshot
from utils.ui import page_header

st.set_page_config(page_title="Talk to Your Data | Saul Stitch House", page_icon="🧵", layout="wide")

page_header("Talk to Your Data", "Ask questions in plain English -- answers are grounded in your dashboard's data and docs.")

if not anthropic_configured():
    st.info(
        "This chatbot needs an Anthropic API key. Add it to `.streamlit/secrets.toml` as "
        "`[anthropic]\\napi_key = \"sk-ant-...\"` (see `README.md`), then reload this page.",
        icon="🔑",
    )
    st.markdown(
        "In the meantime, the **AI Insights** page's rule-based findings and the "
        "**docs/** files (`data_dictionary.md`, `business_glossary.md`, `known_gaps.md`) "
        "answer most \"what does this mean\" and \"why is this a sample\" questions directly."
    )
    st.stop()

with st.expander("What can I ask?"):
    st.markdown(
        "- \"Which product has the best margin right now?\"\n"
        "- \"How much of my revenue comes from Etsy vs. Shopify?\"\n"
        "- \"Why are some fee numbers estimated?\"\n"
        "- \"What's my repeat customer rate?\"\n"
        "- \"Is the Materials page real data?\"\n\n"
        "Answers are grounded in the current dashboard data snapshot and the docs in `docs/` "
        "-- not a live database query, so very specific row-level questions are better answered "
        "on the relevant dashboard page (e.g. Product Catalog for a single order line)."
    )

product_perf, live_pp = bq.get_product_performance()
channel_perf, live_cp = bq.get_channel_performance()
customer_ltv, live_ltv = bq.get_customer_ltv()
monthly_pnl, live_pnl = bq.get_monthly_pnl()
cash_flow, live_cf = bq.get_cash_flow_reconciliation()
materials, _ = bq.get_materials()

overall_live = all([live_pp, live_cp, live_ltv, live_pnl, live_cf])
data_snapshot = build_data_snapshot(
    product_perf, channel_perf, customer_ltv, monthly_pnl, cash_flow, materials, overall_live,
)

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

for msg in st.session_state["chat_history"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("Ask about your sales, products, customers, or finances...")

if question:
    st.session_state["chat_history"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer = ask(question, data_snapshot, st.session_state["chat_history"][:-1])
            except Exception as e:
                answer = f"Something went wrong calling Claude: {e}"
        st.markdown(answer)
    st.session_state["chat_history"].append({"role": "assistant", "content": answer})

if st.session_state["chat_history"]:
    if st.button("Clear conversation"):
        st.session_state["chat_history"] = []
        st.rerun()
