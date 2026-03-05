---
name: ecom-revenue
description: >
  Revenue decomposition and trend analysis. Breaks down Revenue = Traffic x CVR
  x AOV and identifies growth drivers and bottlenecks. Covers 15 checks (R01-R15)
  including MoM trends, seasonality, customer concentration, and return rates.
  Triggers on: "revenue analysis", "revenue breakdown", "revenue trends",
  "revenue decomposition".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# ecom-revenue — Revenue Decomposition & Diagnosis

## Process

1. **Load orders CSV** via `ecom_analytics.loader`
2. **Read references** — Load from `ecom-analytics/references/`: `revenue-decomposition.md`, `benchmarks.md`, `scoring-system.md`
3. **Evaluate R01-R15** as PASS / WARNING / FAIL
4. **Calculate category score** (weight: 25%)
5. **Generate findings** with revenue impact estimates

## What to Analyse

### Revenue Trend (R01-R04)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| R01 MoM revenue growth | High | > 0% | -5% to 0% | < -5% |
| R02 Seasonality detection | Medium | Positive trend after adjustment | — | Declining trend |
| R03 AOV trend | High | Decline < 5%/mo | 5-10%/mo | > 10%/mo |
| R04 Order count trend | High | MoM > -5% | -5% to -10% | < -10% |

### Revenue Structure (R05-R10)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| R05 Repeat revenue share | Critical | > 30% | 20-30% | < 20% |
| R06 Day/hour patterns | Low | Data provided | — | — |
| R07 Top-10% customer share | Medium | < 60% | 60-80% | > 80% |
| R08 Avg discount rate trend | High | < 15% | 15-25% | > 25% |
| R09 Geographic concentration | Medium | Top region < 70% | 70-85% | > 85% |
| R10 Category mix change | Medium | No sudden shifts | — | Sudden shift |

### Revenue Quality (R11-R15)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| R11 Return rate | High | < 5% | 5-10% | > 10% |
| R12 Gross margin trend | Critical | Decline < 2pt/Q | 2-5pt/Q | > 5pt/Q |
| R13 Daily revenue CV | Medium | < 0.5 | 0.5-0.8 | > 0.8 |
| R14 Large-order dependency | Medium | Top order < 5% rev | 5-10% | > 10% |
| R15 Forecast vs actual | Low | Error < 15% | 15-25% | > 25% |

## Key Analyses

- **Revenue tree decomposition** — Sessions x CVR x AOV waterfall
- **Seasonality detection** — Month-over-month patterns
- **Anomaly detection** — IQR-based outlier identification
- **Waterfall analysis** — Period-over-period change attribution

## Python Backend

```python
from ecom_analytics.decomposition import decompose_revenue, detect_anomalies, waterfall_analysis
from ecom_analytics.metrics import compute_revenue_kpis
```
