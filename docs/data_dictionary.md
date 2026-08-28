# Data Dictionary -- Saul Stitch House Analytics

This describes the tables the dashboard (and the "Talk to Your Data" chatbot)
reads from. All of them are dbt **marts** built on top of Fivetran syncs from
QuickBooks Online, Shopify, and Etsy. Source: `saul_stitch_house_analytics`
dbt project, `models/marts/`.

## Commerce marts (`{dataset}_marts_commerce`)

### `dim_products`
One row per SKU, reconciling the product catalog across Shopify, Etsy, and
QuickBooks. Key columns: `sku`, `product_name`, `product_type`, `list_price`,
`unit_cost`, `sold_on_shopify`, `sold_on_etsy`, `tracked_in_quickbooks`,
`is_active_on_shopify`, `is_active_on_etsy`. A product that only exists on one
channel still gets a row -- the boolean flags make catalog gaps visible.

### `dim_customers`
One row per unique customer email, deduplicated across Shopify, Etsy, and
QuickBooks.

### `fct_orders`
One row per order across Shopify and Etsy -- the operational source of truth
for "what did we sell." Includes `sales_channel`, `order_date`,
`total_amount`, discounts, shipping, tax, and channel fees.

### `fct_order_lines`
One row per order line (grain: line item). Joined to `dim_products` by SKU
for margin math: `estimated_line_cost` = `unit_cost * quantity`,
`estimated_line_margin` = `line_amount - estimated_line_cost`. This is the
table the **Product Catalog** dashboard page and the line-item drill-down are
built from.

## Finance marts (`{dataset}_marts_finance`)

### `dim_chart_of_accounts`
QuickBooks chart of accounts, with `classification` (Asset / Liability /
Equity / Revenue / Expense).

### `fct_revenue_transactions`
One row per QuickBooks transaction that recognizes revenue (sales receipts +
invoices, net of credit memos and refund receipts). The accounting source of
truth for revenue, as opposed to `fct_orders` which is the operational view.

### `fct_channel_payouts`
Daily gross/fee/net summary by sales channel, sourced entirely from Shopify +
Etsy (no QuickBooks dependency) -- what the channels *say* they paid out.

### `fct_deposit_reconciliation`
One row per QuickBooks bank deposit, matched (or not) to a channel payout.
`reconciliation_status` is one of `matched`, `matched_with_variance`,
`unmatched`.

## Reporting marts (`{dataset}_marts_reporting`) -- these back the dashboard pages directly

### `mart_channel_performance`
Grain: one row per sales channel per month. Gross revenue, discounts, fees,
net revenue, order volume, AOV. **Backs the Channel Performance page.**

### `mart_product_performance`
Grain: one row per SKU. Revenue, units, and estimated margin, with a
Shopify/Etsy split. **Backs the Product Catalog page's summary view.**

### `mart_customer_ltv`
Grain: one row per customer. Lifetime value, repeat-purchase behavior,
`is_repeat_customer`, `shops_multiple_channels`, `days_since_last_order`.
**Backs the Customer LTV page.**

### `mart_monthly_pnl_snapshot`
Grain: one row per month. `total_revenue`, `total_expenses`, `net_income`,
`net_margin` -- a lightweight P&L sourced from QuickBooks bills and
purchases. **Not a substitute for the accountant's official financials**: it
doesn't handle accruals, depreciation, or owner's equity. **Backs the
Financial Overview page.**

### `mart_cash_flow_reconciliation`
Grain: one row per month. Rolls up channel payouts vs. QuickBooks bank
deposits so the owner can see whether payouts channels reported actually hit
the bank, and how much is still unreconciled. **Backs the Financial Overview
page's reconciliation section.**

## Known caveats that matter when answering questions

- **Shopify fee amounts are frequently estimated**, not exact -- see
  `has_estimated_fees` / `is_fee_estimated` flags. Don't state Shopify fee
  numbers as precise; call them estimates.
- **Etsy-vs-Shopify deposit matching is best-effort**, based on amount and
  date proximity (see `int_deposit_matching` in the dbt project) -- treat
  `day_difference` / `amount_difference` as data-quality signals, not
  guarantees.
- The **monthly P&L is directional**, not GAAP-complete.
- See `known_gaps.md` for what this data model does **not** yet track (most
  importantly: no bill-of-materials / raw-materials cost data source exists
  yet -- the Materials page runs on illustrative sample data until that's
  built).
