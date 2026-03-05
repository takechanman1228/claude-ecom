# Finding Clusters for 84-Check Ecommerce Audit

<!-- Updated: 2026-03-04 | Source: DR5 7-cluster model -->

## Purpose and design assumptions

"Finding clusters" are a layer above individual checks: they group multiple related non-pass results (warn/fail) into executive-level themes that are more likely to represent **systemic** problems than isolated metric noise. This is useful because many of the biggest ecommerce performance drags tend to show up as *patterns* across funnel, merchandising, inventory, pricing, and retention rather than as single-metric anomalies. For example, cart/checkout abandonment is consistently high across ecommerce, and shoppers cite "extra costs," "delivery too slow," "lack of trust," and "too long/complicated checkout" among common reasons to abandon -- i.e., a multi-factor pattern rather than a single cause.

Research also shows that relatively small improvements in site speed can measurably improve conversion-related KPIs and consumer spend, reinforcing the idea that a cluster of "early funnel + speed + mobile gap" failures often indicates structural experience friction.

Supply and post-purchase operations similarly show up as cross-metric patterns. Inventory distortion (out-of-stocks + overstocks) is widely cited as a massive value leak in retail, and stockouts can trigger customer substitution/switching behaviors -- so a combined "availability + demand planning + churn" signal is rarely a one-off.

Returns and retention are also highly cross-functional. Large-retailer surveys cite return rates approaching ~17% of sales in 2024 and an industry cost estimate of ~$890B, underscoring that "returns + margin + repeat purchase softness" is often a structural loop (merchandising, quality/fit, policy, logistics) rather than an isolated KPI spike.

Finally, retention economics are well-established: improving retention rates can have outsized profit effects, which is why "repeat + churn + LTV" clusters should be treated as board-level issues when multiple sub-signals fire together.

---

## Finding cluster catalog

The check descriptions below are **recommended canonical interpretations** aligned to your category blurbs (Revenue, Conversion, Product, Inventory, Retention, Pricing). If your internal checklist text differs, keep the *cluster intent* stable and swap the row descriptions accordingly. The cluster logic is designed so that **multiple** non-pass checks activate a theme, which reduces false alarms and elevates "structural" patterns.

---

### Cluster A -- Purchase Funnel Breakdown

**Member checks (cross-category):**

| Check ID | Brief description (what "non-pass" typically implies) |
|---|---|
| CV01 | Bounce/engagement signal: traffic lands but does not meaningfully engage (landing relevance/intent mismatch). |
| CV02 | Product discovery depth: low PDP/view rate per session (browse layer not moving users to products). |
| CV03 | Add-to-cart rate: weak product-to-cart progression. |
| CV04 | Cart abandonment: many carts created but not progressed (cost shock, uncertainty, distraction). |
| CV05 | Checkout initiation: cart-to-checkout drop (trust, friction, lack of clarity). |
| CV06 | Checkout completion: checkout-to-purchase drop (forms, login, payment methods, errors). |
| CV08 | Mobile conversion gap: mobile materially underperforms desktop beyond mix expectations. |
| CV09 | New vs returning conversion gap: new shoppers fail to convert relative to returners (trust/info deficit). |
| CV10 | Channel conversion dispersion: some acquisition sources convert far worse (mis-targeting or landing mismatch). |
| CV11 | Cost/delivery friction abandonment: drop-off correlated with shipping/tax/fees or delivery promises. |
| CV12 | Search & navigation friction: zero-results, poor filters, low search-to-purchase efficiency. |
| P09 | PDP content completeness: missing/weak info (images, specs, sizing, delivery, returns clarity). |
| P10 | Variant/option complexity: configuration friction (size/color not clear, choice overload). |
| P11 | Reviews coverage/rating health: insufficient social proof or quality perception signals. |
| P15 | Search query coverage/merchandising: top internal queries not well served or surfaced. |
| PR10 | Shipping economics & threshold friction: shipping fees/thresholds likely depressing conversion. |
| R12 | Revenue per session/visitor: monetization efficiency is low given traffic. |

