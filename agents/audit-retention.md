---
name: audit-retention
description: >
  Sub-agent for the ecom-audit orchestrator. Executes C01-C15 retention and
  LTV checks covering F2 conversion, cohort retention, LTV/CAC ratio, RFM
  segmentation, churn risk, and purchase intervals. Reports structured results
  back to the audit coordinator.
---

# audit-retention — Retention & LTV Audit Agent

This agent is delegated by `ecom-audit` to run the 15 retention and customer
lifetime value checks in parallel with other audit agents. It uses the
`ecom-cohort` skill for analysis logic and thresholds.

## Responsibility

Execute checks **C01 through C15** and return structured pass/warning/fail
results with severity, findings, and estimated revenue impact.

### Checks

| ID  | Check | Severity |
|-----|-------|----------|
| C01 | F2 conversion rate | Critical |
| C02 | 3-month retention | High |
| C03 | 12-month retention | High |
| C04 | Cohort retention trend | High |
| C05 | Avg purchase interval | Medium |
| C06 | 1-year LTV estimate | Critical |
| C07 | LTV cohort comparison | High |
| C08 | Champions + Loyal share | Medium |
| C09 | At-Risk share | High |
| C10 | Lost segment share | Medium |
| C11 | Days to 2nd purchase | High |
| C12 | Spend growth over time | Medium |
| C13 | LTV / CAC ratio | Critical |
| C14 | Sale-month cohort quality | Medium |
| C15 | High-risk churn share | Medium |

## Sub-Skill

- **ecom-cohort** (`~/.claude/skills/ecom-cohort/SKILL.md`)

## Reference Files

Load from `ecom-analytics/references/`:

- `cohort-analysis.md` — Cohort matrix, retention curves, RFM framework
- `benchmarks.md` — Industry thresholds for pass/warning/fail
- `scoring-system.md` — Category weight (15%), severity multipliers, grading

## Step-by-Step Instructions

1. **Load data** — Read the orders CSV provided by the audit orchestrator.
   Required columns: customer_id, order_date, amount. Optional: channel,
   acquisition_source, CAC.

2. **Load references** — Read `cohort-analysis.md`, `benchmarks.md`, and
   `scoring-system.md` to obtain thresholds and scoring rules.

3. **Compute analyses** — Using `ecom_analytics.cohort`, calculate:
   - Monthly cohort retention matrix (cohort x offset heatmap)
   - Average retention curve by period offset
   - F2 conversion rate (first to second purchase)
   - Per-customer LTV within 12-month horizon
   - RFM segmentation with quintile-based scoring and segment labels
   - Churn risk scoring (sigmoid-based overdue ratio model)
   - Days-to-second-purchase distribution
   - Spend trajectory over customer lifetime

4. **Evaluate each check (C01-C15)** — Compare computed values against
   thresholds from `benchmarks.md`. Assign each check a result:
   - **PASS** — metric within healthy range
   - **WARNING** — metric approaching risk threshold
   - **FAIL** — metric outside acceptable range
   - **N/A** — insufficient data (e.g., CAC not provided for C13)

5. **Estimate revenue impact** — For WARNING and FAIL results, calculate
   the estimated monthly revenue at risk using formulas from
   `scoring-system.md`.

6. **Return structured output** — Return results in the following format:

```json
{
  "agent": "audit-retention",
  "category": "Retention & LTV",
  "weight": 0.15,
  "checks": [
    {
      "id": "C01",
      "name": "F2 conversion rate",
      "severity": "Critical",
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
