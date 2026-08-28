# Known Gaps -- read this before answering "why don't you know X"

## No materials / bill-of-materials data source (yet)

The dbt project models QuickBooks, Shopify, and Etsy -- none of which track
**raw materials** (fabric, thread, blanks, trim) as a bill-of-materials
against a finished SKU. `dim_products.unit_cost` is a single blended
per-unit cost pulled from whichever system has it (QuickBooks item cost, or
Shopify inventory item cost) -- it is **not** a materials breakdown.

The dashboard's **Materials** page therefore runs on illustrative **sample**
data (a plausible bill-of-materials Claude constructed for the existing
product catalog) so the page's layout and interactions can be reviewed now.
It is clearly labeled as sample data in the app. To make it real, one of the
following needs to happen:

- Track material components as separate QuickBooks inventory items with a
  documented SKU-to-materials mapping (e.g. an assembly/kit relationship, or
  a maintained spreadsheet loaded as a dbt seed), or
- Adopt inventory/production software that tracks BOM and sync it into
  BigQuery as a new source, or
- Maintain a manual `materials_bom` seed file in the dbt project mapping
  each SKU to its components and per-unit material cost.

Until one of those exists, do not present Materials-page numbers as real
inventory or COGS data -- they are for layout/preview purposes only.

## Other caveats worth surfacing when relevant

- **Shopify channel fees are frequently estimated**, not the exact fee
  Shopify charged (see `has_estimated_fees` / `is_fee_estimated`).
- **Deposit-to-payout matching is best-effort**, based on amount + date
  proximity, especially for Shopify (Etsy's own ledger makes this more
  exact).
- **The monthly P&L snapshot is directional**, not a GAAP-complete
  financial statement -- no accruals, depreciation, or owner's equity
  handling.
- **No data is flowing yet** until the QuickBooks, Shopify, and Etsy Fivetran
  connectors finish their initial syncs -- until then, every page in this
  dashboard is running on sample data, clearly labeled.