**Activation rule:** Activate when **>= 3** of the above checks are non-pass, **including at least one** late-funnel check (CV05 or CV06) *or* at least **two** mid-to-late funnel checks (CV03--CV06, CV11). (This avoids triggering on "top-of-funnel traffic quality" alone.)

**Root cause hypothesis template:**

> "{n} funnel-related checks flagged {severity_level}, suggesting structural friction in the browse -> cart -> checkout path rather than isolated variance. {worst_check} appears most critical; investigate the largest step-drop ({worst_step}) and the dominant friction driver ({top_friction})."

**Recommended approach:** Prioritize a *step-by-step funnel diagnosis* (segment by device and channel), then run targeted UX and checkout simplification work (form reduction, clarify total cost earlier, improve guest/returning flows, fix speed and error states). This aligns with evidence that checkout complexity, extra costs, trust concerns, and technical errors are common abandonment drivers.

**Example scenario:** A DTC brand reports "traffic is up," but CV03--CV06 are all below prior baselines. Mobile conversion is far below desktop, internal search produces many zero-results, and PDPs lack sizing clarity and reviews on key SKUs. Revenue per session is depressed despite steady AOV, implying the core issue is *experience progression* rather than demand.

---

### Cluster B -- Promo-Led Growth and Margin Compression

**Member checks (cross-category):**

| Check ID | Brief description (what "non-pass" typically implies) |
|---|---|
| PR01 | Average discount rate is high vs target/seasonality expectations. |
| PR02 | Promo penetration is high (% of orders with discounts/codes). |
| PR03 | Gross margin % after discounting is below target. |
| PR04 | Contribution margin (incl. shipping subsidies/returns allowance) is below target. |
| PR08 | Promo incremental lift is weak (high cannibalization; low true incrementality). |
| PR09 | Coupon leakage/stacking: unprofitable code behavior or uncontrolled eligibility. |
| PR11 | Clearance/markdown reliance is high (late lifecycle inventory cleared via discounting). |
| R01 | Revenue growth appears driven by discounting rather than underlying demand. |
| R02 | Growth momentum is decelerating (promos needing to be deeper/more frequent). |
| R10 | AOV signal is promo-inflated or deteriorates off-promo (weak baseline willingness-to-pay). |
| R11 | Basket size/units per order distort under promos (bundling behavior driven by thresholds). |
| C13 | Repeat purchases are discount-dependent (customers wait for promos). |
| P17 | Price ladder/value architecture is inconsistent (mispriced tiers drive discounting pressure). |

**Activation rule:** Activate when **>= 2** checks are non-pass, **including at least one margin/profitability check** (PR03 or PR04) **and** at least one discount/promo intensity check (PR01/PR02/PR11/PR09).

**Root cause hypothesis template:**

> "{n} pricing and margin checks flagged {severity_level}, indicating growth is being purchased through discount depth/frequency and is compressing unit economics. {worst_check} is most critical; validate whether discounting is incremental ({promo_incrementality}) or cannibalizing full-price demand."

**Recommended approach:** Rebuild pricing/promo governance: segment promos by goal (acquisition vs reactivation vs inventory liquidation), tighten code eligibility, and introduce markdown optimization rather than blanket discounts. Analytics-led pricing and markdown decisions are frequently cited as major levers for improving both revenue and profits.

**Example scenario:** A retailer posts strong top-line weeks during sitewide 20--30% events, but PR03/PR04 and PR09 fail: margins compress and coupon stacking creates negative-margin orders. Off-promo weeks show revenue softness (R02), and repeat customers mostly buy only with codes (C13), signaling a structurally weakened price-value positioning.

---

### Cluster C -- Assortment and Merchandising Misfit

**Member checks (cross-category):**

