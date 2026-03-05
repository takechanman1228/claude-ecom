# EC Health Check — Revenue Impact Calculation Formulas

<!-- Updated: 2026-03-04 | Source: DR4 -->

## Quick Reference Table

| Check ID | Metric | Formula (per period) | Typical Improvement | Annualised Impact Example ($10M revenue) |
|----------|--------|---------------------|---------------------|------------------------------------------|
| CV01 | CVR gap vs benchmark | `(Benchmark_CVR - Actual_CVR) / Actual_CVR * Revenue` | +0.5–1.0 pp | $200K–$400K |
| CV05 | Cart abandonment | `Revenue * (Improvement_pp / 100) * (1 - Current_Abandon_Rate/100)^-1` | -3–5 pp | $100K–$250K |
| CV06 | Checkout abandonment | `Checkout_Starts * Improvement_pp/100 * AOV` | -2–4 pp | $80K–$200K |
| R10 | Return rate | `Orders * Reduction_pp/100 * Cost_Per_Return` | -1–3 pp | $50K–$150K |
| C01 | Returning customer ratio (F2) | `New_Customers * F2_Improvement_pp/100 * LTV_Repeat` | +3–5 pp | $150K–$500K |
| PR01 | Discount rate | `Revenue * Reduction_pp / 100` | -1–3 pp | $100K–$300K |
| R05 | Repeat revenue share | `Total_Revenue * Improvement_pp/100 * (1 - Churn_Volatility)` | +3–5 pp | $75K–$200K |
| R08 | Avg discount rate | `Discounted_Revenue * Reduction_pp / 100` | -1–2 pp | $50K–$150K |
| R14 | Gross margin | `Revenue * Improvement_pp / 100` | +1–3 pp | $100K–$300K |

**Note:** "pp" = percentage points. All examples assume a $10M annual revenue baseline. Actual impact varies by category, AOV, and traffic volume.

---

## CV01 — Conversion Rate (CVR) Gap Analysis

### What it measures
The gap between actual site CVR and the industry median benchmark (default: 2.5%).

### Calculation Formula

```
Lost_Revenue = Sessions * (Benchmark_CVR - Actual_CVR) * AOV

Relative_Gap = (Benchmark_CVR - Actual_CVR) / Benchmark_CVR * 100
```

**Worked example:**
- Monthly sessions: 500,000
- Actual CVR: 1.8%
- Benchmark CVR: 2.5%
- AOV: $75
- Lost revenue = 500,000 * (0.025 - 0.018) * $75 = **$262,500/month** ($3.15M/year)

### Industry Benchmarks (2025)

| Industry | Median CVR | Top Quartile |
|----------|-----------|-------------|
| Food & Beverage | 4.5–6.0% | 7.0%+ |
| Beauty & Personal Care | 4.5–5.7% | 6.5%+ |
| Multi-brand Retail | 4.5–4.9% | 5.5%+ |
| Consumer Electronics | 2.8–3.5% | 4.0%+ |
| Fashion & Apparel | 2.8–3.4% | 4.0%+ |
| Consumer Goods | 3.0–3.4% | 4.0%+ |
| Pet Care | 2.5–3.1% | 3.5%+ |
| Home & Furniture | 1.2–1.4% | 2.0%+ |
| Luxury & Jewelry | 0.7–1.2% | 1.5%+ |

**Global cross-industry median: 2.5–3.0%** (session-based).

### Typical Improvement Rates
- Checkout UX optimisation: +0.3–0.5 pp (Baymard Institute)
- Site speed improvement (1s faster): +7% relative CVR lift
- Mobile UX overhaul: +0.5–1.0 pp on mobile specifically
- A/B testing programme (6 months): +10–25% relative CVR lift

### Sources
- Dynamic Yield Commerce Benchmarks (2025) — industry CVR by sector
- Red Stag Fulfillment — "Average Ecommerce Conversion Rate" (2026)
- Smart Insights — "E-commerce conversion rate benchmarks" (2025 update)
- Baymard Institute — 35.26% relative conversion lift from checkout UX fixes

---

## CV05 — Cart Abandonment Rate

### What it measures
The percentage of shoppers who add items to cart but do not complete purchase.

### Calculation Formula

```
Cart_Abandon_Rate = 1 - (Completed_Purchases / Cart_Sessions) * 100

Recoverable_Revenue = Cart_Sessions * Abandon_Rate * AOV * Recovery_Rate

Revenue_Per_1pp_Improvement = Cart_Sessions * 0.01 * AOV
```

