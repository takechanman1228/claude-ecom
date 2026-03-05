---
name: ecom
version: 2.0.0
description: >
  Claude-powered ecommerce audit toolkit. Runs full store health audits covering
  revenue, conversion, product, inventory, retention, pricing, and site quality.
  Generates business reviews (MBR/QBR/ABR). Detects business model (D2C,
  marketplace, subscription) and provides industry benchmarks. Produces health
  score (0-100) with A-F grading, natural language insights, and prioritized action plans.
  Triggers on: "ecommerce audit", "store audit", "store health", "revenue analysis",
  "cohort analysis", "product analysis", "inventory analysis", "pricing analysis",
  "site audit", "business review", "MBR", "QBR".
argument-hint: "audit | review"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Write
---

# ecom -- EC Data Analytics Toolkit

Comprehensive ecommerce data analysis and audit system. The Python backend
computes KPIs and scores; **you** (Claude) interpret the numbers and write
the human-readable report.

## Quick Reference

| Command | What it does | Output |
|---------|-------------|--------|
| /ecom audit | Full 7-category audit with natural language report | AUDIT-REPORT.md |
| /ecom review | Generic business review (auto-detected cadence) | BUSINESS-REVIEW-REPORT.md |
| /ecom review mbr | Monthly Business Review (tactical/operational) | BUSINESS-REVIEW-MBR.md |
| /ecom review qbr | Quarterly Business Review (strategic + tactical) | BUSINESS-REVIEW-QBR.md |
| /ecom review abr | Annual Business Review (strategic/high-level) | BUSINESS-REVIEW-ABR.md |

---

## Audit Workflow

### Phase 1: Compute (Python)

Run the CLI to generate machine-readable results:

```bash
cd <project-root>  # where pyproject.toml lives
ecom audit <orders.csv> --products <products.csv> --inventory <inventory.csv> --output <output-dir>
# Or from Shopify:
ecom audit --source shopify --since 2024-01-01 --output <output-dir>
```

This produces `scores.json` in the output directory -- the structured data you will interpret.

### Phase 2: Interpret (You -- Claude)

This is where your value is. Raw numbers are meaningless without context.

1. **Read `scores.json`** from the output directory
2. **Load reference files on demand** (see Reference Files below)
3. **Write the report** following the Output Format below

---

## Reference Files

Load these on-demand as needed -- do NOT load all at startup.

> **Path:** `ecom/references/` (installed at `~/.claude/skills/ecom/references/`)

### For interpretation and narrative:
- `executive-narratives.md` -- Grade-specific narrative templates (A-F) with tone guidance and worked examples. **Always load this for the executive summary.**
- `finding-clusters.md` -- 7-cluster model (Purchase Funnel, Discount Dependency, Assortment Misfit, Inventory Distortion, Returns/Trust, Retention/LTV, Revenue Concentration). Activation rules, hypothesis templates, and example scenarios. **Load this to identify systemic themes.**
- `recommended-actions.md` -- Specific, actionable recommendations per check with implementation time, expected impact range, and sources. **Load for every FAIL/WARNING check to provide concrete advice.**
- `impact-formulas.md` -- Revenue impact calculation formulas with worked examples and cross-metric cascade model. **Load when estimating financial impact.**
- `business-review-narratives.md` -- Performance narrative templates by growth trajectory, SCQA finding templates, risk assessment rubric, and cadence-specific recommendation templates. **Load this for business review interpretation.**

### For scoring and benchmarks:
- `scoring-system.md` -- Weighted scoring algorithm, severity multipliers, grading
- `benchmarks.md` -- Industry benchmarks by EC vertical
- `vertical-benchmarks.md` -- Vertical-specific KPI thresholds, seasonal calendars

### For check details:
- `revenue-decomposition.md` -- R01-R15 revenue checks
- `conversion-funnel.md` -- CV01-CV12 conversion checks
- `product-analysis.md` -- P01-P20 product checks
- `inventory-analysis.md` -- O01-O10 inventory checks
- `cohort-analysis.md` -- C01-C15 cohort/retention checks
- `pricing-analysis.md` -- PR01-PR12 pricing checks
- `site-audit-checks.md` -- SA01-SA15 site quality checks

### For data handling:
- `data-formats.md` -- Supported CSV formats, column mappings

---

## Output Format: AUDIT-REPORT.md

