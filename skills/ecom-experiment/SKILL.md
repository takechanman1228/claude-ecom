---
name: ecom-experiment
description: >
  A/B test design and experiment planning. Provides power calculation, sample
  size estimation, test duration, MDE computation, and ICE/RICE prioritization
  of improvement initiatives. Triggers on: "AB test", "experiment design",
  "test design", "statistical power", "sample size", "power calculation".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# ecom-experiment — A/B Test Design

## Process

1. **Gather inputs** — current CVR/AOV, daily traffic, list of initiatives
2. **Read references** — Load from `ecom-analytics/references/`: `experiment-design.md`, `benchmarks.md`
3. **Calculate** — power, sample size, test duration, MDE
4. **Prioritise** — ICE/RICE scoring for each initiative
5. **Output** — test design document + prioritized initiative table

## Capabilities

### Power Calculation

Given current CVR, desired minimum detectable effect (MDE), significance level
(alpha), and power (1-beta), compute required sample size per variant:

```
n = (Z_alpha/2 + Z_beta)^2 * 2 * p * (1-p) / delta^2
```

### Test Duration Estimation

```
duration_days = ceil(2 * n / daily_traffic)
```

### MDE Calculation

Given a fixed test duration and daily traffic, compute the minimum effect size
detectable:

```
n_per_arm = daily_traffic * days / 2
MDE = (Z_alpha/2 + Z_beta) * sqrt(2 * p * (1-p) / n_per_arm)
```

### ICE / RICE Scoring

| Factor | Description | Scale |
|--------|-------------|-------|
| Impact | Estimated revenue uplift | 1-10 |
| Confidence | Certainty of impact estimate | 1-10 |
| Ease | Implementation simplicity | 1-10 |
| Reach | % of users affected (RICE only) | 0-1.0 |

```
ICE = Impact * Confidence * Ease
RICE = (Reach * Impact * Confidence) / Ease
```

### Result Validation

After a test completes, validate statistical significance:
- Two-proportion z-test for CVR differences
- t-test for AOV differences
- Report p-value, confidence interval, and practical significance

## Output

- Test design table: initiative, metric, MDE, sample size, duration
- ICE/RICE priority ranking
- Go/no-go recommendation based on available traffic
- Post-test significance check template

## Python Backend

```python
from scipy.stats import norm
# Power calculation available in ecom_analytics utilities
```