**Worked example (per 1 pp improvement):**
- Monthly cart sessions: 100,000
- Current abandon rate: 72%
- AOV: $80
- Revenue per 1 pp reduction = 100,000 * 0.01 * $80 = **$80,000/month**

### Industry Benchmarks (2025)

| Segment | Cart Abandonment Rate |
|---------|----------------------|
| Global average (Baymard, 50 studies) | 70.2% |
| Desktop | 68.1% |
| Mobile | 79.4% |
| B2B ecommerce | 57% |
| Digital products & software | 55% |
| Grocery | 60% |
| Health & wellness | 69% |
| Electronics | 70% |
| Beauty & cosmetics | 72% |
| Fashion & apparel | 76% |
| Luxury goods | 78% |
| Home & furniture | 81% |
| Automotive parts | 82% |

### Top Abandonment Reasons
1. Extra costs (shipping, tax, fees) — 48%
2. Required account creation — 26%
3. Too long / complicated checkout — 22%
4. Could not see total order cost upfront — 21%
5. Delivery too slow — 18%

### Typical Improvement Rates
- Cart recovery emails (3-email sequence): recover 5–10% of abandoned carts
- Cart recovery email open rate: 45%, CTR: 21%, conversion: 10%
- Guest checkout option: -3 to -5 pp abandonment
- Transparent pricing (no surprise fees): -5 to -8 pp
- Simplified checkout (fewer form fields): -2 to -4 pp
- Live chat: -9% relative reduction
- Saving carts across devices: -20% relative reduction
- **Baymard estimate:** better checkout design alone can yield 35% relative conversion rate increase, translating to ~$260B recoverable globally

### Sources
- Baymard Institute — 50 Cart Abandonment Rate Statistics (2026)
- Contentsquare — 15 Insightful Stats on Shopping Cart Abandonment (2025)
- SaleCycle, Barilliance, Kibo Commerce — historical abandon rate series
- MarketingLTB — Cart Abandonment Rate Statistics 2025

---

## CV06 — Checkout Abandonment Rate

### What it measures
The percentage of users who begin checkout but do not complete payment. This is a subset of cart abandonment — it isolates the checkout-specific friction.

### Calculation Formula

```
Checkout_Abandon_Rate = 1 - (Completed_Orders / Checkout_Starts) * 100

Revenue_Per_1pp_Improvement = Checkout_Starts * 0.01 * AOV

Annualised_Impact = Revenue_Per_1pp_Improvement * 12
```

**Worked example (per 1 pp improvement):**
- Monthly checkout starts: 40,000
- Current checkout abandon rate: 25%
- AOV: $85
- Revenue per 1 pp = 40,000 * 0.01 * $85 = **$34,000/month** ($408K/year)

### Industry Benchmarks
- Average checkout abandonment rate: 20–30% of those who initiate checkout
- Checkout abandonment is roughly 25–40% of all cart abandonment (the rest abandon before starting checkout)
- Baymard Institute finding: average site has 39 form fields at checkout; optimised sites have 12–14, yielding 20–60% reduction in checkout friction

### Typical Improvement Rates
- Reducing checkout steps from 5 to 2–3: -3 to -5 pp
- Adding express payment (Apple Pay, Google Pay, PayPal Express): -2 to -4 pp
- Auto-fill and address lookup: -1 to -2 pp
- Progress indicator in checkout: -1 pp
- Trust badges and security signals: -2 to -3 pp (absence increases abandonment by 18%)

### Sources
- Baymard Institute — Checkout Usability studies (2024–2025)
- Contentsquare Guide to Cart Abandonment (2025)
- SellersCommerce — Shopping Cart Abandonment Statistics (2025)

---

## R10 — Return Rate

### What it measures
The percentage of orders returned. Higher return rates erode margin through reverse logistics costs and unsellable inventory.

### Calculation Formula

```
Return_Rate = Returned_Orders / Total_Orders * 100

Cost_Per_Return = Shipping_Back + Processing + Restocking + Unsellable_Loss
                  (typical: $15–$25 per return)

Savings_Per_1pp_Reduction = Total_Orders * 0.01 * Cost_Per_Return

Net_Impact = Savings_Per_1pp + (Total_Orders * 0.01 * AOV * Resale_Rate)
```