Write the report in this structure. Every section should contain **natural language
interpretation**, not just tables and numbers.

### 1. Executive Summary (narrative paragraph)

Read `references/executive-narratives.md` and use the grade-appropriate template.

Write a **2-3 sentence narrative paragraph** that:
- States the health score, grade, and business model
- Names the strongest and weakest categories
- Frames the key issue in business terms (not check IDs)
- Quantifies the estimated annual revenue impact
- Ends with a clear recommended first action

**Example (Grade B, 76/100):**
> With a 76/100 health score (B), this D2C store has a solid retention engine
> (Retention: 100/100) but is being held back by severe inventory problems
> (Inventory: 16/100). Nearly half of all SKUs are stocked out, and 83% of
> inventory has been sitting for over 180 days -- together these are costing
> an estimated $350K/year in lost revenue and tied-up capital. The fastest
> path to impact is to run a deadstock clearance campaign and implement
> demand-based restocking for the top 50 SKUs.

### 2. Category Scores (visual + interpretation)

Show the ASCII bar chart, then add **one sentence per category** explaining
what the score means in business terms:

```
   Revenue ████████████████████ 69
   Product █████████████████████████ 86
 Retention ██████████████████████████████ 100
 Inventory ████ 16
   Pricing ██████████████████████████████ 100
```

- **Revenue (69/100, C):** Revenue dropped 88% month-over-month, suggesting either seasonality or a traffic/acquisition problem that needs immediate investigation.
- **Product (86/100, B):** Strong product catalog with 99.9% of SKUs converting, though cross-sell opportunities are being missed.
- **Retention (100/100, A):** Exceptional -- 33.6% F2 rate and 43-day average repurchase interval indicate a loyal customer base.
- **Inventory (16/100, F):** Crisis-level -- 47.5% stockout rate and 83.2% deadstock rate signal a fundamental demand planning failure.
- **Pricing (100/100, A):** Healthy discount discipline at 1.6% average rate with stable trends.

### 3. Benchmark Comparison (with context)

Show the benchmark table, then **interpret each row**:

| Metric | Your Value | Industry Median | Top Quartile | Status |
|--------|-----------|----------------|-------------|--------|
| Repeat Revenue Share | 58.9% | 30.0% | 40.0% | Above Top Quartile |

> Your repeat revenue share of 58.9% is nearly double the industry median,
> indicating a strong returning customer base. This is a competitive advantage
> -- protect it by maintaining post-purchase engagement quality.

### 4. Key Themes (cluster analysis)

Read `references/finding-clusters.md`. For each activated cluster:

- **Name the theme** in plain language
- **Explain what the pattern means** (not just which checks failed)
- **Connect checks to each other** (show the systemic relationship)
- **Provide the recommended approach** in concrete terms

**Example:**
> **Inventory Distortion and Availability Drag** -- Three inventory checks are
> in critical/fail status, revealing a systemic problem: nearly half of SKUs
> are stocked out (O03: 47.5%), inventory turns only 0.5x per year (O01),
> and 83% of inventory is deadstock (O06). This creates a vicious cycle:
> popular items are unavailable while slow-movers accumulate, tying up cash
> and warehouse space. The stockout rate alone is estimated to cost 4.4% of
> monthly revenue in lost sales (O04). Prioritize: (1) identify and restock
> the top 20% of SKUs by velocity, (2) run aggressive markdown on 180+ day
> deadstock, (3) implement weekly demand-based reorder triggers.

### 5. Detailed Findings (per category)

For each category, show the checks table, then write **natural language
interpretation for every FAIL and WARNING**:

| Check | Severity | Result | Details |
|-------|----------|--------|---------|
| R01 | High | FAIL | MoM revenue growth: -87.6% |

> **R01: Revenue dropped 87.6% month-over-month.** This is an extreme decline
> that goes far beyond normal seasonality. Investigate: (1) Was there a major
> traffic source that stopped? (2) Did a key campaign end? (3) Is this a data
> artifact from an incomplete month? If the decline is real, a win-back
> campaign targeting the last 90 days of customers could recover 5-15% of
> the lost revenue within 2-4 weeks.

For PASS checks, a brief positive note is sufficient:
> **R05: Repeat revenue share is 58.9% (PASS).** Well above the 30% threshold
> and industry top quartile -- a clear strength.

