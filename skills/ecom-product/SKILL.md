---
name: ecom-product
description: >
  Product performance analysis. Evaluates 20 checks (P01-P20) covering ABC
  classification, cross-sell discovery, product lifecycle, category performance,
  return rates, and deadstock. Triggers on: "product analysis", "ABC analysis",
  "cross-sell", "product performance".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# ecom-product — Product Performance Analysis

## Process

1. **Load data** — orders CSV (line-item level) + products CSV
2. **Read references** — Load from `ecom-analytics/references/`: `product-analysis.md`, `benchmarks.md`, `scoring-system.md`
3. **Evaluate P01-P20** as PASS / WARNING / FAIL
4. **Calculate category score** (weight: 20%)
5. **Output** — product rankings, cross-sell matrix, lifecycle stages

## What to Analyse

### Product Concentration (P01-P05)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| P01 Top-20% revenue share | Medium | 60-80% | 80-90% | > 90% or < 50% |
| P02 C-rank inventory cost | High | < 15% of total | 15-25% | > 25% |
| P03 New product ramp speed | High | 50% target in 30d | 30-50% | < 30% |
| P04 Avg reviews per product | Medium | A-rank > 10 | 5-10 | < 5 |
| P05 Converting SKU rate | High | > 70% SKUs with sales | 50-70% | < 50% |

### Cross-Sell & Bundling (P06-P07)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| P06 Multi-item order rate | Medium | > 25% | 15-25% | < 15% |
| P07 Cross-sell pair lift | Medium | Pairs with lift > 2.0 | 1.5-2.0 | None > 1.5 |

### Cannibalisation & Lifecycle (P08-P10)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| P08 Category cannibalisation | High | No -30% drops | — | -30%+ drop on new launch |
| P09 Deadstock (180d+) | Critical | < 10% SKUs | 10-20% | > 20% |
| P10 Lifecycle stage distribution | Medium | Decline < 30% | 30-50% | > 50% |

### Quality & Returns (P11-P15)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| P11 High-return products | High | All < 10% | Some 10-15% | Any > 15% |
| P12 Seasonal timing | Medium | Pre-season stock OK | — | Late stocking |
| P13 Content richness | Medium | 3+ images, 200+ chars | — | Missing content |
| P14 Category margin | High | All categories > 0 | — | Negative margin |
| P15 A-rank stockout frequency | Critical | 0 stockouts | 1-2 events | 3+ events |

### Growth & Repeat (P16-P20)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| P16 Bundle effectiveness | Medium | Bundle AOV > 1.2x | 1.0-1.2x | < 1.0x |
| P17 Rating-sales correlation | Low | Data provided | — | — |
| P18 New product frequency | Medium | 1+/month | 1/quarter | < 1/quarter |
| P19 Price tier distribution | Medium | 3+ tiers | 2 tiers | 1 tier |
| P20 Consumable repurchase rate | High | > 20% | 10-20% | < 10% |

## Key Analyses

- **ABC analysis** — Revenue-based A/B/C classification (80/15/5 split)
- **Cross-sell matrix** — Co-purchase pairs with lift scores
- **Product lifecycle** — Launch / Growth / Mature / Decline staging
- **Category performance** — Revenue share, margin, order count by category

## Python Backend

```python
from ecom_analytics.product import abc_analysis, cross_sell_matrix, product_lifecycle, category_performance
```
