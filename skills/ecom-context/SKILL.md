---
name: ecom-context
description: >
  EC business model detection and baseline context. Identifies D2C, marketplace,
  subscription, or O2O model from order data. Provides industry-specific
  benchmarks and data quality assessment. Called as a prerequisite by all other
  ecom sub-skills.
  Triggers on: "ecommerce context", "business model detection", "industry classification", "benchmarks".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# ecom-context — EC Business Context Foundation

Detects the ecommerce business model and provides baseline benchmarks for all
downstream analyses.

## Process

1. **Load data** — read orders CSV (minimum), products CSV (optional)
2. **Read references** — Load from `ecom-analytics/references/`: `benchmarks.md`, `data-formats.md`
3. **Detect business model** — apply decision tree below
4. **Provide benchmarks** — return industry-appropriate KPI targets

## Business Model Detection

```
IF subscription_rate > 30%       → Subscription
ELIF sku_count > 10,000          → Marketplace
ELIF physical_store_data present → O2O
ELSE                             → D2C
```

### Signals to Check

| Signal | Source | Threshold |
|--------|--------|-----------|
| Recurring order pattern | Order frequency per customer | > 30% customers with regular intervals |
| SKU breadth | Products CSV | > 10,000 unique SKUs |
| Multiple sellers | Vendor column | > 1 distinct vendor |
| Store location | Billing/shipping data | Physical address patterns |

## Output

- Business model: D2C / Marketplace / Subscription / O2O
- Industry vertical: Fashion / Food / Electronics / Beauty / Home / General
- Scale tier: Small (<1M), Medium (1-10M), Large (10-100M), Enterprise (100M+)
- Applicable benchmarks from `ecom-analytics/references/benchmarks.md`
- Data quality summary: completeness, date range, customer count

## Data Quality Checks

| Check | Pass Criteria |
|-------|--------------|
| Date range | > 90 days of data |
| Order count | > 100 orders |
| Customer IDs | > 80% populated |
| Amount values | No negative amounts (excl. refunds) |
| Duplicates | < 1% duplicate order IDs |