**Worked example (per 1 pp reduction):**
- Annual orders: 150,000
- Cost per return: $18
- AOV: $75
- Direct savings = 150,000 * 0.01 * $18 = **$27,000/year**
- Recovered revenue (assuming 75% resellable at full price) = 150,000 * 0.01 * $75 * 0.75 = **$84,375/year**
- **Total impact per 1 pp: ~$111K/year**

### Industry Benchmarks (2025)

| Category | Return Rate |
|----------|------------|
| Overall ecommerce (US) | 16.9–20.5% |
| Brick-and-mortar retail | 8.9% |
| Clothing & apparel | 25–26% |
| Footwear | 20–22% |
| Electronics | 12–15% |
| Auto parts | 19.4% |
| Home & furniture | 10–14% |
| Beauty & cosmetics | 4–6% |
| Food & beverage | 2–4% |

### Cost Breakdown Per Return
| Component | Cost Range |
|-----------|-----------|
| Return shipping | $8–$12 |
| Processing & inspection | $5–$8 |
| Restocking & storage | $2–$4 |
| Unsellable percentage | 10–25% of returns |
| **Total direct cost** | **$15–$25** |
| As percentage of item price | ~59% of a $50 item |

### Typical Improvement Rates
- Better product descriptions + sizing guides: -2 to -5 pp
- High-quality product images / 360-degree views: -1 to -2 pp
- Customer reviews with fit details: -1 to -2 pp
- Stricter return policy (restocking fees): -3 to -5 pp (trade-off: may reduce CVR)
- AI-powered size recommendation: -2 to -4 pp for apparel
- Brands with sophisticated return management: 34% lower rates vs industry average

### Sources
- NRF — 2025 Retail Returns Landscape (19.3% online returns benchmark)
- Appriss Retail + Deloitte — 2024 Consumer Returns Report (13.21% overall retail)
- McKinsey — Improving Returns Management for Apparel (25% apparel benchmark)
- Outvio — eCommerce Return Rate Statistics 2025
- Rocket Returns — Ecommerce Return Rates 2025 Industry Analysis

---

## C01 — Returning Customer Ratio (F2 Conversion)

### What it measures
The share of customers who make a second purchase (F2 conversion), and the broader returning customer ratio. Repeat customers drive disproportionate revenue and have dramatically higher conversion rates (60–70%) compared to new prospects (5–20%).

### Calculation Formula

```
Returning_Customer_Ratio = Repeat_Customers / Total_Customers * 100

F2_Conversion_Rate = Customers_With_2+_Orders / Total_Customers * 100

LTV_Uplift_Per_1pp_F2 = New_Customers * 0.01 * (LTV_Repeat - LTV_OneTime)

Revenue_Impact = LTV_Uplift_Per_1pp_F2 * (1 + Downstream_Acceleration)
```

**Worked example (per 1 pp F2 improvement):**
- Annual new customers: 50,000
- LTV of one-time buyer: $215
- LTV of 2+ purchase buyer: $538 (2.5x multiplier)
- Revenue uplift = 50,000 * 0.01 * ($538 - $215) = **$161,500/year**
- With downstream acceleration (F2 buyers convert to F3 at 38.8%): effective uplift is higher

### Key LTV Multipliers by Purchase Count

| Purchase Count | Relative LTV | F(n) to F(n+1) Conversion |
|---------------|-------------|--------------------------|
| 1 (one-time) | 1.0x | ~18.8% convert to F2 |
| 2 | 2.5x | ~38.8% convert to F3 |
| 3 | 3.8x | ~50%+ convert to F4 |
| 5+ | 7.3x | High retention zone |

### Industry Benchmarks

| Category | Repeat Customer Rate | Repeat Revenue Share |
|----------|---------------------|---------------------|
| Overall ecommerce | 15–30% | 25–45% |
| Consumables (top) | 39–44% | 62–67% |
| Health & supplements | 29% | 45–55% |
| Beauty & cosmetics | 25.9% | 35–45% |
| Fashion & apparel | 15–26% | 13–25% |
| Home & furniture | 14.7% | 12–18% |
| Pet supplies | 30%+ | 45–55% |
| Grocery & food delivery | 30–40%+ | 50–65% |
| Durables / high-ticket | 11–17% | 12–18% |

