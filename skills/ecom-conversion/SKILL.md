---
name: ecom-conversion
description: >
  Conversion funnel analysis. Evaluates 12 checks (CV01-CV12) covering overall
  CVR, mobile vs desktop, cart abandonment, channel-level conversion, and funnel
  step drop-off. Identifies improvement opportunities with estimated revenue
  impact. Triggers on: "CVR analysis", "conversion rate", "funnel analysis",
  "drop-off analysis", "conversion analysis".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# ecom-conversion — CVR Funnel Analysis

## Process

1. **Load data** — orders CSV (required), sessions/GA4 data (optional)
2. **Read references** — Load from `ecom-analytics/references/`: `conversion-funnel.md`, `benchmarks.md`, `scoring-system.md`
3. **Evaluate CV01-CV12** as PASS / WARNING / FAIL
4. **Calculate category score** (weight: 20%)
5. **Output** — funnel visualization, CVR improvement opportunities, estimated impact

## What to Analyse

### Overall CVR (CV01-CV06)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| CV01 Overall CVR level | Critical | Within benchmark ±1σ | — | Outside benchmark |
| CV02 Mobile vs Desktop gap | High | Ratio < 2x | 2-3x | > 3x |
| CV03 Cart abandonment rate | Critical | < 75% | 75-85% | > 85% |
| CV04 Cart-to-purchase rate | High | > 40% | 25-40% | < 25% |
| CV05 New visitor CVR | High | > 1.0% | 0.5-1.0% | < 0.5% |
| CV06 Returning visitor CVR | Medium | > 3.0% | 1.5-3.0% | < 1.5% |

### Channel & Page CVR (CV07-CV10)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| CV07 Channel-level CVR | Medium | All > 0.5% | Some < 0.5% | Multiple < 0.5% |
| CV08 Landing page CVR | High | Top pages > 2% | 1-2% | < 1% |
| CV09 Search-to-product rate | Medium | > 30% | 15-30% | < 15% |
| CV10 Product-to-cart rate | High | > 8% | 4-8% | < 4% |

### Funnel Efficiency (CV11-CV12)

| Check | Severity | Pass | Warning | Fail |
|-------|----------|------|---------|------|
| CV11 Checkout step drop-off | Critical | Each step < 20% | 20-30% | > 30% |
| CV12 CVR time-series trend | High | MoM decline < 0.3pt | 0.3-0.5pt | > 0.5pt |

## Notes

- When session/GA4 data is unavailable, calculate proxy CVR from order frequency
- Mark session-dependent checks as N/A (do not penalise score)
- Estimate revenue impact of CVR improvement: +1pt CVR × sessions × AOV

## Python Backend

CVR checks rely primarily on aggregated order data. If session data is
available, use it for richer funnel analysis.

```python
from ecom_analytics.metrics import compute_revenue_kpis
```