| Check ID | Brief description (what "non-pass" typically implies) |
|---|---|
| P01 | Assortment breadth misfit: too many or too few SKUs for demand (dilution or lack of choice). |
| P02 | Active SKU ratio is low: many SKUs are inactive/low-velocity. |
| P03 | Long-tail productivity is weak: a large share of SKUs generate negligible revenue. |
| P05 | Newness rate is low: little revenue from recently launched products. |
| P06 | Launch success is weak: new items fail early sell-through/engagement. |
| P07 | Lifecycle imbalance: too much end-of-life/obsolete vs core winners. |
| P08 | Category performance dispersion is high: "dead categories" coexist with a few winners. |
| P13 | Cross-sell/upsell attach rate is low (add-ons not converting). |
| P14 | Bundles/kits underperform (bundling not delivering higher AOV/margin). |
| P16 | Recommendation/personalization effectiveness is weak (little lift). |
| P18 | Cannibalization/duplicate SKUs: overlapping products split demand. |
| P19 | Market-basket affinity signals are weak or not operationalized (poor adjacency merchandising). |
| R08 | Category/collection concentration signals: revenue overly skewed into a narrow set of categories. |
| PR06 | Price dispersion/architecture issues inside categories (confusing ladders, gaps, overlaps). |

**Activation rule:** Activate when **>= 3** checks are non-pass, including at least **two** Product checks and at least **one** of (R08 or PR06) to ensure this is cross-functional (assortment *and* commercial architecture).

**Root cause hypothesis template:**

> "{n} assortment/merchandising checks flagged {severity_level}, suggesting the catalog is misaligned to demand and value positioning (too much tail, weak launches, or unclear tiers). {worst_check} is most critical; validate whether the issue is breadth (too many SKUs) or depth (missing winners) and whether pricing architecture reinforces or confuses choices."

**Recommended approach:** Do SKU and category rationalization with clear roles (hero/core/seasonal/experimental), improve category-level merchandising (sorting, bundling, cross-sell adjacency), and align internal price ladders to clear "good-better-best" tiers. Personalization and cross-sell programs can be meaningful revenue/profit levers when operationalized well.

**Example scenario:** A brand has 3,000 SKUs, but most revenue comes from a few subcategories (R08) while many SKUs show zero sales (P03/P02). New launches don't stick (P06), bundles don't move (P14), and recommendations do not lift AOV (P16). The catalog is "busy," but merchandising is not guiding customers into coherent tiers and complements.

---

### Cluster D -- Inventory Distortion and Availability Drag

**Member checks (cross-category):**

| Check ID | Brief description (what "non-pass" typically implies) |
|---|---|
| O01 | Overall in-stock rate is below service-level target. |
| O02 | Top-seller in-stock rate is weak (availability failing where it matters most). |
| O03 | Stockout days / time-to-restock is high (slow recovery). |
| O04 | Inventory turnover is unhealthy (too slow = cash tied up; too fast = understock risk). |
| O05 | Days inventory on hand is far from target (over/under). |
| O06 | Aged inventory share is high (slow movers accumulating). |
| O07 | Excess inventory vs forecast is high (overbuying / weak sell-through). |
| O08 | Forecast error is high (demand planning miscalibration). |
| R03 | Revenue volatility suggests supply-demand mismatch (availability constraining revenue or forcing promos). |
| C14 | Churn / retention deterioration correlates with OOS or fulfillment issues (availability-driven churn). |

**Activation rule:** Activate when **>= 2** checks are non-pass, **including at least one** stockout/service-level signal (O01--O03) **and** at least one planning/efficiency signal (O04--O08) or downstream impact signal (R03/C14).

**Root cause hypothesis template:**

> "{n} inventory health checks flagged {severity_level}, indicating inventory distortion (out-of-stocks and overstocks) that is simultaneously constraining sales and tying up cash. {worst_check} is most critical; validate whether the primary failure is planning accuracy ({forecast_error}) or replenishment/availability execution ({restock_time})."