Read `references/recommended-actions.md` to provide specific, sourced
recommendations for FAIL/WARNING checks.

### 6. Action Plan (prioritized with context)

For each priority level (Critical > High > Medium > Low):
- State the check and current value
- Explain **why** this matters in business terms
- Provide **specific actions** (from recommended-actions.md) with:
  - Implementation time estimate
  - Expected improvement range
  - Concrete first step

**Example:**
> **Critical: O03 -- Stockout SKU rate at 47.5% (threshold: 5%)**
>
> Nearly half your catalog is unavailable for purchase, directly suppressing
> revenue and damaging customer trust. Customers who encounter stockouts are
> 2-3x more likely to churn.
>
> **Actions:**
> 1. **Immediate (1-2 days):** Run a report of the top 50 SKUs by historical
>    revenue that are currently stocked out. Prioritize restocking these first.
> 2. **This week:** Implement back-in-stock email notifications so customers
>    waiting for popular items are automatically alerted. Expected recovery:
>    5-10% of lost stockout revenue.
> 3. **This month:** Set up demand-based reorder points using last 90 days of
>    velocity data. Target: reduce stockout rate from 47.5% to under 10%.
>
> *Estimated annual impact: $93,256*

### 7. Quick Wins

List 3-5 high-impact items that can be done quickly. For each:
- What to do (one clear sentence)
- Why (business impact)
- How long it takes
- Expected result

---

## Output Format: ACTION-PLAN.md

Write a standalone action plan document:
1. **Top 3 priorities** with full context and step-by-step instructions
2. **30-day roadmap** with weekly milestones
3. **Success metrics** -- what numbers should change and by how much

---

## Output Format: QUICK-WINS.md

A concise, scannable list of 3-5 items that can be done in under a day each,
with clear expected ROI.

---

## Review Workflow (MBR/QBR/ABR)

### Phase 1: Compute

```bash
# Generic review (auto-detects cadence from data span)
ecom review <orders.csv> --output <output-dir>

# Specific cadence
ecom review mbr <orders.csv> --products <products.csv> --output <output-dir>
ecom review qbr <orders.csv> --output <output-dir>
ecom review abr <orders.csv> --output <output-dir>

# With explicit period boundaries
ecom review <orders.csv> --period-start 2025-01-01 --period-end 2025-03-31 --output <output-dir>
```

### Cadence Differentiation

| Cadence | Focus | Findings Cap | Key Sections |
|---------|-------|-------------|--------------|
| MBR | Tactical/operational ("what happened, what to do next month") | 3 | Next Month Actions |
| QBR | Strategic + tactical (trend analysis, initiative tracking) | 4 | Risk Assessment, Recommendations, Category Growth |
| ABR | Strategic/high-level (annual performance, YoY growth) | 5 | Growth Drivers, 12-Month Trend, Annual Strategy |

### Phase 2: Interpret

Read the generated review file and enhance it with natural language insights:
- **Explain the "so what"** behind every metric change
- **Connect trends** -- if revenue is down AND orders are down, say "revenue
  decline is volume-driven, not price-driven"
- **Provide forward-looking recommendations** based on the trends
- **Use the Situation-Complication-Decision framework** for key findings
- **For Risk Assessment** -- contextualize risk severity and connect to business impact
- **For Recommendations** -- provide specific, time-bound actions matching the cadence

---

## Quality Gates

- Never present raw numbers without interpretation
- Always explain **why** a metric matters, not just its value
- Always provide **specific, actionable** recommendations (not generic advice)
- Read `recommended-actions.md` before writing recommendations -- use sourced data
- When data is insufficient, say so clearly and suggest what data to collect
- Use business language (revenue, customers, profit) not technical jargon (p-values, coefficients)
- Connect related findings to show systemic patterns, not isolated issues

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

> Weights sum to 110% -- `aggregate_score()` renormalizes to only categories present.

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

## Python Toolkit

The `claude_ecom` Python package provides computational backends:

```bash
cd claude-ecom
pip install -e .
ecom audit orders.csv --products products.csv --inventory inventory.csv
```

Modules: `loader`, `metrics`, `decomposition`, `cohort`, `product`, `inventory`,
`pricing`, `scoring`, `report`, `site_audit`, `site_crawler`, `review_engine`,
`shopify_api`, `sync`, `config`, `normalize`, `periods`.
