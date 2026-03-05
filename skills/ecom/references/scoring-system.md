# EC Health Scoring System

<!-- Updated: 2026-03-04 | v0.4 -->

## Weighted Scoring Algorithm

```
S_category = Σ(C_result × W_severity) / Σ(W_severity) × 100

S_total = Σ(S_category × W_category)
        = S_revenue × 0.25
        + S_conversion × 0.20
        + S_product × 0.20
        + S_inventory × 0.10
        + S_retention × 0.15
        + S_pricing × 0.10
```

Where:
- `C_result` = check score: PASS (1.0), WARNING (0.5), FAIL (0.0)
- `W_severity` = severity multiplier (see below)
- `W_category` = category weight (see below)

## Severity Multipliers

| Severity | Multiplier | Criteria |
|----------|-----------|----------|
| Critical | 5.0 | Immediate revenue or customer impact. Fix now |
| High | 3.0 | Significant performance drag. Fix within 7 days |
| Medium | 1.5 | Optimisation opportunity. Fix within 30 days |
| Low | 0.5 | Best practice. Minor impact. Backlog |

## Check Result Scoring

| Result | Points | Description |
|--------|--------|-------------|
| PASS | 1.0 | Meets or exceeds benchmark |
| WARNING | 0.5 | Partially meets benchmark — attention needed |
| FAIL | 0.0 | Below benchmark — action required |
| N/A | (excluded) | Insufficient data — not scored |

## Category Weights

| # | Category | Weight | Check Count | Check IDs |
|---|----------|--------|-------------|-----------|
| 1 | Revenue Structure | 25% | 15 | R01-R15 |
| 2 | Conversion | 20% | 12 | CV01-CV12 |
| 3 | Product | 20% | 20 | P01-P20 |
| 4 | Inventory | 10% | 10 | O01-O10 |
| 5 | Retention / LTV | 15% | 15 | C01-C15 |
| 6 | Pricing | 10% | 12 | PR01-PR12 |
| | **Total** | **100%** | **84** | |

### Weight Rationale

- **Revenue (25%):** The ultimate measure of store health — everything flows through revenue
- **Conversion (20%):** Directly actionable and high-leverage for growth
- **Product (20%):** Catalog health determines long-term sustainability
- **Retention (15%):** LTV and repeat purchases drive profitable growth
- **Inventory (10%):** Important but operational — limited in many EC datasets
- **Pricing (10%):** Strategic lever but requires careful change management

## Grading Thresholds

| Grade | Score Range | Label | Recommended Action |
|-------|-----------|-------|-------------------|
| A | 90-100 | Excellent | Minor optimizations. Focus on growth strategy |
| B | 75-89 | Good | Some improvement opportunities. Prioritize |
| C | 60-74 | Needs Work | Notable issues requiring attention |
| D | 40-59 | Poor | Significant problems. Urgent action needed |
| F | 0-39 | Critical | Multiple critical failures. Emergency response |

## Quick Win Identification

```
IF severity IN ("Critical", "High")
AND estimated_fix_time <= 15 minutes
THEN flag as Quick Win

SORT BY (severity_multiplier × estimated_revenue_impact) DESC
LIMIT 10
```

## Revenue Impact Estimation

| Severity | Default Impact Estimate (% of annual revenue) |
|----------|----------------------------------------------|
| Critical FAIL | ~3% of annual revenue per check |
| High FAIL | ~1.5% |
| Medium FAIL | ~0.5% |
| Low FAIL | ~0.1% |
| WARNING | 50% of FAIL estimate |

Confidence levels:
- **High:** Direct data-based calculation (stockout loss, discount cost)
- **Medium:** Benchmark-derived estimate (CVR improvement, retention lift)
- **Low:** Indirect estimate (brand effect, long-term LTV improvement)

## Example Calculation

```
Revenue checks: 5 PASS (H×3, M×2), 2 WARNING (H×1, M×1), 1 FAIL (C×1)
Weighted sum = (3×3 + 2×1.5) × 1.0 + (1×3 + 1×1.5) × 0.5 + (1×5) × 0.0
             = 12.0 + 2.25 + 0.0 = 14.25
Max possible = 3×3 + 2×1.5 + 1×3 + 1×1.5 + 1×5 = 21.5
Score = 14.25 / 21.5 × 100 = 66.3 → Grade C
```

## Executive Narrative Generation

After computing the overall score and grade, generate an executive narrative paragraph
using the templates in [`executive-narratives.md`](executive-narratives.md).

### Workflow

1. Compute `S_total` → map to grade (A/B/C/D/F)
2. Identify `top_category` (highest `S_category`) and `bottom_category` (lowest `S_category`)
3. Count `num_critical` (FAIL checks with severity ≥ High) and `num_warnings`
4. Identify activated finding clusters from [`finding-clusters.md`](finding-clusters.md) → `cluster_names`
5. Select `top_issue` from the highest-severity FAIL check in the worst cluster
6. Compute `total_impact` using formulas from [`impact-formulas.md`](impact-formulas.md)
7. Format the grade-appropriate template with `str.format(**data)`

### Placeholder Sources

| Placeholder | Source |
|-------------|--------|
| `{score}` | `S_total` (rounded integer) |
| `{grade}` | Grading thresholds table above |
| `{business_model}` | Business model detection |
| `{top_category}` | Max `S_category` name |
| `{bottom_category}` | Min `S_category` name |
| `{top_issue}` | Worst check in worst cluster (plain language) |
| `{cluster_names}` | Activated clusters, priority-ordered |
| `{num_critical}` | Count of Critical/High FAIL checks |
| `{num_warnings}` | Count of WARNING checks |
| `{total_impact}` | Annualized impact estimate |

See [`executive-narratives.md`](executive-narratives.md) for the full template library.
