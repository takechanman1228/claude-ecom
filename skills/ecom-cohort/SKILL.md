---
name: ecom-cohort
description: >
  Cohort retention, LTV estimation, and RFM segmentation. Evaluates 15 checks
  (C01-C15) covering F2 conversion, retention curves, LTV/CAC ratio, RFM
  distribution, and churn risk. Triggers on: "cohort analysis", "LTV",
  "retention", "customer analysis", "RFM", "customer lifetime value".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# ecom-cohort — Cohort, Retention & LTV Analysis

## Process

1. **Load orders CSV** (customer_id, order_date, amount required)
2. **Read references** — Load from `ecom-analytics/references/`: `cohort-analysis.md`, `benchmarks.md`, `scoring-system.md`
3. **Evaluate C01-C15** as PASS / WARNING / FAIL
4. **Calculate category score** (weight: 15%)
5. **Output** — cohort heatmap, retention curve, LTV estimate, RFM segments, churn risk

## What to Analyse

### F2 & Retention (C01-C04)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| C01 F2 conversion rate | Critical | > 25% | 15-25% | < 15% |
| C02 3-month retention | High | > 20% | 10-20% | < 10% |
| C03 12-month retention | High | > 10% | 5-10% | < 5% |
| C04 Cohort retention trend | High | Improving or stable | — | Declining |

### Purchase Behaviour (C05-C07)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| C05 Avg purchase interval | Medium | Within benchmark ±30% | — | Outside |
| C06 1-year LTV estimate | Critical | LTV > CAC x 3 | CAC x 2-3 | < CAC x 2 |
| C07 LTV cohort comparison | High | Recent ≥ 80% avg | 60-80% | < 60% |

### RFM & Segments (C08-C10)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| C08 Champions + Loyal share | Medium | > 20% | 10-20% | < 10% |
| C09 At-Risk share | High | < 25% | 25-35% | > 35% |
| C10 Lost segment share | Medium | < 30% | 30-45% | > 45% |

### Acquisition & Churn (C11-C15)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| C11 Days to 2nd purchase | High | < 60 days | 60-90 | > 90 |
| C12 Spend growth over time | Medium | Increasing | Flat | Decreasing |
| C13 LTV / CAC ratio | Critical | > 3.0 | 2.0-3.0 | < 2.0 |
| C14 Sale-month cohort quality | Medium | ≥ 70% of normal LTV | 50-70% | < 50% |
| C15 High-risk churn share | Medium | < 15% | 15-25% | > 25% |

## Key Analyses

- **Cohort retention matrix** — Monthly cohort × offset heatmap
- **Retention curve** — Average retention by period offset
- **LTV estimation** — Per-customer spend within horizon
- **RFM segmentation** — Quintile-based R/F/M scoring → segment labels
- **Churn risk scoring** — Sigmoid-based overdue ratio model

## Python Backend

```python
from ecom_analytics.cohort import build_cohort_matrix, compute_retention_curve, estimate_ltv, rfm_segmentation, churn_risk_score
```
