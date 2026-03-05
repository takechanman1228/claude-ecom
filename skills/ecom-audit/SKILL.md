---
name: ecom-audit
description: >
  Full EC store audit with parallel sub-agent delegation. Analyses revenue
  structure, conversion, product performance, inventory, retention/LTV, and
  pricing across 84 checks. Generates unified health score and three report
  files. Triggers on: "ecommerce audit", "store diagnosis", "full analysis",
  "store health check".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# ecom-audit — Full EC Store Audit

Orchestrates a comprehensive 84-check audit across 6 categories, delegating to
sub-agents for parallel execution.

## Process

1. **Collect data** — request orders CSV + products CSV + inventory CSV
2. **Detect business model** — delegate to `ecom-context`
3. **Delegate to sub-agents** (parallel):
   - `audit-revenue` — R01-R15 checks → `ecom-revenue`
   - `audit-product` — P01-P20 checks → `ecom-product`, `ecom-inventory`
   - `audit-retention` — C01-C15 checks → `ecom-cohort`
   - `audit-operations` — O01-O10 checks → `ecom-inventory`
   - `audit-pricing` — PR01-PR12 checks → `ecom-pricing`
   - `audit-growth` — CV01-CV12 checks → `ecom-conversion`, `ecom-experiment`
4. **Score** — aggregate per-category scores with weights (see `ecom-analytics/references/scoring-system.md`)
5. **Report** — generate AUDIT-REPORT.md, ACTION-PLAN.md, QUICK-WINS.md

## Data Collection

Request these files from the user:

| File | Required | Description |
|------|----------|-------------|
| Orders CSV | Yes | Order-level or line-item-level transaction data |
| Products CSV | Optional | Product catalog with prices, categories, costs |
| Inventory CSV | Optional | Current stock levels per SKU |
| Sessions/GA4 | Optional | Traffic and funnel data for CVR analysis |

## Scoring

See `ecom-analytics/references/scoring-system.md` for category weights, severity multipliers, and A-F grading.

## Output Files

- **AUDIT-REPORT.md** — Executive summary + detailed findings per category
- **ACTION-PLAN.md** — Prioritized actions grouped by severity
- **QUICK-WINS.md** — High-severity, low-effort fixes (< 15 min)

## Priority Definitions

| Priority | Criteria | Timeline |
|----------|----------|----------|
| Critical | Revenue/data loss risk | Fix immediately |
| High | Significant performance drag | This week |
| Medium | Optimization opportunity | This month |
| Low | Best practice, minor impact | Backlog |

## Quick Wins Criteria

```
IF severity IN ("Critical", "High")
AND estimated_fix_time <= 15 minutes
THEN flag as Quick Win
SORT BY (severity_multiplier * estimated_revenue_impact) DESC
LIMIT 10
```

## Python Backend

```bash
cd ecom-analytics
python cli.py audit orders.csv --products products.csv --inventory inventory.csv --output ./reports/
```
