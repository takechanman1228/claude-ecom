---
name: ecom-shopify-import
version: 0.2.0
description: >
  Shopify Admin API integration for ecom-analytics. Imports order-level,
  product, and inventory data via Bulk Operations, enabling ~30 additional
  audit checks that require transaction-level data (R07 customer concentration,
  C11 days-to-2nd-purchase, O01-O10 inventory checks, P05+ product analysis).
  Triggers on: "shopify import", "shopify sync", "shopify api setup",
  "connect shopify", "shopify data".
argument-hint: "setup | sync"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# ecom-shopify-import — Shopify Admin API Data Import

Imports transaction-level data from Shopify Admin API using Bulk Operations,
normalizes it into the canonical ecom-analytics schema, and enables the full
84-check audit suite.

## Prerequisites

1. **Shopify Custom App** with the following scopes:
   - `read_orders` — order and line-item data
   - `read_products` — product catalog and variants
   - `read_inventory` — inventory levels by location

2. **Create the Custom App:**
   - Shopify Admin → Settings → Apps and sales channels → Develop apps
   - Create app → Configure Admin API scopes → Install app
   - Copy the Admin API access token (starts with `shpat_`)

## Workflow

### Step 1: Setup

```bash
ecom-analytics shopify setup
```

Interactive prompts for:
- Store domain (e.g. `my-store.myshopify.com`)
- Admin API access token
- API version (default: `2025-01`)
- Timezone and currency

Creates `.ecom-analytics/config.toml` (auto-added to `.gitignore`).

Alternatively, set `SHOPIFY_ACCESS_TOKEN` env var to override the file token.

### Step 2: Sync

```bash
ecom-analytics shopify sync --since 2024-01-01
```

Runs 3 sequential Bulk Operations:
1. **Orders + LineItems** — all orders since the given date
2. **Products + Variants** — full product catalog
3. **InventoryItems + Levels** — current inventory by location

Output saved to `.ecom-analytics/data/` as Parquet (or CSV fallback).

Options:
- `--mode full|incremental` — full re-sync or merge with existing data
- `--until 2024-12-31` — end date filter
- `--timeout-minutes 120` — max wait per bulk operation

### Step 3: Audit

```bash
ecom-analytics audit --source shopify --since 2024-01-01
```

Or, if data is already synced:
```bash
ecom-analytics audit --source shopify --since 2024-01-01
```

Produces the standard reports: AUDIT-REPORT.md, ACTION-PLAN.md, QUICK-WINS.md.

## Checks Enabled by API Data

These checks require transaction-level data not available from aggregated CSV exports:

| Check | Description |
|-------|-------------|
| R07 | Top 10% customer revenue concentration |
| C11 | Average days to 2nd purchase |
| O01-O10 | Full inventory health suite (stockout rate, overstock, deadstock, turnover) |
| P05 | Product lifecycle stage analysis |
| P06 | Cross-sell pair discovery |
| P07 | Category performance breakdown |
| PR01-PR02 | Discount dependency analysis (order-level) |

## Data Flow

```
Shopify Admin API (GraphQL Bulk Operations)
    ↓ JSONL (parent-child linked via __parentId)
normalize.py
    ↓ Flat DataFrames (orders, order_items, products, inventory)
build_orders_compat()
    ↓ Canonical schema (matches loader.py CSV output)
metrics.py / cohort.py / product.py / inventory.py / pricing.py
    ↓ KPIs and check results
scoring.py → report.py
    ↓ AUDIT-REPORT.md, ACTION-PLAN.md, QUICK-WINS.md
```

## Reference

See `ecom-analytics/references/data-formats.md` for the complete column mapping
between Shopify API fields and the canonical internal schema.

## Security

- Access tokens are stored in `.ecom-analytics/config.toml`
- `.ecom-analytics/` is automatically added to `.gitignore`
- `SHOPIFY_ACCESS_TOKEN` env var always overrides file token
- Customer emails are SHA-256 hashed by default (use `--allow-pii` to opt in)
