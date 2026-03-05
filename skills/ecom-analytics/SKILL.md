---
name: ecom-analytics
version: 0.3.0
description: >
  EC-specialized data analytics and audit toolkit. Performs full ecommerce store
  audits covering revenue decomposition, conversion funnels, product performance,
  inventory health, cohort retention/LTV, and pricing analysis. Detects business
  model (D2C, marketplace, subscription) and provides industry benchmarks.
  Generates health score (0-100) with A-F grading and prioritized action plans.
  Triggers on: "ecommerce analysis", "ecommerce audit", "store audit",
  "store health", "revenue analysis", "cohort analysis", "product analysis",
  "inventory analysis", "pricing analysis", "AB test design", "site audit",
  "landing page audit", "CTA check", "page speed".
argument-hint: "audit | revenue | cohort | product | inventory | pricing | experiment | quickwins | site-audit"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# ecom-analytics — EC Data Analytics Orchestrator

Comprehensive ecommerce data analysis and audit system. Routes commands to
specialized sub-skills and aggregates results into unified health scores and
action plans.

## Quick Reference

| Command | What it does |
|---------|-------------|
| /ecom-analytics audit | Full 6-category audit with parallel sub-skill delegation |
| /ecom-analytics revenue | Revenue decomposition (Revenue = Traffic x CVR x AOV) |
| /ecom-analytics cohort | Cohort retention, LTV estimation, RFM segmentation |
| /ecom-analytics product | ABC analysis, cross-sell discovery, lifecycle diagnosis |
| /ecom-analytics inventory | Stockout / overstock analysis, safety stock calculation |
| /ecom-analytics pricing | Discount dependency, price elasticity, margin analysis |
| /ecom-analytics experiment | A/B test design, power calculation, ICE/RICE scoring |
| /ecom-analytics quickwins | Extract top quick wins from audit results |
| /ecom-analytics site-audit | Site / landing page quality audit (SA01-SA15) |
| /ecom-analytics shopify setup | Configure Shopify Admin API credentials |
| /ecom-analytics shopify sync | Sync data from Shopify via Bulk Operations |

## Orchestration Logic

1. **Collect data** — request orders CSV (required), products CSV, inventory CSV
2. **Detect business model** — D2C / Marketplace / Subscription / O2O
3. **Route** — delegate to appropriate sub-skill or run full audit
4. **Score** — apply 7-category weighted scoring (99 checks total)
5. **Report** — generate AUDIT-REPORT.md, ACTION-PLAN.md, QUICK-WINS.md

## Business Model Detection

Detects D2C / Marketplace / Subscription / O2O from order data signals.
Full detection logic: delegate to `ecom-context`.

## Quality Gates

- Never assume data that is not in the CSV
- Always validate CSV schema before analysis
- Report confidence level for each estimate
- Flag checks as N/A when required data is missing (do not penalise score)

## Reference Files

Load these on-demand as needed — do NOT load all at startup.

> **Reference path convention:** All sub-skills resolve references from
> `ecom-analytics/references/`. When installed via `install.sh`, this maps
> to `~/.claude/skills/ecom-analytics/references/`.

Path resolution: references are at `ecom-analytics/references/`.

- `scoring-system.md` — Weighted scoring algorithm, severity multipliers, grading
- `benchmarks.md` — Industry benchmarks by EC vertical
- `data-formats.md` — Supported CSV formats, column mappings, canonical analytics schema
- `revenue-decomposition.md` — R01-R15 revenue checks with implementation pseudocode
- `conversion-funnel.md` — CV01-CV12 conversion checks with implementation pseudocode
- `product-analysis.md` — P01-P20 product checks with implementation pseudocode
- `inventory-analysis.md` — O01-O10 inventory checks with implementation pseudocode
- `cohort-analysis.md` — C01-C15 cohort/retention checks with implementation pseudocode
- `pricing-analysis.md` — PR01-PR12 pricing checks with implementation pseudocode
- `site-audit-checks.md` — SA01-SA15 site quality checks
- `experiment-design.md` — A/B test design guide
- `finding-clusters.md` — 7-cluster finding themes for 84-check audit
- `impact-formulas.md` — Revenue impact formulas with worked examples
- `recommended-actions.md` — Prioritized action plans with vertical strategy playbooks
- `vertical-benchmarks.md` — Vertical-specific KPI thresholds, seasonal calendars, strategy playbooks
- `executive-narratives.md` — Grade A-F narrative templates with placeholders
- `check-implementation-summary.md` — Quick reference for 84 check implementations

## Scoring Methodology

### EC Health Score (0-100)

```
Category Score = Sum(result * severity_mult) / Sum(severity_mult) * 100
Overall Score  = Sum(category_score * category_weight)
```

### Category Weights (total = 100%)

| Category | Weight | Checks |
|----------|--------|--------|
| Revenue Structure | 25% | R01-R15 |
| Conversion | 20% | CV01-CV12 |
| Product | 20% | P01-P20 |
| Inventory | 10% | O01-O10 |
| Retention/LTV | 15% | C01-C15 |
| Pricing | 10% | PR01-PR12 |
| Site Quality | 10% | SA01-SA15 |

> Weights sum to 110% — `aggregate_score()` renormalizes to only categories present.

### Severity Multipliers

| Severity | Multiplier |
|----------|-----------|
| Critical | 5.0x |
| High | 3.0x |
| Medium | 1.5x |
| Low | 0.5x |

### Grading

| Grade | Score | Action |
|-------|-------|--------|
| A | 90-100 | Minor optimizations only |
| B | 75-89 | Some improvement opportunities |
| C | 60-74 | Notable issues need attention |
| D | 40-59 | Significant problems present |
| F | <40 | Urgent intervention required |

## Sub-Skills

1. `ecom-context` — Business model detection and benchmarks
2. `ecom-audit` — Full parallel audit orchestration
3. `ecom-revenue` — Revenue decomposition (R01-R15)
4. `ecom-conversion` — CVR funnel analysis (CV01-CV12)
5. `ecom-product` — Product performance (P01-P20)
6. `ecom-inventory` — Inventory health (O01-O10)
7. `ecom-cohort` — Cohort retention / LTV (C01-C15)
8. `ecom-pricing` — Price / discount analysis (PR01-PR12)
9. `ecom-experiment` — A/B test design
10. `ecom-quickwins` — Quick win extraction
11. `ecom-shopify-import` — Shopify Admin API data import
12. `ecom-site-audit` — Site / landing page quality audit (SA01-SA15)

## Python Toolkit

The `ecom_analytics` Python package provides computational backends:

```bash
cd ecom-analytics
python cli.py audit orders.csv --products products.csv --inventory inventory.csv
```

Modules: `loader`, `metrics`, `decomposition`, `cohort`, `product`, `inventory`,
`pricing`, `scoring`, `report`.