### Typical Improvement Rates
- Loyalty / VIP tier programme: +5–10 pp repeat rate, 15–25% annual revenue lift
- Post-purchase email sequence (3–5 emails): +3–5 pp F2 conversion
- Personalised product recommendations: +2–4 pp
- Subscription / auto-replenish models: +10–15 pp for consumables
- 5% increase in retention → 25–95% increase in profits (Bain & Company)
- Existing customers spend 67% more after 30+ months (Bain & Company)
- Probability of selling to existing customer: 60–70% vs 5–20% for new

### Sources
- BS&Co — Repeat Purchase Rate Benchmarks: 18.8% across 156K DTC customers (2026)
- BS&Co — LTV by Purchase Count: DTC Benchmarks from 162K customers
- Rivo — VIP Customer Repeat Rate Statistics (27 stats)
- Geckoboard — Repeat Customer Rate KPI (25–30% benchmark)
- Bain & Company — customer retention and LTV research

---

## PR01 — Discount Rate (Promotional Intensity)

### What it measures
The percentage of revenue sold at a discount. Excessive discounting erodes margins and trains customers to wait for promotions.

### Calculation Formula

```
Discount_Rate = Discounted_Orders_Revenue / Total_Revenue * 100

Avg_Discount_Depth = Total_Discount_Amount / Discounted_Orders_Revenue * 100

Margin_Impact_Per_1pp_Reduction = Revenue * 0.01
  (direct: each 1 pp less discounting = 1 pp more revenue retained)

Profit_Multiplier = 1pp discount reduction → 2-3 pp net profit improvement
  (because discount savings flow directly to bottom line)
```

**Worked example (per 1 pp reduction in discount rate):**
- Annual revenue: $10M
- Current discount rate: 22% of revenue sold at discount
- Average discount depth: 18%
- Revenue recovered per 1 pp reduction = $10M * 0.01 = **$100,000/year**
- Net profit impact (at 2.5x multiplier) = **$250,000/year**

### Industry Benchmarks

| Metric | Benchmark |
|--------|-----------|
| Typical ecommerce discount rate | 10–30% of orders |
| Average discount depth | 15–25% off |
| Black Friday / holiday depth | 25–40% off |
| End-of-lifecycle clearance | 40–60% off |
| Luxury brands | 5–10% (to preserve brand) |
| New product introductory | 5–15% |

### Profit Impact Rules of Thumb
- A 20% discount on a 40% margin product = giving away **50% of profit** on that sale
- Every 1 pp of discount depth reduction → 2–3x that in net profit improvement
- Online shoppers use coupon codes ~38% of the time
- 93% of shoppers use a coupon or discount code at least once per year

### Typical Improvement Rates
- Tiered discounts instead of blanket: -2 to -5 pp average discount depth
- Time-limited offers vs permanent sale: -3 to -5 pp discount rate
- Personalised pricing (discount only for at-risk segments): -2 to -4 pp
- Shifting from discounts to value-adds (free shipping, gifts): -1 to -3 pp discount depth with same conversion impact
- Exit-intent targeting (discount only to abandoners): limits discount exposure to ~15–20% of traffic

### Sources
- Opensend — 7 Average Discount Rate Statistics for eCommerce (2025)
- SalesSo — Discounting Statistics in Sales: 2025 Data & Trends
- Onramp Funds — 10 Profit Margin Benchmarks for eCommerce 2025

---

## R05 — Repeat Revenue Share

### What it measures
The proportion of total revenue generated by repeat (returning) customers. Higher repeat revenue share indicates more predictable, stable revenue with lower acquisition cost dependency.

### Calculation Formula

```
Repeat_Revenue_Share = Revenue_From_Repeat_Customers / Total_Revenue * 100

Revenue_Stability_Score = Repeat_Revenue_Share * (1 - Monthly_Revenue_CV)
  where CV = coefficient of variation of monthly revenue

Impact_Per_1pp_Improvement = Total_Revenue * 0.01 * (1 - Blended_CAC_Rate)
  (repeat revenue has near-zero marginal CAC vs 15-30% for new customer revenue)
```

**Worked example (per 1 pp shift from new to repeat revenue):**
- Annual revenue: $10M
- Current repeat revenue share: 35%
- CAC as % of new customer revenue: 25%
- Effective savings = $10M * 0.01 * 0.25 = **$25,000/year in CAC savings**
- Plus: reduced revenue volatility and improved forecasting accuracy

### Industry Benchmarks

