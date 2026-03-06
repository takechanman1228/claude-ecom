# Finding Clusters for Ecommerce Review


## Purpose and design assumptions

"Finding clusters" are a layer above individual checks: they group multiple related non-pass results (watch/fail) into executive-level themes that are more likely to represent **systemic** problems than isolated metric noise. Many of the biggest ecommerce performance drags show up as *patterns* across merchandising, pricing, and customer behavior rather than as single-metric anomalies.

Retention economics are well-established: improving retention rates can have outsized profit effects, which is why "repeat + churn + LTV" clusters should be treated as board-level issues when multiple sub-signals fire together.

---

## Finding cluster catalog

The check descriptions below use only **implemented checks** (those the Python backend evaluates). The cluster logic is designed so that **multiple** non-pass checks activate a theme, which reduces false alarms and elevates "structural" patterns.

---

### Cluster B -- Promo-Led Growth and Margin Compression

**Member checks (cross-category):**

| Check ID | Brief description (what "non-pass" typically implies) |
|---|---|
| PR02 | Promo penetration is high (% of orders with discounts/codes). |
| PR03 | Discount depth trend is escalating (deeper discounts over time). |
| PR08 | Free-shipping threshold is not driving AOV increase effectively. |
| R01 | Revenue growth appears driven by discounting rather than underlying demand. |
| R08 | Average discount rate is rising, eroding margins (subsumes former PR01). |

**Activation rule:** Activate when **>= 2** checks are non-pass, **including at least one** discount intensity check (PR02/PR03) **and** at least one revenue or margin signal (R01/R08/PR08).

**Root cause hypothesis template:**

> "{n} pricing and margin checks flagged {severity_level}, indicating growth is being purchased through discount depth/frequency and is compressing unit economics. {worst_check} is most critical; validate whether discounting is incremental or cannibalizing full-price demand."

**Recommended approach:** Rebuild pricing/promo governance: segment promos by goal (acquisition vs reactivation vs inventory liquidation), tighten code eligibility, and introduce markdown optimization rather than blanket discounts.

---

### Cluster C -- Assortment and Merchandising Misfit

**Member checks (cross-category):**

| Check ID | Brief description (what "non-pass" typically implies) |
|---|---|
| P01 | Assortment breadth misfit: too many or too few SKUs for demand (dilution or lack of choice). |
| P05 | Converting SKU rate is low: many SKUs are inactive/low-velocity. |
| P06 | Multi-item order rate is low (weak cross-sell / product adjacency). |
| P07 | Cross-sell pair lift is weak (no strong product affinities found). |
| P10 | Lifecycle imbalance: too many decline-stage products vs core winners. |
| P19 | Price tier distribution is too narrow (limited market reach). |
| R08 | Category/collection concentration signals: revenue overly skewed. |

**Activation rule:** Activate when **>= 3** checks are non-pass, including at least **two** Product checks and at least **one** of (R08 or PR07) to ensure this is cross-functional (assortment *and* commercial architecture).

**Root cause hypothesis template:**

> "{n} assortment/merchandising checks flagged {severity_level}, suggesting the catalog is misaligned to demand and value positioning (too much tail, weak launches, or unclear tiers). {worst_check} is most critical; validate whether the issue is breadth (too many SKUs) or depth (missing winners) and whether pricing architecture reinforces or confuses choices."

**Recommended approach:** Do SKU and category rationalization with clear roles (hero/core/seasonal/experimental), improve category-level merchandising (sorting, bundling, cross-sell adjacency), and align internal price ladders to clear "good-better-best" tiers.

---

### Cluster F -- Customer and LTV Engine Weakness

**Member checks (cross-category):**

| Check ID | Brief description (what "non-pass" typically implies) |
|---|---|
| C01 | Repeat purchase rate is low for the business model/category. |
| C08 | Champions + Loyal segment share is low (not enough high-value customers). |
| C09 | At-Risk segment share is high (engaged customers drifting away). |
| C10 | Lost segment share is high (chronic retention failure). |
| C11 | Days to second purchase is too long (slow second-order conversion). |
| R05 | New vs returning revenue mix is skewed toward new (repeat base not contributing). |
| R14 | Large order dependency suggests fragile, non-recurring revenue. |

