---
name: ecom
version: 0.1.0
description: >
  Claude-powered ecommerce analytics toolkit for D2C stores.
  Single command: review. Analyzes order transaction data across multiple
  time periods (30d/90d/365d), produces KPI trees with health signals,
  structured findings, and concrete action plans.
  Triggers on: "ecommerce review", "store review", "store health",
  "revenue analysis", "customer analysis", "product analysis",
  "business review".
argument-hint: "review [30d|90d|365d]"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Write
---

# ecom -- Ecommerce Analytics Toolkit

D2C ecommerce analytics system. The Python backend computes KPIs, runs
health checks, and scores performance from order transaction data;
**you** (Claude) interpret the numbers and write the human-readable report.

**Input:** Order transaction data only (CSV).

## Quick Reference

| Command | What it does | Output |
|---------|-------------|--------|
| /ecom review | Full business review (auto-selects periods from data) | REVIEW.md |
| /ecom review 30d | Focused on the last 30 days | REVIEW.md |
| /ecom review 90d | Focused on the last 90 days | REVIEW.md |
| /ecom review 365d | Focused on the last 365 days | REVIEW.md |
| /ecom review [question] | Answers a specific question from the data | Inline response |

One command. Two modes: full report or focused answer.

---

## Response Modes

### Mode 1: Full Review (default)

Triggered when: no natural-language question in the user's input.
Output: REVIEW.md file following the full 6-part structure defined below.

Examples: `/ecom review`, `/ecom review 30d`, `/ecom review 365d`

### Mode 2: Focused Query

Triggered when: user's input includes a natural-language question or topic.
Output: inline conversational response (no file creation).

Examples:
- "how was last month?" → extract from monthly_trend
- "how was last year?" → 365d data
- "how was Q4 last year?" → extract from monthly_trend
- "how's retention looking?" → customer metrics focus

#### Query-to-Period Mapping

| Query pattern | Data source |
|---|---|
| last 30 days | `--period 30d` |
| last 3 months / last 90 days | `--period 90d` |
| last year / this year | `--period 365d` |
| last month / specific month name | full run, extract from monthly_trend |
| Q1-Q4 / specific quarter | full run, extract from monthly_trend |

Calendar-month questions ("last month", "January") use the 365d monthly_trend, NOT a 30d trailing window. Use `--period 30d` only when the user explicitly asks for "last 30 days".

**Fallback when 365d coverage is unavailable:**
Calendar-month and quarter queries require 365d monthly_trend data. If 365d coverage is missing (data < 400 days):
- Answer from the best available trailing window data
- State that exact calendar-month/quarter breakdown is not available
- Suggest running a full review for deeper analysis