| Category | Repeat Revenue Share |
|----------|---------------------|
| Overall ecommerce | 25–45% |
| Consumables (top performers) | 62–67% |
| Consumables (mid-tier) | 55–64% |
| Fashion & apparel | 13–25% |
| Durables / high-ticket | 12–18% |
| Subscription-based | 65–80% |

### Key Insight: Over-indexing
- Consumable brands: repeat customers generate 1.5x their share of revenue (e.g., 44% of customers drive 67% of revenue)
- Fashion / durables: repeat customers generate ~1:1 their share (no over-index)
- Implication: repeat revenue improvement strategies have highest ROI for consumable categories

### Typical Improvement Rates
- Loyalty programme implementation: +5–10 pp repeat revenue share over 12 months
- Subscription model introduction (consumables): +15–25 pp
- Email lifecycle marketing (post-purchase flows): +3–5 pp
- Personalisation engine: +2–4 pp
- Healthy target: 40%+ repeat revenue share for most ecommerce

### Sources
- BS&Co — Repeat Purchase Rate Benchmarks (2026): 156K DTC customer analysis
- Finaloop — Ecommerce Profit Benchmarks (2024–2025 P&L data)
- Rivo — VIP Customer Repeat Rate Statistics

---

## R08 — Average Discount Rate (Margin Erosion)

### What it measures
The average discount percentage applied across all discounted transactions. Unlike PR01 (which measures how often discounts occur), R08 measures how deep discounts are when they are applied.

### Calculation Formula

```
Avg_Discount_Rate = Total_Discount_Amount / Gross_Revenue_Before_Discounts * 100

Margin_Recovery_Per_1pp = Discounted_Revenue * 0.01

Effective_Margin_Impact = Margin_Recovery / (Revenue * Gross_Margin_Rate)
  (percentage of margin recovered relative to total margin pool)
```

**Worked example (per 1 pp reduction in average discount depth):**
- Annual gross revenue (before discounts): $12M
- Discounted portion: $4M (33% of revenue is discounted)
- Current average discount: 20%
- Margin recovered per 1 pp = $4M * 0.01 = **$40,000/year**
- If gross margin is 55%: this represents 0.6% of total margin pool recovered

### Benchmarks

| Discount Depth Tier | Range | Typical Context |
|---------------------|-------|-----------------|
| Light discounting | 5–10% | Loyalty perks, first-purchase incentive |
| Moderate discounting | 10–20% | Standard promotions, seasonal sales |
| Heavy discounting | 20–30% | Clearance, competitive pricing |
| Aggressive discounting | 30%+ | End-of-life, Black Friday, distressed inventory |

### Margin Erosion Math
| Gross Margin | 10% Discount Impact | 20% Discount Impact | 30% Discount Impact |
|-------------|---------------------|---------------------|---------------------|
| 30% | Gives away 33% of profit | Gives away 67% of profit | Sells at cost |
| 40% | Gives away 25% of profit | Gives away 50% of profit | Gives away 75% |
| 50% | Gives away 20% of profit | Gives away 40% of profit | Gives away 60% |
| 60% | Gives away 17% of profit | Gives away 33% of profit | Gives away 50% |

### Typical Improvement Rates
- Replacing flat discounts with tiered spend thresholds: -2 to -3 pp depth
- Gift-with-purchase instead of % off: equivalent conversion lift at 0% discount depth
- Personalised discount depth (ML-based willingness-to-pay): -3 to -5 pp
- Reducing discount frequency (fewer sale events): -1 to -2 pp average depth

### Sources
- Opensend — Average Discount Rate Statistics for eCommerce (2025)
- SalesSo — Discounting Statistics in Sales (2025)
- Finaloop — Ecommerce Profit Benchmarks: P&L metrics (2024–2025)

---

## R14 — Gross Margin

### What it measures
Gross profit as a percentage of net revenue. The fundamental measure of product-level profitability before operating expenses.

### Calculation Formula

```
Gross_Margin = (Net_Revenue - COGS) / Net_Revenue * 100

Profit_Per_1pp_Improvement = Net_Revenue * 0.01

Adjusted_Gross_Margin = Gross_Margin - (Return_Rate * Cost_Per_Return / AOV * 100)
  (accounts for return-adjusted true margin)
```

**Worked example (per 1 pp improvement):**
- Annual net revenue: $10M
- Current gross margin: 52%
- Gross profit increase per 1 pp = $10M * 0.01 = **$100,000/year**
- With 20% return rate adjustment: effective margin is ~4 pp lower than stated

### Industry Benchmarks (2025)

