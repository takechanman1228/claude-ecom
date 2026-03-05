---
name: ecom-pricing
description: >
  Price and discount analysis. Evaluates 12 checks (PR01-PR12) covering
  discount dependency, price elasticity, margin analysis, free-shipping
  threshold optimisation, and subscription pricing. Triggers on: "pricing analysis",
  "discount analysis", "price optimization", "profit margin", "margin analysis".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# ecom-pricing — Price & Discount Analysis

## Process

1. **Load orders CSV** (amount required; discount, cost optional)
2. **Read references** — Load from `ecom-analytics/references/`: `pricing-analysis.md`, `benchmarks.md`, `scoring-system.md`
3. **Evaluate PR01-PR12** as PASS / WARNING / FAIL
4. **Calculate category score** (weight: 10%)
5. **Output** — discount dependency report, elasticity estimates, margin scenarios

## What to Analyse

### Discount Dependency (PR01-PR04)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| PR01 Avg discount rate | High | < 15% | 15-25% | > 25% |
| PR02 Discounted order ratio | High | < 40% | 40-60% | > 60% |
| PR03 Discount depth trend | Critical | MoM increase < 1pt | 1-2pt | > 2pt |
| PR04 Discount vs non-discount LTV | High | Discount ≥ 70% normal | 50-70% | < 50% |

### ROI & Elasticity (PR05-PR08)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| PR05 Coupon code ROI | Medium | All > 1.0 | Some < 1.0 | Majority < 1.0 |
| PR06 Price change sensitivity | Medium | Elasticity measured | — | No data |
| PR07 Category margin variance | Medium | No negative margin | — | Negative margin exists |
| PR08 Free-shipping threshold | High | AOV bump > 10% near threshold | 5-10% | < 5% |

### Profitability (PR09-PR12)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| PR09 Sale period margin | High | Gross margin > 15% | 10-15% | < 10% |
| PR10 Competitor price gap | Medium | Within ±20% | ±20-30% | > ±30% |
| PR11 Price-tier CVR | Medium | All tiers > 0.5% | — | Any tier < 0.5% |
| PR12 Subscription discount | Medium | < 20% | 20-30% | > 30% |

## Key Analyses

- **Discount dependency** — Rate, trend, and order ratio
- **Price elasticity** — Simple log-log regression per product
- **Margin analysis** — Overall and by-category gross margin
- **Free-shipping threshold** — Optimal threshold suggestion based on AOV distribution

## Python Backend

```python
from ecom_analytics.pricing import discount_dependency, price_elasticity_simple, margin_analysis, free_shipping_threshold
```