**monthly_trend limitation: no year-over-year comparison by month/quarter**
monthly_trend covers only the most recent 12 months. Comparing "Q4 this year vs Q4 last year" is not possible.
Instead:
- Present absolute values (revenue, orders) for the requested period
- Calculate its share of annual revenue (seasonality concentration)
- Compare against Q1-Q3 average for relative scale
- Add 365d overall YoY growth rate as context
- Do not mention the absence of YoY comparison (follow Handling Incomplete Data rules — omit what you can't measure)

If the query doesn't map to a clear period, run full (no --period flag) and answer from the most relevant data.

#### Focused Query Response Format

1. **Direct answer** (2-3 sentences with key numbers from review.json)
2. **Supporting context** (1-2 observations that add nuance — tensions, comparisons)
3. **One actionable takeaway** (if warranted by the data)

Total: 10-30 lines. Headings, KPI tree, and Finding format are NOT required. Use whatever structure best fits the answer.
For example, "what's the new vs returning split?" is clearest as a partial KPI tree.
Apply the same data rules: all numbers from review.json only, match user's language.
Do NOT create a REVIEW.md file.

---

## Data Input

Order transaction data (CSV). Each row = one order or line item.

Required columns:
- Order ID, Order date, Customer ID (or email)
- Revenue (after discounts, before tax/shipping)
- Quantity, SKU/Product ID
- Discount amount (if available)

```bash
ecom review orders.csv --output <output-dir>
ecom review orders.csv --period 90d --output <output-dir>
```

---

## Workflow

### Phase 1: Compute (Python)

```bash
ecom review orders.csv --output <output-dir>
```

The engine internally:

1. **Period analysis** -- computes KPIs for each time period (30d, 90d, 365d)
   with prior-period comparisons, decompositions, and trend detection.
2. **Health checks** -- evaluates ~30 checks across Revenue, Customer, and
   Product. Each check produces a pass/watch/fail signal with severity
   weighting. These power the 🟢/🟡/🔴 markers in the KPI tree.

Output: `review.json` (see Schema section below).

### Phase 2: Interpret (You -- Claude)

1. **Read `review.json`**
2. **Load reference files on demand** (see Reference Files below)
3. **Write REVIEW.md** following the Output Format below

**Your job is to weave trends and diagnostics into one coherent story.**
Period analysis tells you *where things are heading*. Health checks tell you
*what's broken right now*. The report combines both.

---

## review.json Schema

This is the data contract between Python and Claude. Every field below is
guaranteed to exist in the output. Claude reads this structure; Claude does
NOT invent data that isn't here.

```jsonc
{
  "version": "0.1.0",

  // --- Metadata ---
  "metadata": {
    "generated_at": "2026-03-05T18:00:00Z",
    "data_start": "2025-01-01",
    "data_end": "2025-12-31",
    "total_orders": 5784,
    "total_customers": 2765,
    "total_revenue": 1383651,
    "currency": "USD",
    "revenue_definition": "Net sales after discounts, before tax and shipping"
  },

  // --- Data quality warnings (empty array = no issues) ---
  "data_quality": [
    // Example entries (only present when issues detected):
    // { "type": "partial_period", "period": "2026-02", "days_with_data": 3,
    //   "message": "Latest month (2026-02) has only 3 days of data. MoM comparisons use prior complete months." }
    // { "type": "short_data_span", "days": 45, "message": "Data spans only 45 days..." }
    // { "type": "limited_data_span", "days": 200, "message": "Data spans 200 days (<1 year)..." }
  ],

  // --- Data coverage: which periods are available ---
  "data_coverage": {
    "30d": true,       // true if >=45 days of data exist
    "90d": true,       // true if >=120 days of data exist
    "365d": true       // true if >=400 days of data exist
  },

  // --- Period metrics (one block per available period) ---
  "periods": {
    "30d": {
      "summary": {
        "revenue": 98000,
        "revenue_change": -0.003,       // vs prior 30d
        "orders": 412,
        "orders_change": -0.03,
        "aov": 238,
        "aov_change": -0.001,
        "customers": 287,
        "customers_change": -0.05
      },
      "kpi_tree": {
        "new_customer_revenue": 38000,
        "new_customer_revenue_share": 0.388,
        "new_customers": 95,
        "new_customers_change": -0.08,
        "new_customer_aov": 400,
        "returning_customer_revenue": 60000,
        "returning_customer_revenue_share": 0.612,
        "returning_customers": 192,
        "returning_customers_change": -0.03,
        "returning_customer_aov": 312
      },
      "drivers": {
        "aov_effect": 1200,            // revenue change attributable to AOV
        "volume_effect": -1500,         // revenue change attributable to order count
        "mix_effect": 0                 // revenue change attributable to new/returning mix shift
      }
    },
    "90d": { /* same structure */ },
    "365d": {
      /* same structure as 30d (summary, kpi_tree, drivers) plus: */
      "repeat_purchase_rate": 0.38,   // only in 365d block
      "monthly_trend": [
        { "month": "2025-01", "revenue": 95000, "orders": 420, "aov": 226, "customers": 310, "new_customers": 180, "returning_customers": 130, "days_with_data": 31 },
        // ... only months with actual data (no zero-fill for future months)
        { "month": "2025-12", "revenue": 12000, "orders": 45, "aov": 267, "customers": 38, "new_customers": 10, "returning_customers": 28, "days_with_data": 3, "partial": true }
      ]
    }
  },

  // --- Health checks (powers 🟢/🟡/🔴 markers) ---
  "health": {
    "checks": [
      {
        "id": "R01",                    // internal only, never expose
        "category": "revenue",
        "severity": "high",
        "result": "watch",              // pass | watch | fail
        "message": "MoM revenue growth: -3.8%",
        "value": -0.038,
        "threshold": 0.0
      }
      // ... more checks
    ],
    "top_issues": [
      // Pre-sorted by severity * impact. Max 10.
      {
        "id": "P06",
        "category": "product",
        "severity": "high",
        "result": "fail",
        "message": "Multi-item order rate: 0.0%",
        "estimated_annual_impact": 77573
      }
      // ...
    ]
  },

  // --- Pre-computed action candidates ---
  "action_candidates": [
    {
      "action": "Introduce product bundles to increase multi-item orders",
      "source_check": "P06",            // internal reference
      "severity": "high",
      "estimated_annual_impact": 77573,
      "timeline": "this_month"
    }
    // ... max 10 candidates, sorted by impact
  ]
}
```

### Schema Rules

- `periods` only contains keys for periods where `data_coverage` is `true`
- All `_change` fields are proportional change vs prior period (e.g., 0.08 = +8%)
- `health.checks` contains every check result; `health.top_issues` is a
  filtered/sorted subset (fail and watch only, max 10, sorted by severity × impact)
- `action_candidates` are suggestions from Python; Claude refines, merges, and
  rewrites them in business language for the report
- `monthly_trend` contains only months with actual order data (no zero-fill for future months)
- `monthly_trend` entries with `"partial": true` have less than half the month's days with data
- When `data_quality` is non-empty, mention relevant warnings in Data Notes

---

## Reference Files

Load on-demand -- do NOT load all at startup.

> **Path:** `ecom/references/`

- `review-narratives.md` -- Narrative templates by health level and growth trajectory, finding templates, period-specific guidance. **Always load.**
- `finding-clusters.md` -- Cluster model for grouping related issues into themes. **Load to identify themes.**
- `recommended-actions.md` -- Actionable recommendations per check with timeline and impact range. **Load for watch/fail checks.**
- `impact-formulas.md` -- Revenue impact formulas with worked examples. **Load when estimating impact.**
- `health-checks.md` -- Check definitions (R/C/P) with thresholds and interpretation.
- `benchmarks.md` -- D2C ecommerce KPI benchmarks.

---

## Output Format: REVIEW.md

The following structure applies to Full Review mode only. See Response Modes for Focused Query.

One report. Three parts. **Target: ~150 lines.** Tighter is better.

### Report Construction Checklist (MANDATORY)

Before writing, verify your report contains ALL sections in this exact order.
Missing or reordered sections are a format violation.

1. [ ] Executive Summary -- narrative blockquote (4-6 lines) + Scoreboard table
2. [ ] 30d Pulse section (if data available) -- KPI tree + max 1 finding
3. [ ] 90d Momentum section (if data available) -- KPI tree + drivers + max 2 findings
4. [ ] 365d Structure section (if data available) -- KPI tree + drivers + max 3 findings
5. [ ] Action Plan -- max 5 items grouped by time horizon + Guardrails
6. [ ] Data Notes -- 2-4 lines

Structural rules:
- Sections MUST appear in this order. Do NOT reorganize by theme.
- Period sections MUST use the KPI tree format with emoji markers.
- Do NOT create standalone sections like "What's Working Well" or "Issues to Address".
- Positive signals belong in Executive Summary narrative and KPI tree markers.

---

### Part 1: Executive Summary

#### Narrative (4-6 lines, blockquote)

Synthesize across all available periods. Structure:

```
[North Star result + trend across periods]
[What's working: 1-2 strengths confirmed by data -- 80/20 rule]
[What needs attention: the key tension/risk, with data]
[Most important action, with timeline]
```

**Example:**
> Revenue reached $1.38M for the year (+25.7% YoY), but growth is decelerating --
> the last 90 days grew only 8% vs prior 90 days, and last month was flat (+0.3%).
> Growth depends on existing customer AOV increases (+14.8%), while new customer
> acquisition has stalled (share: 42.3%, unchanged). Reallocate 20% of retention
> budget to acquisition channels by end of this month, targeting CPA below $XX.

#### Scoreboard

```
          30d Pulse     90d Momentum    365d Structure
Revenue   $98K (= flat) $340K (+ 8%)    $1.38M (+ 26%)
Orders    412 (- 3%)    1,280 (+ 5%)    5,784 (+ 10%)
AOV       $238 (= flat) $266 (+ 12%)    $239 (+ 15%)
Customers 287 (- 5%)    812 (+ 3%)      2,765 (+ 10%)
```

`+` improving, `-` deteriorating, `=` stable.
Only show periods that data supports.

---

### Part 2: Period Sections

**CRITICAL: Each period gets its own heading and its own KPI tree. Do NOT merge periods into thematic sections.**

All periods use the same skeleton. **But they are not equal length:**

| Period | Depth | Findings cap | Role |
|--------|-------|-------------|------|
| 30d Pulse | Shallow -- KPI tree + 1-2 sentences + max 1 finding | 1 | Flag fires only |
| 90d Momentum | Medium -- KPI tree + drivers + max 2 findings | 2 | Main analytical body |
| 365d Structure | Deep -- KPI tree + drivers + max 3 findings | 3 | Strategic narrative |

If only one period is available, give it the full depth (3 findings).

**The total across all periods must not exceed 5-7 findings.** If a theme
appears in multiple periods, state it once at the most structural level and
reference supporting signals from shorter periods.

#### Skeleton

##### [Period Name]: [One-line headline -- the "so what"]

**KPI Tree:**

```
Revenue $X (vs prior period: +X%)
|-- 🟢 New Customer Revenue $X (X% of total)
|   |-- New Customers: X (+X%)
|   |-- New Customer AOV: $X (+X%)
|-- 🟡 Existing Customer Revenue $X (X% of total)
    |-- Returning Customers: X (+X%)
    |-- Returning AOV: $X (+X%)
    |-- Repeat Purchase Rate: X% -- first-to-second purchase conversion (365d only)
```

🟢 healthy / 🟡 watch / 🔴 problem (driven by health check results).

**Growth Drivers** (1-2 sentences, 90d and 365d only):

Was the change volume-driven or price-driven? Connect to KPI tree nodes.

**Findings** (within period cap):

Each follows Finding Quality Standards. Findings should weave trend data and
health check diagnostics together, not present them separately. Use this format:

### [Finding title]

**What is:** [1 sentence, quantitative fact]

**Why it matters:** [Data-backed tension with "however"/"despite"/"but"]

**What to do:** [Direction only — 1 sentence. Details go in Action Plan.]

---

### Part 3: Action Plan (unified, max 5 items)

**Hard cap: 5 action items. Exceeding 5 is a format violation.**

Action Plan is the single source of truth for deadlines and success metrics.
Findings point to the problem and direction; Action Plan specifies the execution.

One list synthesizing across all periods. Group by time horizon:

```
Immediate (from 30d signals)
1. ...

This Month (from 90d findings)
2. ...

This Quarter (from 365d insights)
3. ...
```

For each item:
- **What** (one concrete sentence)
- **Why** (reference specific data)
- **When** (specific deadline)
- **Success metric** (measurable)

End with (REQUIRED -- omitting Guardrails is a format violation):
> **Guardrails:** [2-3 metrics that must not deteriorate while executing above actions]
>
> Example: AOV must stay above $X | Repeat purchase rate must not drop below X% | Discount rate must stay under X%

---

### Data Notes (2-4 lines)

Always include:
- Revenue definition (from `metadata.revenue_definition`)
- Data period and order count
- Periods included/omitted

---

## Period Interaction Rules

- **Confirm or contradict across periods.** Don't let periods exist in isolation.
- **Zoom in:** If 90d shows a break, check 30d for continuation.
- **Never repeat a finding across periods.** State once at the structural level.
- **Executive Summary synthesizes**, does not summarize sequentially.

---

## Finding Quality Standards

**Every finding follows: What is → Why it matters → What to do**

- **What is:** 1 sentence. Quantitative fact. No interpretation.
- **Why it matters:** Data-backed tension. Must show contrast ("despite", "however").
  Abstract concerns like "growth must be validated" are PROHIBITED.
- **What to do:** Direction and rationale only — 1 sentence. Deadlines and
  success metrics belong in the Action Plan. "Consider", "improve", "optimize",
  "explore" are PROHIBITED.

**Good:**
```
What is:       Annual revenue grew 25.7% YoY.
Why it matters: However, despite a 25.4% reduction in discount rate, new customer
               revenue share remains at 42.3% -- growth depends entirely on
               existing customer AOV increases (+14.8%).
What to do:    Reallocate retention budget toward acquisition channels to diversify growth sources.
```

**Bad (PROHIBITED):**
```
What is:       Revenue grew 25.7%.
Why it matters: Rapid growth must be validated. <-- no data, no tension
What to do:    Consider improving acquisition. <-- banned verb, no deadline
```

---

## Handling Incomplete Data

- Omit what you can't measure. No N/A, no empty sections.
- Don't apologize. Never say "unfortunately..."
- Shorter data = shorter report.
- All gaps noted in Data Notes only.

---

## Language and Data Scope Rules

### Language
- Write entire report in ONE language (match user's prompt/store language)
- Data Notes follows same language as body

### Data Scope: review.json Only
- All numbers MUST come from review.json or be derived from its values
- Do NOT reference external sources (Shopify Analytics, GA, etc.)
- If additional data would help, note as recommended investigation in "What to do"
- PROHIBITED: "CVR from Shopify shows 2.1%" (CVR not in review.json)
- ALLOWED: "Investigate CVR in Shopify Analytics to determine root cause"

### data_quality Warnings
- When `data_quality` array is non-empty, mention relevant warnings in Data Notes
- Do NOT present partial-month MoM as real performance signals

---

## Quality Gates

- Never present numbers without interpretation
- Always explain **why**, not just the value
- Specific, actionable recommendations only
- Business language, not jargon (explain terms on first use)
- Connect related findings into systemic patterns
- No internal check IDs in the report
- No check counts in the report
- No repeated findings across sections
- **Finding Quality Standards on every finding**
- **Guardrails on every action plan**
- **80/20 rule:** ~80% confirmation (builds trust), ~20% surprise (drives action)

---

## Internal: Health Check Engine

> Each check returns pass / watch / fail. These power the 🟢🟡🔴 KPI tree markers.
> Check definitions in `references/health-checks.md`.
> Do NOT use numeric scores, letter grades, or percentage-based health ratings.

---

## Python Toolkit

```bash
cd claude-ecom
pip install -e .
ecom review orders.csv
ecom review orders.csv --period 90d
```

Modules: `loader`, `metrics`, `decomposition`, `cohort`, `product`,
`checks`, `report`, `review_engine`, `config`, `normalize`, `periods`.