| Category | Gross Margin Range | Median |
|----------|-------------------|--------|
| Beauty & cosmetics | 50–70% | 60% |
| Apparel & accessories | 40–60% | 50% |
| Private label fashion | 55–65% | 60% |
| Third-party seller fashion | 25–35% | 30% |
| Home goods | 35–45% | 40% |
| Consumer electronics | 15–25% | 20% |
| Food & beverage | 30–45% | 38% |
| Pet & animal | 38–74% | 50% |
| Sporting goods | 28–66% | 43% |
| Leisure & lifestyle | 45–75% | 66% |

### Scale Benchmarks (Finaloop, 2024)
| Revenue Tier | Median Gross Margin |
|-------------|-------------------|
| 7-figure brands | 52% |
| 8-figure brands | 56% |
| Scaling threshold | ~70% (needed to break into 8 figures reliably) |

### Profitability Thresholds
| Gross Margin | Assessment |
|-------------|-----------|
| 70%+ | Strong pricing power; comfortable scaling |
| 60–70% | Solid and sustainable for most ecommerce |
| 50–60% | Operable but scaling is tight |
| Under 50% | Fragile — small cost increases erase profit |

### Typical Improvement Rates
- Supplier renegotiation: +2–5 pp
- Private label / vertical integration: +10–20 pp vs third-party
- SKU rationalisation (cut low-margin products): +2–4 pp blended margin
- Price optimisation (dynamic pricing): +1–3 pp
- Reducing return rate by 5 pp: +1–2 pp effective gross margin
- Reducing average discount depth by 3 pp: +1–2 pp gross margin
- High return rates (25–40%) cut net profits by 8–12 pp

### Sources
- Onramp Funds — 10 Profit Margin Benchmarks for eCommerce 2025
- TrueProfit — Good Gross Profit Margins for Ecom in 2026 (5,000+ stores)
- Finaloop — Ecommerce Profit Benchmarks: P&L + Performance Metrics (2024–2025)
- Amasty — What's a Good Net Profit Margin for E-commerce

---

## Cross-Metric Impact Chains

Many of these metrics are interconnected. Improving one often creates cascading effects on others.

```
CVR Improvement (CV01)
  └─> More orders at same traffic
       └─> Lower effective CAC
            └─> Better margin (R14)

Cart/Checkout Abandon Reduction (CV05/CV06)
  └─> Higher CVR (CV01)
       └─> More first-time buyers
            └─> Larger F2 conversion pool (C01)

Return Rate Reduction (R10)
  └─> Direct cost savings
       └─> Gross margin improvement (R14)
            └─> More room for strategic discounting (PR01/R08)

F2 Conversion Improvement (C01)
  └─> Higher repeat revenue share (R05)
       └─> Lower blended CAC
            └─> Revenue stability + margin improvement (R14)

Discount Reduction (PR01/R08)
  └─> Direct margin recovery (R14)
       └─> Better brand perception
            └─> Higher full-price conversion (CV01)
```

### Priority Matrix: Effort vs Impact

| Priority | Check | Typical Effort | Typical Impact | Time to Realise |
|----------|-------|---------------|----------------|-----------------|
| 1 | CV05/CV06 (abandon) | Low–Medium | High | 1–4 weeks |
| 2 | CV01 (CVR) | Medium | High | 2–8 weeks |
| 3 | C01 (F2 conversion) | Medium | Very High (LTV) | 4–12 weeks |
| 4 | PR01/R08 (discounting) | Low | Medium–High | Immediate |
| 5 | R10 (returns) | Medium–High | Medium | 4–12 weeks |
| 6 | R14 (gross margin) | High | High | 8–24 weeks |
| 7 | R05 (repeat revenue) | Medium | Medium | 8–24 weeks |

---

## Core Variables and Identities

All formulas assume "hold everything else constant" (traffic, mix, operations).

### Variable Definitions

| Symbol | Definition |
|--------|-----------|
| \(R\) | Current annual net sales (example: \(R = \$10{,}000{,}000\)) |
| \(S\) | Annual site sessions (visits) |
| \(AOV\) | Net average order value (after discounts, before returns) |
| \(CVR\) | Ecommerce conversion rate (orders / visits) |
| \(CAR\) | Cart abandonment rate |
| \(ChAR\) | Checkout abandonment rate |
| \(GM\) | Gross margin rate on net sales |
| \(RR\) | Return rate (as % of sales or orders; specify) |
| \(\epsilon\) | Price elasticity of demand (negative for most goods) |

