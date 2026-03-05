---
name: audit-pricing
description: >
  Sub-agent for the ecom-audit orchestrator. Executes PR01-PR12 pricing checks
  covering discount dependency, price elasticity, margin analysis,
  free-shipping threshold, coupon ROI, and subscription pricing. Reports
  structured results back to the audit coordinator.
---

# audit-pricing — Pricing Audit Agent

This agent is delegated by `ecom-audit` to run the 12 pricing health checks
in parallel with other audit agents. It uses the `ecom-pricing` skill for
analysis logic and thresholds.

## Responsibility

Execute checks **PR01 through PR12** and return structured pass/warning/fail
results with severity, findings, and estimated revenue impact.

### Checks

| ID   | Check | Severity |
|------|-------|----------|
| PR01 | Avg discount rate | High |
| PR02 | Discounted order ratio | High |
| PR03 | Discount depth trend | Critical |
| PR04 | Discount vs non-discount LTV | High |
| PR05 | Coupon code ROI | Medium |
| PR06 | Price change sensitivity | Medium |
| PR07 | Category margin variance | Medium |
| PR08 | Free-shipping threshold | High |
| PR09 | Sale period margin | High |
| PR10 | Competitor price gap | Medium |
| PR11 | Price-tier CVR | Medium |
| PR12 | Subscription discount | Medium |

## Sub-Skill

- **ecom-pricing** (`~/.claude/skills/ecom-pricing/SKILL.md`)

## Reference Files

Load from `ecom-analytics/references/`:

- `pricing-analysis.md` — Discount dependency, elasticity, margin formulas
- `benchmarks.md` — Industry thresholds for pass/warning/fail
- `scoring-system.md` — Category weight (10%), severity multipliers, grading

## Step-by-Step Instructions

1. **Load data** — Read the orders CSV provided by the audit orchestrator.
   Required column: amount. Optional columns: discount, discount_code, cost,
   shipping_cost, category. Products CSV is helpful for cost-based margin
   analysis.

2. **Load references** — Read `pricing-analysis.md`, `benchmarks.md`, and
   `scoring-system.md` to obtain thresholds and scoring rules.

3. **Compute analyses** — Using `ecom_analytics.pricing`, calculate:
   - Discount dependency metrics (avg rate, discounted order ratio, trend)
   - Discount vs non-discount customer LTV comparison
   - Coupon code ROI (incremental revenue / discount cost)
   - Simple log-log price elasticity per product
   - Gross margin overall and by category
   - Free-shipping threshold optimization (AOV distribution analysis)
   - Sale-period margin impact

4. **Evaluate each check (PR01-PR12)** — Compare computed values against
   thresholds from `benchmarks.md`. Assign each check a result:
   - **PASS** — metric within healthy range
   - **WARNING** — metric approaching risk threshold
   - **FAIL** — metric outside acceptable range
   - **N/A** — insufficient data (e.g., no discount column)

5. **Estimate revenue impact** — For WARNING and FAIL results, calculate
   the estimated monthly revenue at risk. For discount dependency issues,
   estimate margin erosion. For free-shipping threshold, estimate AOV uplift
   potential.

6. **Return structured output** — Return results in the following format:

```json
{
  "agent": "audit-pricing",
  "category": "Pricing",
  "weight": 0.10,
  "checks": [
    {
      "id": "PR01",
      "name": "Avg discount rate",
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
