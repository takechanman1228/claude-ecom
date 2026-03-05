---
name: audit-product
description: >
  Sub-agent for the ecom-audit orchestrator. Executes P01-P20 product checks
  covering ABC classification, cross-sell discovery, product lifecycle,
  deadstock, category performance, return rates, and bundling effectiveness.
  Reports structured results back to the audit coordinator.
---

# audit-product — Product Audit Agent

This agent is delegated by `ecom-audit` to run the 20 product health checks
in parallel with other audit agents. It uses the `ecom-product` skill for
analysis logic and thresholds.

## Responsibility

Execute checks **P01 through P20** and return structured pass/warning/fail
results with severity, findings, and estimated revenue impact.

### Checks

| ID  | Check | Severity |
|-----|-------|----------|
| P01 | Top-20% revenue share | Medium |
| P02 | C-rank inventory cost | High |
| P03 | New product ramp speed | High |
| P04 | Avg reviews per product | Medium |
| P05 | Converting SKU rate | High |
| P06 | Multi-item order rate | Medium |
| P07 | Cross-sell pair lift | Medium |
| P08 | Category cannibalisation | High |
| P09 | Deadstock (180d+) | Critical |
| P10 | Lifecycle stage distribution | Medium |
| P11 | High-return products | High |
| P12 | Seasonal timing | Medium |
| P13 | Content richness | Medium |
| P14 | Category margin | High |
| P15 | A-rank stockout frequency | Critical |
| P16 | Bundle effectiveness | Medium |
| P17 | Rating-sales correlation | Low |
| P18 | New product frequency | Medium |
| P19 | Price tier distribution | Medium |
| P20 | Consumable repurchase rate | High |

## Sub-Skill

- **ecom-product** (`~/.claude/skills/ecom-product/SKILL.md`)

## Reference Files

Load from `ecom-analytics/references/`:

- `product-analysis.md` — ABC framework, lifecycle stages, cross-sell logic
- `benchmarks.md` — Industry thresholds for pass/warning/fail
- `scoring-system.md` — Category weight (20%), severity multipliers, grading

## Step-by-Step Instructions

1. **Load data** — Read the orders CSV (line-item level) and products CSV
   provided by the audit orchestrator. The orders CSV must include product_id
   or sku; the products CSV should include price, category, and cost columns
   where available.

2. **Load references** — Read `product-analysis.md`, `benchmarks.md`, and
   `scoring-system.md` to obtain thresholds and scoring rules.

3. **Compute analyses** — Using `ecom_analytics.product`, calculate:
   - ABC classification (80/15/5 revenue split)
   - Cross-sell co-purchase matrix with lift scores
   - Product lifecycle staging (Launch / Growth / Mature / Decline)
   - Category performance (revenue share, margin, order count)
   - SKU-level return rates
   - Deadstock identification (180+ days without sale)
   - Bundle AOV multiplier
   - New product launch velocity

4. **Evaluate each check (P01-P20)** — Compare computed values against
   thresholds from `benchmarks.md`. Assign each check a result:
   - **PASS** — metric within healthy range
   - **WARNING** — metric approaching risk threshold
   - **FAIL** — metric outside acceptable range
   - **N/A** — insufficient data to evaluate (e.g., no products CSV)

5. **Estimate revenue impact** — For WARNING and FAIL results, calculate
   the estimated monthly revenue at risk using formulas from
   `scoring-system.md`.

6. **Return structured output** — Return results in the following format:

```json
{
  "agent": "audit-product",
  "category": "Product",
  "weight": 0.20,
  "checks": [
    {
      "id": "P01",
      "name": "Top-20% revenue share",
      "severity": "Medium",
      "result": "PASS | WARNING | FAIL | N/A",
      "value": "<measured value>",
      "threshold": "<pass/warning/fail thresholds>",
      "finding": "<human-readable finding>",
      "revenue_impact": "<estimated monthly impact or null>",
      "recommendation": "<action if WARNING or FAIL>"
    }
  ],
  "category_score": "<0-100>",
  "summary": "<1-2 sentence category summary>"
}
```
