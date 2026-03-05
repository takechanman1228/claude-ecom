# Experiment Design Guide

<!-- Updated: 2026-03-04 -->

## Power Calculation

### Sample Size for Two-Proportion Test (CVR)

```
n = (Z_{α/2} + Z_β)² × 2 × p × (1-p) / δ²
```

Where:
- `Z_{α/2}` = 1.96 for α = 0.05 (two-sided)
- `Z_β` = 0.84 for power = 80%
- `p` = baseline conversion rate
- `δ` = minimum detectable effect (absolute)
- `n` = required sample size per arm

### Common Scenarios

| Baseline CVR | MDE | Power | n per arm | Total |
|-------------|-----|-------|-----------|-------|
| 2.0% | +0.5pt | 80% | 3,200 | 6,400 |
| 2.0% | +1.0pt | 80% | 860 | 1,720 |
| 3.0% | +0.5pt | 80% | 4,500 | 9,000 |
| 3.0% | +1.0pt | 80% | 1,200 | 2,400 |
| 5.0% | +1.0pt | 80% | 1,900 | 3,800 |

### Test Duration

```
duration_days = ceil(2 × n_per_arm / daily_traffic)
```

| Daily Traffic | MDE 0.5pt (2% base) | MDE 1.0pt (2% base) |
|---------------|---------------------|---------------------|
| 1,000 | 6-7 days | 2 days |
| 5,000 | 2 days | 1 day |
| 10,000 | 1 day | 1 day |
| 500 | 13 days | 4 days |
| 200 | 32 days | 9 days |

**Minimum test duration: 7 days** (to capture weekly patterns, regardless of traffic).

### MDE Calculation (Given Fixed Duration)

```
n_per_arm = daily_traffic × test_days / 2
MDE = (Z_{α/2} + Z_β) × √(2 × p × (1-p) / n_per_arm)
```

## ICE / RICE Prioritisation

### ICE Scoring

```
ICE = Impact × Confidence × Ease
```

| Factor | Scale | Description |
|--------|-------|-------------|
| Impact | 1-10 | Expected revenue uplift (10 = transformative) |
| Confidence | 1-10 | Evidence strength (10 = proven in similar context) |
| Ease | 1-10 | Implementation simplicity (10 = 5-minute change) |

### RICE Scoring

```
RICE = (Reach × Impact × Confidence) / Effort
```

| Factor | Scale | Description |
|--------|-------|-------------|
| Reach | 0-1.0 | Fraction of users affected |
| Impact | 1-10 | Expected per-user revenue uplift |
| Confidence | 1-10 | Evidence strength |
| Effort | 1-10 | Implementation complexity (10 = hardest) |

### Priority Thresholds

| ICE Score | Priority |
|-----------|----------|
| > 500 | Run immediately |
| 200-500 | Next sprint |
| 100-200 | Backlog |
| < 100 | Deprioritise |

## Statistical Validation

### Two-Proportion Z-Test (CVR)

```python
from scipy.stats import norm
z = (p1 - p2) / sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
p_value = 2 * (1 - norm.cdf(abs(z)))
```

### T-Test (AOV)

```python
from scipy.stats import ttest_ind
t_stat, p_value = ttest_ind(control_aov, treatment_aov)
```

### Decision Rules

| p-value | Practical significance | Decision |
|---------|----------------------|----------|
| < 0.05 | Yes (MDE met) | Ship treatment |
| < 0.05 | No (effect too small) | Keep control (not worth complexity) |
| ≥ 0.05 | — | Inconclusive; extend or redesign |

## Common EC Test Ideas

| Test | Metric | Typical MDE | Effort |
|------|--------|-------------|--------|
| Free-shipping threshold change | AOV | +5-15% | Low |
| Cart abandonment email | CVR | +0.3-1.0pt | Low |
| Product page layout | Add-to-cart rate | +1-3pt | Medium |
| Checkout flow simplification | Completion rate | +2-5pt | Medium |
| Pricing change | Revenue/unit | ±5-20% | Low |
| Upsell widget | AOV | +3-8% | Medium |
| Search ranking algorithm | Search CVR | +1-5pt | High |

## Guardrail Metrics

Always monitor these during tests:
- Overall revenue (no significant decline)
- Return rate (not increasing)
- Customer satisfaction (if measured)
- Page load time (no degradation)