**Recommended approach:** Segment service levels by SKU role (hero vs tail), rebuild forecast inputs, and tighten replenishment and "back-in-stock" operating cadence. Inventory distortion is repeatedly described as a major industry cost center, and stockouts can influence switching/substitution behaviors that harm loyalty when repeated.

**Example scenario:** A retailer shows simultaneous O02 stockouts on top sellers and O06/O07 excess inventory in the tail. Revenue is spiky (R03) because promotions are used to clear overstocks while heroes are unavailable. Customer cohorts that encounter OOS have higher churn (C14), turning inventory problems into retention problems.

---

### Cluster E -- Returns, Trust, and Post-Purchase Friction

**Member checks (cross-category):**

| Check ID | Brief description (what "non-pass" typically implies) |
|---|---|
| R13 | Net revenue is heavily reduced by refunds/returns (net vs gross gap is high). |
| P12 | Returns by SKU/category are elevated (quality, fit, expectation mismatch). |
| O10 | Returns processing / restock cycle time is slow (reverse logistics drag). |
| C15 | Post-purchase dissatisfaction signals are elevated (complaint/contact rate, poor post-purchase sentiment). |

**Activation rule:** Activate when **>= 2** checks are non-pass, and at least one is R13 or P12 (so the cluster reflects economic impact or product-level root causes, not just operations timing).

**Root cause hypothesis template:**

> "{n} post-purchase checks flagged {severity_level}, suggesting a returns-and-trust loop where product expectations, policies, and reverse logistics are degrading net revenue and loyalty. {worst_check} is most critical; identify the dominant return driver ({top_return_reason}) and the highest-impact SKU/category ({top_return_sku})."

**Recommended approach:** Treat returns as a structural profit and retention lever: improve pre-purchase clarity (fit/specs, imagery, reviews), reduce high-return SKUs, and streamline reverse logistics so returned units are recovered faster. Returns are widely cited as large-scale industry cost pressure, and dissatisfaction with returns policy/experience can influence purchase completion and repeat behavior.

**Example scenario:** A fashion store has acceptable front-end conversion but a widening net-vs-gross revenue gap (R13). A small set of SKUs drive disproportionate returns (P12), and operations take weeks to process returns (O10), keeping inventory locked. Post-purchase contacts spike (C15), and repeat rate softens in cohorts exposed to return friction.

---

### Cluster F -- Retention and LTV Engine Weakness

**Member checks (cross-category):**