### Revenue Identity

\[
R = S \cdot CVR \cdot AOV
\]

If you know \(R\), \(AOV\), and \(CVR\), infer sessions:

\[
S = \frac{R}{AOV \cdot CVR}
\]

**$10M store baseline:** \(R=\$10M\), \(AOV=\$100\), \(CVR_{cur}=1.09\%\), \(S \approx 9.17M\) sessions/year.

### Funnel Decomposition

\(CVR \approx ATC \cdot (1 - CAR) \cdot (1 - ChAR)\) where \(ATC\) = add-to-cart rate. **Warning:** CV01, CV05, CV06 are linked. Do not sum uplifts — model as sequential multipliers.

---

## Per-Check Impact Models

Formal models using the $10M store baseline (\(R=\$10M\), \(AOV=\$100\), \(CVR_{cur}=1.09\%\)).

### CV01 — CVR Gap (Formal)

\(\Delta R_{annual} = R_{cur}(CVR_{bench}/CVR_{cur} - 1)\)

```python
def cvr_gap_revenue_impact(annual_revenue, cvr_current, cvr_benchmark):
    return annual_revenue * (cvr_benchmark / cvr_current - 1.0)
```

**Example.** 1.09% vs 2.5% benchmark: \(\Delta R \approx \$12.94M\). **Confidence: High.** Caveat: benchmark must be category/device-matched.

### CV05 — Cart Abandonment (Formal)

Per 1pp: \(\Delta R = R_{cur} \cdot 0.01 / (1 - CAR_{cur})\). To target: \(\Delta R = R_{cur}((1-CAR_{bench})/(1-CAR_{cur}) - 1)\)

```python
def abandonment_revenue_per_pp(annual_revenue, abandonment_rate):
    return annual_revenue * 0.01 / (1.0 - abandonment_rate)

def abandonment_revenue_to_target(annual_revenue, ab_current, ab_target):
    return annual_revenue * ((1.0 - ab_target) / (1.0 - ab_current) - 1.0)
```

**Example.** CAR=63.7%: per 1pp = ~$275K/yr. To 60%: ~$1.02M/yr. **Confidence: Medium-High.** Caveat: if CAR is cart-to-purchase, it overlaps CV06.

### CV06 — Checkout Abandonment (Formal)

Per 1pp: \(\Delta R = R_{cur} \cdot 0.01 / (1 - ChAR_{cur})\)

```python
def checkout_abandonment_impact(annual_revenue, char_current, char_target=None):
    comp_cur = 1.0 - char_current
    per_pp = annual_revenue * 0.01 / comp_cur
    if char_target is None:
        return {"per_pp_revenue": per_pp}
    return {"per_pp_revenue": per_pp,
            "to_target_revenue": annual_revenue * ((1.0 - char_target) / comp_cur - 1.0)}
```

**Example.** ChAR=46.2%: per 1pp = ~$186K/yr. To 30%: ~$3.01M/yr. **Confidence: Medium.** Caveat: definition alignment critical; mobile materially higher than desktop.

### R10 — Return Rate (Formal)

\(\Delta V = R \cdot 0.01\), \(\Delta N_{ret} = \Delta V / AOV_{ret}\), \(\Delta \Pi = \Delta N_{ret}(C_{ship}+C_{proc}) + \Delta V \cdot L_{restock}\). Shortcut: \(\Delta \Pi \approx \Delta V \cdot k\) where \(k \in [0.21, 0.27]\).

```python
def returns_savings_per_pp(annual_sales, aov_return, ship_cost, proc_cost, restock_loss_rate):
    delta_value = annual_sales * 0.01
    delta_returns = delta_value / aov_return
    return delta_returns * (ship_cost + proc_cost) + delta_value * restock_loss_rate
```

**Example.** \(AOV_{ret}=\$100\), ship=$8, proc=$6, restock=10%: **~$24K per 1pp**. **Confidence: Medium.** Caveat: costs highly business-specific.

### C01 — F2 Conversion (Formal)

\(\Delta LTV_{12} = (p_{F2} \cdot u)(O_{rep} - 1) \cdot AOV_{rep}\), \(\Delta R_{annual} = N_{new} \cdot \Delta LTV_{12}\)