**Activation rule:** Activate when **>= 3** checks are non-pass, including at least one RFM segment check (C08/C09/C10) and at least one value check (C01/C11/R05).

**Root cause hypothesis template:**

> "{n} customer and value checks flagged {severity_level}, indicating the store is failing to convert first-time buyers into repeat buyers at profitable frequency/velocity. {worst_check} is most critical; diagnose whether the primary break is early repeat (time-to-2nd) or long-run churn, and identify the weakest cohort ({worst_cohort})."

**Recommended approach:** Build a customer "engine" (post-purchase onboarding, replenishment triggers, lifecycle marketing, loyalty economics, and category expansion) and tie it tightly to margin and product strategy.

---

### Cluster G -- Revenue Concentration and Growth Sustainability Risk

**Member checks (cross-category):**

| Check ID | Brief description (what "non-pass" typically implies) |
|---|---|
| R04 | Order count trend declining (demand concentration risk). |
| R07 | Revenue concentration: top 10% of customers drive too much revenue. |
| P01 | Product concentration: top 20% of SKUs overly dominant. |

**Activation rule:** Activate when **>= 2** checks are non-pass, including at least one concentration check (R07/P01).

**Root cause hypothesis template:**

> "{n} concentration-related checks flagged {severity_level}, suggesting structural fragility: revenue depends on a narrow set of customers/SKUs. {worst_check} is most critical; quantify downside if the top dependency is disrupted and define the diversification path."

**Recommended approach:** Quantify concentration (top-N share) and pursue deliberate diversification (bench products behind hero SKUs, broaden customer base through customer programs).

---

## Standalone checks

These checks are intentionally **not included in cluster activation logic** because they are either single-point-of-failure incidents or highly data-dependent:

| Check ID | Why it is standalone | Brief description |
|---|---|---|
| PR07 | Model-dependent | Category margin variance signal is category-specific; cluster activation would be noise. |
| R13 | Can be incident-like | Daily revenue volatility may reflect one-off events rather than structural issues. |

---

## Deduplication and overlap rules

1. **Single primary owner.** A check can appear in multiple clusters as **supporting evidence**, but it should have exactly one **Primary Cluster** for activation counting.

2. **Closest actionable root cause.** If two clusters could plausibly own a check, assign ownership based on **closest actionable root cause** (not the symptom). Discount intensity belongs to Cluster B; customer segment drift belongs to Cluster F.

3. **Worst-check selection.** When selecting `{worst_check}` in hypothesis templates, pick the non-pass check with the highest severity (Fail = 2 points, Watch = 1 point; tie-break by estimated $ impact).

---

## Priority ordering when multiple clusters activate simultaneously

1. **B -- Promo-Led Growth and Margin Compression** -- Discount dependency creates a treadmill where revenue requires margin sacrifice.
2. **C -- Assortment and Merchandising Misfit** -- Catalog structure influences both conversion and margin.
3. **F -- Customer and LTV Engine Weakness** -- Customer programs are a compounding engine; failure means growth only through acquisition spend.
4. **G -- Revenue Concentration and Growth Sustainability Risk** -- Concentration is the "second-order" strategic risk.

---

## Practical implementation notes

Implement clusters as deterministic rules over your existing check statuses: each check emits `{pass, watch, fail, n/a}`. Activate a cluster when its rule is met, then generate the executive narrative using the template placeholders (`{n}`, `{worst_check}`, etc.).

To keep clusters robust across seasonality and promo calendars, consider evaluating checks on two windows:

- **Short window** (e.g., trailing 28 days) for incident detection.
- **Long window** (e.g., trailing 90 days) for structural confirmation.

Treat a finding as "structural" only when the cluster activates in both windows or repeatedly across weeks.
