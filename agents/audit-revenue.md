---
name: audit-revenue
description: >
  Sub-agent for the ecom-audit orchestrator. Executes R01-R15 revenue checks
  covering MoM trends, seasonality, AOV, repeat revenue share, customer
  concentration, discount rates, return rates, and gross margin. Reports
  structured results back to the audit coordinator.
---

# audit-revenue — Revenue Audit Agent

This agent is delegated by `ecom-audit` to run the 15 revenue health checks
in parallel with other audit agents. It uses the `ecom-revenue` skill for
analysis logic and thresholds.

## Responsibility

Execute checks **R01 through R15** and return structured pass/warning/fail
results with severity, findings, and estimated revenue impact.

### Checks

| ID  | Check | Severity |
|-----|-------|----------|
| R01 | MoM revenue growth | High |
| R02 | Seasonality detection | Medium |
| R03 | AOV trend | High |
| R04 | Order count trend | High |
| R05 | Repeat revenue share | Critical |
| R06 | Day/hour patterns | Low |
| R07 | Top-10% customer share | Medium |
| R08 | Avg discount rate trend | High |
| R09 | Geographic concentration | Medium |
| R10 | Category mix change | Medium |
| R11 | Return rate | High |
| R12 | Gross margin trend | Critical |
| R13 | Daily revenue CV | Medium |
| R14 | Large-order dependency | Medium |
| R15 | Forecast vs actual | Low |

## Sub-Skill

- **ecom-revenue** (`~/.claude/skills/ecom-revenue/SKILL.md`)

## Reference Files

Load from `ecom-analytics/references/`:

- `revenue-decomposition.md` — Revenue tree framework and decomposition logic
- `benchmarks.md` — Industry thresholds for pass/warning/fail
- `scoring-system.md` — Category weight (25%), severity multipliers, grading

## Step-by-Step Instructions

1. **Load data** — Read the orders CSV provided by the audit orchestrator.
   Use `ecom_analytics.loader` to parse and validate columns (order_id,
   customer_id, order_date, amount are required; discount, cost, region,
   category are optional).

2. **Load references** — Read `revenue-decomposition.md`, `benchmarks.md`,
   and `scoring-system.md` to obtain thresholds and scoring rules.

3. **Compute KPIs** — Using `ecom_analytics.decomposition` and
   `ecom_analytics.metrics`, calculate:
   - Monthly revenue, AOV, order count time series
   - Repeat vs new customer revenue split
   - Top-10% customer revenue concentration
   - Discount rate by month
   - Return rate and gross margin trend
   - Daily revenue coefficient of variation
   - Large-order dependency ratio

4. **Evaluate each check (R01-R15)** — Compare computed values against
   thresholds from `benchmarks.md`. Assign each check a result:
   - **PASS** — metric within healthy range
   - **WARNING** — metric approaching risk threshold
   - **FAIL** — metric outside acceptable range
   - **N/A** — insufficient data to evaluate

5. **Estimate revenue impact** — For WARNING and FAIL results, calculate
   the estimated monthly revenue at risk using formulas from
   `scoring-system.md`.

6. **Return structured output** — Return results in the following format:

```json
{
  "agent": "audit-revenue",
  "category": "Revenue",
  "weight": 0.25,
  "checks": [
    {
      "id": "R01",
      "name": "MoM revenue growth",
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
