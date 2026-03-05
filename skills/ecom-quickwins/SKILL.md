---
name: ecom-quickwins
description: >
  Quick Win extraction from audit results. Identifies high-severity, low-effort
  improvements executable in under 15 minutes. Sorts by severity multiplier
  times estimated revenue impact. Triggers on: "quick wins", "easy fixes",
  "low hanging fruit".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# ecom-quickwins — Quick Win Extraction

## Process

1. **Input** — check results from all sub-skills (PASS/WARNING/FAIL per check)
2. **Filter** — severity ∈ {Critical, High} AND estimated_fix_time ≤ 15 min
3. **Score** — severity_multiplier × estimated_revenue_impact
4. **Sort** — descending by score
5. **Output** — QUICK-WINS.md with top 10 items + execution steps

## Quick Win Criteria

```
IF severity IN ("Critical", "High")
AND estimated_fix_time <= 15 minutes
THEN flag as Quick Win
SORT BY (severity_multiplier * estimated_revenue_impact) DESC
LIMIT 10
```

## Common Quick Win Patterns

| Pattern | Source | Typical Impact | Time |
|---------|--------|---------------|------|
| A-rank stockout → emergency reorder | O03 | Revenue recovery | 5 min |
| Cart abandonment email setup | CV03 | CVR +0.5pt | 10 min |
| Free-shipping threshold display | PR08 | AOV +5% | 10 min |
| Deadstock clearance sale | P09 | Carrying cost reduction | 15 min |
| Repeat customer coupon | C01 | F2 rate +5pt | 10 min |
| Remove underperforming coupons | PR05 | Margin improvement | 5 min |
| Update top product descriptions | P13 | CVR micro-improvement | 15 min |
| Fix broken category pages | CV08 | CVR recovery | 10 min |

## Output Format

QUICK-WINS.md includes:
1. Summary table (severity, action, impact, time, source check)
2. Step-by-step execution instructions for each quick win
3. Total estimated monthly revenue impact

## Python Backend

```python
from ecom_analytics.scoring import score_checks, estimate_revenue_impact
from ecom_analytics.report import generate_quick_wins
```
