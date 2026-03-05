---
name: audit-operations
description: >
  Sub-agent for the ecom-audit orchestrator. Executes O01-O10 inventory and
  operations checks covering turnover rate, stockout rate, opportunity cost,
  overstock, deadstock, safety stock adequacy, and lead time accuracy. Reports
  structured results back to the audit coordinator.
---

# audit-operations — Inventory & Operations Audit Agent

This agent is delegated by `ecom-audit` to run the 10 inventory and operations
health checks in parallel with other audit agents. It uses the `ecom-inventory`
skill for analysis logic and thresholds.

## Responsibility

Execute checks **O01 through O10** and return structured pass/warning/fail
results with severity, findings, and estimated revenue impact.

### Checks

| ID  | Check | Severity |
|-----|-------|----------|
| O01 | Overall turnover rate | High |
| O02 | A-rank days of stock | Critical |
| O03 | Stockout SKU rate | Critical |
| O04 | Stockout opportunity cost | Critical |
| O05 | Overstock (>90d) value | High |
| O06 | Deadstock (>180d) rate | High |
| O07 | Safety stock adequacy | Medium |
| O08 | Lead time accuracy | Medium |
| O09 | Seasonal stockout | Medium |
| O10 | Inventory cost ratio | Medium |

## Sub-Skill

- **ecom-inventory** (`~/.claude/skills/ecom-inventory/SKILL.md`)

## Reference Files

Load from `ecom-analytics/references/`:

- `inventory-analysis.md` — Stockout, overstock, safety stock formulas
- `benchmarks.md` — Industry thresholds for pass/warning/fail
- `scoring-system.md` — Category weight (10%), severity multipliers, grading

## Step-by-Step Instructions

1. **Load data** — Read the inventory CSV and orders CSV provided by the
   audit orchestrator. The inventory CSV should include sku, quantity_on_hand,
   and optionally cost_per_unit and lead_time_days. The orders CSV provides
   sales velocity data.

2. **Load references** — Read `inventory-analysis.md`, `benchmarks.md`, and
   `scoring-system.md` to obtain thresholds and scoring rules.

3. **Compute analyses** — Using `ecom_analytics.inventory`, calculate:
   - Inventory turnover rate per SKU and overall (annual sales qty / avg inventory)
   - Stockout identification (zero-stock SKUs) with lost revenue estimate
   - Overstock analysis (>90 days of supply) with carrying cost
   - Deadstock flagging (>180 days without sale)
   - Safety stock levels: Z * sigma * sqrt(lead_time) per SKU
   - A-rank days-of-stock calculation
   - Inventory cost as percentage of revenue

4. **Evaluate each check (O01-O10)** — Compare computed values against
   thresholds from `benchmarks.md`. Assign each check a result:
   - **PASS** — metric within healthy range
   - **WARNING** — metric approaching risk threshold
   - **FAIL** — metric outside acceptable range
   - **N/A** — insufficient data (e.g., no inventory CSV provided)

5. **Estimate revenue impact** — For WARNING and FAIL results, calculate
   the estimated monthly revenue at risk. For stockouts, use lost-sale
   estimation from `scoring-system.md`. For overstock, use carrying cost
   percentage.

6. **Return structured output** — Return results in the following format:

```json
{
  "agent": "audit-operations",
  "category": "Operations & Inventory",
  "weight": 0.10,
  "checks": [
    {
      "id": "O01",
      "name": "Overall turnover rate",
      "severity": "High",
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
