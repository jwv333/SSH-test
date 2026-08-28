# Saul Stitch House -- Analytics Dashboard

A Streamlit dashboard on top of the `saul_stitch_house_analytics` dbt project
(QuickBooks + Shopify + Etsy, synced via Fivetran into BigQuery).

## Pages

- **Overview** (`app.py`) -- executive KPIs, revenue by channel, net margin trend, top products.
- **Product Catalog** -- line-item order detail (`fct_order_lines`) with filters, plus the per-SKU catalog summary (`mart_product_performance`).
- **Materials** -- bill of materials per product. **Runs on illustrative sample data** -- no materials/BOM source exists in QuickBooks, Shopify, or Etsy today. See `docs/known_gaps.md`.
- **Channel Performance** -- Shopify vs. Etsy: revenue, fees, AOV, order volume by month (`mart_channel_performance`).
- **Customer LTV** -- lifetime value, repeat rate, recency (`mart_customer_ltv`).
- **Financial Overview** -- monthly P&L snapshot and cash-flow reconciliation (`mart_monthly_pnl_snapshot`, `mart_cash_flow_reconciliation`).
- **AI Insights** -- rule-based findings (margin outliers, fee rates, retention, reconciliation health) with an optional Claude-written narrative.
- **Talk to Your Data** -- a Claude-powered chatbot grounded in `docs/*.md` and a live snapshot of your current numbers.

Every page works out of the box on realistic **sample data** with no setup,
so you can review the whole app before BigQuery is connected. Any page not
yet backed by live data shows a `📊 Showing sample data` banner.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Connect BigQuery (optional -- app runs on sample data without this)

Copy the secrets template and fill in your project + a service account key
(read-only: BigQuery Data Viewer + BigQuery Job User is enough):

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml`:
- `bigquery.project_id` -- your GCP project ID.
- `bigquery.dataset` -- the dbt `dataset:` target name (default `analytics`; see `profiles.example.yml` in the dbt project). The app reads from `{dataset}_marts_commerce`, `{dataset}_marts_finance`, and `{dataset}_marts_reporting`, matching the dbt project's `generate_schema_name` macro.
- `bigquery.service_account` -- paste the full JSON key contents.

Each page tries BigQuery first and falls back to sample data automatically
if a table isn't there yet (e.g. before the Fivetran syncs finish), so it's
safe to connect BigQuery before every connector is live.

### 3. Enable AI Insights narrative + Talk to Your Data (optional)

Add an Anthropic API key to the same `secrets.toml`:

```toml
[anthropic]
api_key = "sk-ant-..."
model = "claude-sonnet-4-5"  # optional
```

Without a key, the AI Insights page still shows its rule-based findings
(no API key needed for those); the narrative button and the Talk to Your
Data chatbot are hidden with instructions to add a key.

### 4. Run it

```bash
streamlit run app.py
```

## Project layout

```
app.py                        Overview page (entry point)
pages/
  1_Product_Catalog.py
  2_Materials.py
  3_Channel_Performance.py
  4_Customer_LTV.py
  5_Financial_Overview.py
  6_AI_Insights.py
  7_Talk_to_Your_Data.py
utils/
  bq.py                        BigQuery access layer + sample-data fallback
  theme.py                     Chart color tokens (Anthropic dataviz skill palette)
  ui.py                        Shared UI helpers (banners, formatting)
  insights.py                  Rule-based insight engine + optional Claude narrative
  chat.py                      Talk to Your Data chatbot (Claude + docs/*.md)
docs/
  data_dictionary.md           Table/column reference for the dashboard + chatbot
  business_glossary.md         Terms (AOV, LTV, channel fees, etc.)
  known_gaps.md                What this data model doesn't track yet, and why
.streamlit/
  config.toml                  Theme
  secrets.toml.example         Copy to secrets.toml and fill in
```

## Notes on accuracy

- Shopify channel fees are frequently **estimated**, not exact.
- Deposit-to-payout matching is **best-effort** (amount + date proximity).
- The monthly P&L is **directional**, not a GAAP-complete financial statement.
- The Materials page is **sample data** until a real bill-of-materials source is modeled.

See `docs/known_gaps.md` for the full list -- it's also what the Talk to
Your Data chatbot uses to flag these caveats in its answers.
