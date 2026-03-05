# Check Implementation Summary

<!-- Updated: 2026-03-04 | Source: DR2 -->

Quick-reference table for 43 checks with implementation pseudocode in the category reference files.
For full pseudocode and thresholds, see the corresponding category file.

## Summary Table

| Check | Metric | Data Requirements | Thresholds (Pass / Warn / Fail) | N/A Condition | Priority | Reference File |
|-------|--------|-------------------|-------------------------------|---------------|----------|----------------|
| R02 | Seasonality detection | orders: `order_ts`, `net_revenue` (≥18 mo) | strength <0.30 / 0.30–0.60 / ≥0.60 | <18 mo data | High | `revenue-decomposition.md` |
| R06 | Day/hour patterns | orders: `order_ts`, `net_revenue` | DOW peak ≤1.5 / 1.5–2.5 / >2.5 | <8 weeks or TZ unknown | High | `revenue-decomposition.md` |
| R09 | Geographic concentration | orders: `shipping_region`, `net_revenue` | top-geo ≤70% & HHI <2500 / 70–85% / ≥85% | geo missing >20% | Medium | `revenue-decomposition.md` |
| R11 | Return rate | returns + orders | ≤15% / 15–25% / >25% | no returns data | Medium | `revenue-decomposition.md` |
| R12 | Gross margin trend | order_items: revenue, cogs | slope ≥−0.2pp/mo / −0.2 to −0.5 / <−0.5 | COGS missing >20% | Medium | `revenue-decomposition.md` |
| R15 | Forecast accuracy (WMAPE) | forecasts + actuals | WMAPE ≤20% / 20–35% / >35% | no forecasts | Low | `revenue-decomposition.md` |
| CV02 | Mobile vs desktop CVR gap | sessions + purchases by device | ratio ≥0.70 / 0.50–0.70 / <0.50 | <1k sessions/device | High | `conversion-funnel.md` |
| CV07 | Channel-level CVR | sessions: `channel_group` + purchases | no major ch <0.6× / 0.4–0.6× / <0.4× | channel attribution missing | Medium | `conversion-funnel.md` |
| CV08 | Landing page CVR | sessions: `landing_page_url` + purchases | ≥70% of top LPs ≥0.75× / 50–70% / <50% | LP data unavailable | High | `conversion-funnel.md` |
| CV09 | Search-to-product-view rate | events: search + view_item | ≥40% / 25–40% / <25% | search not tracked | Medium | `conversion-funnel.md` |
| CV10 | PDP add-to-cart rate | events: view_item + add_to_cart | ≥6% / 4–6% / <4% | events missing | High | `conversion-funnel.md` |
| CV11 | Checkout step drop-off | events: checkout steps | completion ≥30% / 20–30% / <20% | step events missing | High | `conversion-funnel.md` |
| P02 | C-rank inventory cost | inventory + unit_cost + ABC rank | ≤20% / 20–35% / >35% | inventory value missing | Medium | `product-analysis.md` |
| P03 | New product launch velocity | products: `launch_ts` + sales | median ≤7d / 7–14d / >14d | <20 new SKUs | Medium | `product-analysis.md` |
| P04 | Product reviews health | reviews + sales | ≥70% reviewed / 40–70% / <40% | no reviews | Medium | `product-analysis.md` |
| P08 | Category cannibalization | category sales + launches | ≤30% / 30–60% / >60% | no launch events | Low | `product-analysis.md` |
| P09 | Deadstock 180d | inventory + 180d sales | ≤5% / 5–10% / >10% | inventory missing | High | `product-analysis.md` |
| P12 | Seasonal stock timing | seasonal SKUs + in-stock | ≥97% / 92–97% / <92% | no seasonal classification | Low | `product-analysis.md` |
| P13 | Product content richness | product content fields + sales | ≥80% / 50–80% / <50% | content fields absent | Medium | `product-analysis.md` |
| P14 | Category gross margin | order_items: category, revenue, cogs | no cat >5pp below / 5–10pp / >10pp below | COGS missing | Medium | `product-analysis.md` |
| P15 | A-rank stockout frequency | inventory availability + ABC rank | rev-wt in-stock ≥98% / 95–98% / <95% | no availability snapshots | Medium | `product-analysis.md` |
| P16 | Bundle effectiveness | bundle orders + items | attach ≥5% & ΔGP≥0 / 2–5% / <2% | no bundles | Medium | `product-analysis.md` |
| P17 | Rating-sales correlation | ratings + sales | rho ≥0.2 / −0.2 to 0.2 / ≤−0.2 | few rated SKUs | Low | `product-analysis.md` |
| P18 | New product intro frequency | products: `created_ts` | 2–10% / 1–2% or 10–20% / <1% or >20% | no created_ts | High | `product-analysis.md` |
| P20 | Consumable repurchase rate | orders + consumable flag | ≥30% / 15–30% / <15% | consumables not tagged | Medium | `product-analysis.md` |
| O02 | A-rank days of stock | inventory + demand rate | median 21–60d / 14–21 or 60–90 / <14 or >90 | inventory/sales missing | Medium | `inventory-analysis.md` |
| O07 | Safety stock adequacy | demand var + lead time + CSL | ≥90% of rec / 70–90% / <70% | lead time missing | Low | `inventory-analysis.md` |
| O08 | Lead time accuracy | POs + receipts | median APE ≤10% / 10–20% / >20% | no PO/receipt data | Low | `inventory-analysis.md` |
| O09 | Seasonal stockout prevention | seasonal items + in-stock + peaks | ≤1% OOS / 1–3% / >3% | no seasonal tagging | Low | `inventory-analysis.md` |
| C02 | 3-month retention | orders + customers | ≥15% / 10–15% / <10% | cohort not aged 90d | High | `cohort-analysis.md` |
| C03 | 12-month retention | orders + customers | ≥20% / 15–20% / <15% | cohort not aged 365d | High | `cohort-analysis.md` |
| C04 | Cohort retention trend | cohort retention series | decline <1pp / 1–3pp / >3pp | <6 cohorts | High | `cohort-analysis.md` |
| C06 | 1-year LTV estimate | orders + cogs + cohort age | coverage ≥80% / 50–80% / <50% | immature cohorts | Medium | `cohort-analysis.md` |
| C07 | LTV cohort comparison | LTV by cohort | ratio ≥0.90 / 0.75–0.90 / <0.75 | cohorts not matured | Medium | `cohort-analysis.md` |
| C13 | LTV/CAC ratio | LTV + CAC by cohort | ≥3.0 / 1.5–3.0 / <1.5 | CAC missing | Medium | `cohort-analysis.md` |
| C14 | Sale-month cohort quality | cohorts + discount flags | ratio ≥0.90 / 0.75–0.90 / <0.75 | cannot ID sale cohorts | Medium | `cohort-analysis.md` |
| C15 | High-risk churn share | customer order recency | ≤35% / 35–50% / >50% | too little history | High | `cohort-analysis.md` |
| PR04 | Discount vs non-discount LTV | cohort + first-order discount | ratio ≥0.90 / 0.75–0.90 / <0.75 | missing discount/LTV | Medium | `pricing-analysis.md` |
| PR05 | Coupon code ROI | orders + coupon + campaign cost | ROI ≥1.0 / 0–1.0 / <0 | incrementality unmeasurable | Low | `pricing-analysis.md` |
| PR06 | Price change sensitivity | price history + demand | \|e\| ≤1 / 1–2 / >2 | insufficient price changes | Low | `pricing-analysis.md` |
| PR10 | Competitor price gap | competitor price feed | \|gap\| ≤5% / 5–15% / >15% | no competitor data | Low | `pricing-analysis.md` |
| PR11 | Price tier CVR | price + sessions/purchases | no tier <0.6× / 0.4–0.6× / <0.4× | tiering not possible | Medium | `pricing-analysis.md` |
| PR12 | Subscription discount appropriateness | subscription + margin data | ΔGP≥0 & disc ≤15% / slight neg / ΔGP≤−10% | no subscription data | Low | `pricing-analysis.md` |

## Cross-References

- Full pseudocode for each check: see the Reference File column above
- Finding clusters that group these checks: [`finding-clusters.md`](finding-clusters.md)
- Revenue impact formulas: [`impact-formulas.md`](impact-formulas.md)
- Vertical-specific threshold overrides: [`vertical-benchmarks.md`](vertical-benchmarks.md)