| Check ID | Brief description (what "non-pass" typically implies) |
|---|---|
| C01 | Repeat purchase rate is low for the business model/category. |
| C02 | Purchase frequency is low (customers are not forming a habit). |
| C03 | Time to second purchase is long (slow second-order conversion). |
| C04 | Cohort retention curve drops steeply after first purchase. |
| C05 | Churn/inactivity rate is high. |
| C06 | Reactivation rate is low (lapsed customers not returning). |
| C07 | LTV is low or declining (value per customer shrinking). |
| C09 | Loyalty program engagement is weak (if present). |
| C10 | Subscription/replenishment retention is weak (if present). |
| C11 | Cross-category repeat behavior is weak (customers don't expand beyond first category). |
| C12 | Returning-customer value differential is weak (returners don't outperform materially). |
| R05 | New vs returning revenue mix is skewed toward new (repeat base not contributing). |
| R14 | Recurring/returning revenue base is fragile (low predictable revenue component). |
| P20 | Category penetration / multi-category purchase rate is low (narrow relationship breadth). |

**Activation rule:** Activate when **>= 3** checks are non-pass, including at least one cohort-shape check (C03 or C04 or C05) and at least one value check (C07 or C12 or R05).

**Root cause hypothesis template:**

> "{n} retention and value checks flagged {severity_level}, indicating the store is failing to convert first-time buyers into repeat buyers at profitable frequency/velocity. {worst_check} is most critical; diagnose whether the primary break is early repeat (time-to-2nd) or long-run churn, and identify the weakest cohort ({worst_cohort})."

**Recommended approach:** Build a retention "engine" (post-purchase onboarding, replenishment triggers, lifecycle marketing, loyalty economics, and category expansion) and tie it tightly to margin and product strategy. Retention improvements can have outsized profit impact, and loyalty economics in ecommerce are often driven by repeat customers buying more over time with lower serve cost.

**Example scenario:** A consumables brand has healthy first-purchase acquisition but weak second-order conversion (C03) and a steep cohort curve (C04). Returning customer value is not meaningfully higher than new (C12), and reactivation is low (C06). Revenue mix is dominated by new customers (R05), meaning growth requires continuous acquisition spend rather than compounding loyalty.

---

### Cluster G -- Revenue Concentration and Growth Sustainability Risk

**Member checks (cross-category):**

| Check ID | Brief description (what "non-pass" typically implies) |
|---|---|
| R04 | Channel concentration: over-reliance on one channel/platform for revenue. |
| R06 | Customer concentration: a small set of customers drive a large % of revenue. |
| R07 | Product concentration: a small set of SKUs drive a large % of revenue. |
| R09 | Geographic concentration: one region drives a large % of revenue. |
| P04 | Hero SKU dependency: business is fragile to winner stockouts or trend shifts. |
| PR05 | Price competitiveness mismatch: relative price position threatens volume or margin. |

**Activation rule:** Activate when **>= 2** checks are non-pass, including at least one concentration check (R04/R06/R07/R09/P04). Treat PR05 as an amplifying condition when present.

**Root cause hypothesis template:**

> "{n} concentration-related checks flagged {severity_level}, suggesting structural fragility: revenue depends on a narrow set of channels/customers/SKUs/regions. {worst_check} is most critical; quantify downside if the top dependency is disrupted ({top_dependency}) and define the diversification path ({diversification_vector})."

**Recommended approach:** Quantify concentration using simple concentration metrics (e.g., top-N share; optionally HHI-style indices) and pursue deliberate diversification (bench products behind hero SKUs, broaden channel mix, and deepen retention so customer concentration is less brittle). Concentration is a recognized business risk concept, and the Herfindahl-Hirschman Index is a standard concentration measure that can be adapted for channel/product mix diagnostics.

**Example scenario:** An ecommerce business gets 60% of revenue from a single marketplace channel (R04) and 35% from one hero SKU (R07/P04). When the hero goes out of stock or a platform algorithm changes, revenue collapses. Even if conversion is healthy, the business profile is strategically fragile until it builds "bench depth" (alternates) and diversified demand sources.

---

## Standalone checks

These checks are intentionally **not included in cluster activation logic** because they are either (a) often "single-point-of-failure" incidents where one non-pass warrants immediate attention, or (b) highly model/data-dependent (so clustering can create noise if inputs are sparse). They can still be referenced as supporting evidence in narratives.

| Check ID | Why it is standalone | Brief description |
|---|---|---|
| CV07 | Often incident-like | Payment/transaction failure rate elevated (PSP errors, fraud tooling blocks, outages). |
| R15 | High-severity leakage | Chargebacks/fraud/cancellations materially reducing captured revenue. |
| PR07 | Model-dependent | Price elasticity signal is unstable/uncertain (sensitivity estimates too noisy to drive cluster activation). |
| PR12 | Governance-style issue | Price integrity/parity anomalies across variants/channels (can create trust, support, and margin issues even alone). |
| C08 | Requires CAC/finance joins | LTV:CAC or payback period is off-target (composite health check; can be blocked by missing CAC data). |
| O09 | Often supplier/process-specific | Replenishment lead time reliability / OTIF issues (can dominate availability regardless of other signals). |

---

## Deduplication and overlap rules

Even with a "primary assignment" map (as above), overlaps happen in practice because some checks are causal bridges (e.g., shipping cost shocks affect both conversion and margin; stockouts affect both revenue and retention). The point of deduplication is to keep cluster activations interpretable and avoid double-counting the same underlying failure mode.

Use these rules when your implementation allows a check to be referenced in more than one place:

1. **Single primary owner.** A check can appear in multiple clusters as **supporting evidence**, but it should have exactly one **Primary Cluster** that "owns" it for activation counting. Activation counts should be computed on **unique check IDs** within a cluster (warn/fail counted once per ID), and cross-cluster rollups should avoid adding the same non-pass ID multiple times when computing an overall "health score."

2. **Closest actionable root cause.** If two clusters could plausibly own a check, assign ownership based on **closest actionable root cause** (not the symptom). Concretely: conversion-step errors belong to Cluster A even if they reduce revenue; discount intensity belongs to Cluster B even if it increases returns; stockouts belong to Cluster D even if they depress retention. This mirrors how root-cause workstreams are typically staffed and sequenced.

3. **Worst-check selection.** When selecting `{worst_check}` in hypothesis templates, pick the non-pass check with the highest severity using a consistent scoring rule (example: Fail = 2 points, Warn = 1 point; tie-break by estimated $ impact such as lost gross profit or lost contribution margin). This keeps narratives stable across quarters and ensures the "headline" maps to the biggest lever.

---

## Priority ordering when multiple clusters activate simultaneously

When several clusters activate at once, prioritize based on (a) **constraint logic** (what blocks revenue immediately), (b) **profit leakage magnitude**, and (c) **compounding effects** (retention and concentration). The ordering below reflects commonly observed ecommerce failure chaining: availability and checkout friction can destroy conversion immediately, while price/promo and returns can destroy profit even when conversion is stable, and retention/concentration determine whether growth compounds or stays fragile.

1. **D -- Inventory Distortion and Availability Drag** -- If you can't fulfill demand, you lose revenue now and often harm loyalty; inventory distortion is also widely framed as a major industry-scale cost driver.
2. **A -- Purchase Funnel Breakdown** -- Checkout and funnel friction are immediate conversion killers, with well-documented abandonment drivers (cost shock, trust, complexity, errors).
3. **E -- Returns, Trust, and Post-Purchase Friction** -- Returns can erase gross-to-net and degrade repeat behavior; reported industry costs are large enough that this cluster can dominate P&L impact.
4. **B -- Promo-Led Growth and Margin Compression** -- Discount dependency can create a treadmill where revenue requires margin sacrifice; analytics-led promo design is repeatedly cited as a profit lever.
5. **C -- Assortment and Merchandising Misfit** -- Catalog structure, tiering, and cross-sell effectiveness influence both conversion and margin, but often after the "stop the bleeding" issues above are stabilized.
6. **F -- Retention and LTV Engine Weakness** -- Retention is a compounding engine; when it fails you can still grow, but only by continually paying for new customers, and profit leverage from retention can be large.
7. **G -- Revenue Concentration and Growth Sustainability Risk** -- Concentration is often the "second-order" strategic risk: the business may be growing today, but is fragile to shocks in a dominant channel/SKU/customer segment.

---

## Practical implementation notes

Implement clusters as deterministic rules over your existing check statuses: each check emits `{pass, warn, fail, n/a}`. Activate a cluster when its rule is met, then generate the executive narrative using the template placeholders (`{n}`, `{worst_check}`, etc.). This mirrors how many audit/benchmarking systems translate noisy metric suites into stable "themes."

To keep clusters robust across seasonality and promo calendars, consider evaluating checks on two windows:

- **Short window** (e.g., trailing 28 days) for incident detection.
- **Long window** (e.g., trailing 90 days) for structural confirmation.

Treat a finding as "structural" only when the cluster activates in both windows or repeatedly across weeks. This reduces false positives from one-off campaigns while still surfacing persistent issues.
