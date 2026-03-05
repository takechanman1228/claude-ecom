---
name: ecom-inventory
description: >
  Inventory and stockout analysis. Evaluates 10 checks (O01-O10) covering
  turnover rate, stockout rate, opportunity cost, overstock, deadstock, and
  safety stock adequacy. Triggers on: "inventory analysis", "stockout",
  "inventory turnover", "reorder optimization", "overstock".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# ecom-inventory — Inventory & Stockout Analysis

## Process

1. **Load data** — inventory CSV + orders CSV (for velocity)
2. **Read references** — Load from `ecom-analytics/references/`: `inventory-analysis.md`, `benchmarks.md`, `scoring-system.md`
3. **Evaluate O01-O10** as PASS / WARNING / FAIL
4. **Calculate category score** (weight: 10%)
5. **Output** — stockout losses, overstock list, safety stock recommendations

## What to Analyse

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| O01 Overall turnover rate | High | > 6x/year | 4-6x | < 4x |
| O02 A-rank days of stock | Critical | 14-45 days | 7-14 or 45-60 | < 7 or > 60 |
| O03 Stockout SKU rate | Critical | < 5% | 5-10% | > 10% |
| O04 Stockout opportunity cost | Critical | < 3% of monthly rev | 3-5% | > 5% |
| O05 Overstock (>90d) value | High | < 20% of inv value | 20-35% | > 35% |
| O06 Deadstock (>180d) rate | High | < 10% SKUs | 10-20% | > 20% |
| O07 Safety stock adequacy | Medium | A-rank > 95% | 85-95% | < 85% |
| O08 Lead time accuracy | Medium | Error < 20% | 20-35% | > 35% |
| O09 Seasonal stockout | Medium | Peak month = 0 | 1-2 SKUs | 3+ SKUs |
| O10 Inventory cost ratio | Medium | < 25% of revenue | 25-40% | > 40% |

## Key Analyses

- **Stockout analysis** — Identify zero-stock SKUs, estimate lost revenue
- **Overstock analysis** — Flag slow-moving inventory, calculate carrying cost
- **Safety stock** — Z × σ × √(lead_time) per SKU
- **Turnover rate** — Annual sales qty / avg inventory per SKU

## Python Backend

```python
from ecom_analytics.inventory import stockout_analysis, overstock_analysis, safety_stock_calculation, inventory_turnover
```