```python
def ltv_uplift_from_f2(p_f2, uplift_rel, o_rep, aov_repeat):
    return p_f2 * uplift_rel * (o_rep - 1.0) * aov_repeat

def annual_revenue_uplift_from_f2(new_customers, p_f2, uplift_rel, o_rep, aov_repeat):
    return new_customers * ltv_uplift_from_f2(p_f2, uplift_rel, o_rep, aov_repeat)
```

**Example.** \(N_{new}=60K\), \(p_{F2}=25\%\), 5% relative lift, \(O_{rep}=3\), \(AOV_{rep}=\$110\): \(\Delta LTV_{12}=\$2.75\), annual = **$165K**. **Confidence: Medium-Low.** Caveat: +5pp absolute vs +5% relative yields ~4x difference.

### R05 — Repeat Revenue Share (Formal)

\(\Delta R_{shift} = R(s_{tgt}-s_{cur})\), \(\text{Net savings} = (\Delta R_{shift}/AOV_{new}) \cdot (CAC - \text{retention\_cost})\)

```python
def repeat_share_shift_savings(annual_revenue, s_cur, s_tgt, aov_new, cac_new, retention_cost=0.0):
    delta_rev = annual_revenue * (s_tgt - s_cur)
    fewer_new = delta_rev / aov_new
    return {"delta_repeat_revenue": delta_rev, "fewer_new_orders": fewer_new,
            "net_savings": fewer_new * cac_new - fewer_new * retention_cost}
```

**Example.** 35% to 44%, CAC=$40, retention=$5: **$315K net savings**. **Confidence: Medium.** Caveat: constant total revenue is simplifying.

### PR01 & R08 — Discount Reduction (Formal)

\(P'=P_0(1-d+\Delta d)\), \(Q' \approx Q(1+\epsilon \cdot \Delta d/(1-d))\), \(\Delta GP = (P'-c)Q' - (P-c)Q\). Revenue quality: \(\Delta R_{\text{const vol}} = R/(1-d) \cdot \Delta d\).

```python
def discount_margin_recovery(list_price, cogs, d_current, d_reduction_pp, elasticity, annual_orders):
    p, p_new = list_price*(1-d_current), list_price*(1-d_current+d_reduction_pp)
    q_new = annual_orders * (1 + elasticity * ((p_new/p) - 1.0))
    return {"delta_revenue": p_new*q_new - p*annual_orders,
            "delta_gross_profit": (p_new-cogs)*q_new - (p-cogs)*annual_orders}
```

**Example.** \(P_0=\$125\), d=20%, c=$55, Q=100K, 1pp reduction, \(\epsilon=-1.5\): **GP +$38K** (revenue -$65K). Constant-volume: $125K. **Confidence: Medium.** Caveat: elasticity is the key unknown.

### R14 — Gross Margin (Formal)

\(\Delta GP_{\text{per 1pp}} = R \cdot 0.01\). Revenue equivalent: \(\Delta R_{needed} = 0.01 \cdot R / GM\).

```python
def gross_margin_pp_to_profit(annual_revenue, gm_pp_improvement=0.01):
    return annual_revenue * gm_pp_improvement

def revenue_growth_equivalent(annual_revenue, gm_current, profit_target):
    return profit_target / gm_current
```

**Example.** GM=40%: 1pp = $100K GP = equivalent to $250K (2.5%) revenue growth. **Confidence: High.** Caveat: GM definitions vary by what is in COGS.

---

## Cross-Metric Cascade Model

### Avoiding Double-Counting

CVR, cart abandonment, and checkout abandonment are linked funnel stages. Summing individual uplifts double-counts because improving one changes the base for others. Use **multiplicative** composition instead.

**Decomposition:** \(R = S \cdot ATC \cdot (1-CAR) \cdot (1-ChAR) \cdot AOV\)

| Check | Component affected |
|-------|--------------------|
| CV05 | \((1 - CAR)\) |
| CV06 | \((1 - ChAR)\) |
| PR01/R08 | \(AOV\) (and possibly \(ATC\) indirectly) |
| R10 | Profit via cost/value-loss; affects C01 indirectly |

### Combined Revenue Formula (No Double-Counting)

\[
R_{new} = R_{cur} \cdot \frac{1 - CAR_{new}}{1 - CAR_{cur}} \cdot \frac{1 - ChAR_{new}}{1 - ChAR_{cur}}
\]

A CVR target of 2.5% via CV05/CV06 alone is aggressive — also requires upstream ATC, traffic mix, and merchandising improvements.
