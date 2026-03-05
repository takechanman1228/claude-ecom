# Pricing Analysis Checklist (PR01-PR12)

<!-- Updated: 2026-03-04, v0.4 -->

## Framework

Discount dependency × Price elasticity × Margin analysis × Threshold optimisation

## Check Definitions

### PR01 — Average Discount Rate

- **Severity:** High (3.0×)
- **PASS:** < 15%
- **WARNING:** 15-25%
- **FAIL:** > 25%
- **Calculation:** Σ(discount) / Σ(amount + discount)

### PR02 — Discounted Order Ratio

- **Severity:** High (3.0×)
- **PASS:** < 40% of orders have a discount applied
- **WARNING:** 40-60%
- **FAIL:** > 60%
- **Impact:** High ratios indicate price expectation conditioning

### PR03 — Discount Depth Trend

- **Severity:** Critical (5.0×)
- **Question:** Are discounts getting deeper over time?
- **PASS:** Monthly avg discount rate increase < 1pt
- **WARNING:** 1-2pt increase per month
- **FAIL:** > 2pt increase per month
- **Impact:** Escalating discounts erode margins and customer expectations

### PR04 — Discount vs Non-Discount Customer LTV

- **Severity:** High (3.0×)
- **PASS:** Discount-acquired customer LTV ≥ 70% of full-price customer LTV
- **WARNING:** 50-70%
- **FAIL:** < 50%
- **Impact:** Low ratio suggests discounts attract low-value customers

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Flag whether a customer used a discount on their first order, then compute 365-day LTV (gross profit).

**Pseudocode:**
```python
customers["first_order_discounted"] = first_order.discount_amount > 0

ltv_disc = ltv365_gp[customers.first_order_discounted].mean()
ltv_nodisc = ltv365_gp[~customers.first_order_discounted].mean()

ratio = ltv_disc / max(ltv_nodisc, 1e-9)
```

**Thresholds:**
- **PASS:** `ratio >= 0.90`
- **WARNING:** `0.75 <= ratio < 0.90`
- **FAIL:** `ratio < 0.75`

**N/A condition:** Missing first-order discount field or missing LTV/COGS data.

**Priority:** Medium

### PR05 — Coupon Code ROI

- **Severity:** Medium (1.5×)
- **PASS:** All coupon codes have ROI > 1.0
- **WARNING:** Some codes < 1.0
- **FAIL:** Majority of codes < 1.0
- **Calculation:** incremental_revenue / discount_cost per code

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Coupon code per order (`coupon_code`), discount cost, and campaign costs.

**Pseudocode:**
```python
# best: use holdout or geo split; fallback: baseline = matched non-coupon days/users
incr_revenue = revenue_with_coupon - baseline_revenue
incr_gross_profit = incr_revenue * gross_margin_assumption

discount_cost = sum(discount_amount on coupon orders)
campaign_cost = marketing_cost_for_coupon

roi = (incr_gross_profit - discount_cost - campaign_cost) / max(discount_cost + campaign_cost, 1e-9)
```

**Thresholds:**
- **PASS:** `roi >= 1.0` (>= $1 incremental gross profit per $1 invested)
- **WARNING:** `0 <= roi < 1.0`
- **FAIL:** `roi < 0` (coupon is destroying incremental profit)

**N/A condition:** No way to estimate incrementality (no holdout, no baseline strategy) or no campaign cost tagging.

**Priority:** Low

### PR06 — Price Change Sensitivity

- **Severity:** Medium (1.5×)
- **PASS:** Price elasticity measured for top products
- **WARNING:** Partial measurement
- **FAIL:** No elasticity data available
- **Note:** Informational — guides pricing strategy

#### Implementation
<!-- v0.4: added per DR2 research -->

**Data requirements:** SKU price history and units sold (plus traffic controls if possible).

**Pseudocode:**
```python
# Event-based elasticity around price changes (simplified)
for each sku with >=2 price points:
    q1 = avg_units_per_day(pre_window)
    q2 = avg_units_per_day(post_window)
    p1 = price_pre
    p2 = price_post
    elasticity = ((q2 - q1)/q1) / ((p2 - p1)/p1)
```

**Thresholds:**
- **PASS:** For top SKUs/categories, median `|elasticity| <= 1`
- **WARNING:** `1 < |elasticity| <= 2`
- **FAIL:** `|elasticity| > 2` (high price sensitivity)

**N/A condition:** Insufficient price change events (e.g., < 3 meaningful changes), or heavy promo/traffic confounding without controls.

**Priority:** Low

### PR07 — Category Margin Variance

- **Severity:** Medium (1.5×)
- **PASS:** No category with negative gross margin
- **WARNING:** 1 category at break-even
- **FAIL:** Any category with negative margin
- **Data:** Requires `cost` column

### PR08 — Free-Shipping Threshold Effectiveness

- **Severity:** High (3.0×)
- **Question:** Does the threshold drive AOV increase?
- **PASS:** > 10% AOV bump for orders near threshold
- **WARNING:** 5-10% bump
- **FAIL:** < 5% bump (threshold too high or not visible)
- **Calculation:** Compare AOV of orders within 80-100% of threshold vs below

### PR09 — Sale Period Gross Margin

- **Severity:** High (3.0×)
- **PASS:** Gross margin > 15% during sale periods
- **WARNING:** 10-15%
- **FAIL:** < 10%

### PR10 — Competitor Price Gap

- **Severity:** Medium (1.5×)
- **PASS:** Within ±20% of competitor pricing
- **WARNING:** ±20-30%
- **FAIL:** > ±30% gap
- **Note:** Requires competitor data; N/A if unavailable

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Competitor price feed mapped to your SKUs, normalized currency.

**Pseudocode:**
```python
comp = competitor_prices_latest.groupby("sku")["competitor_price"].median().rename("comp_price")
you = your_prices_latest.set_index("sku")["price"].rename("your_price")

x = you.to_frame().join(comp, how="inner")
x["gap"] = (x.your_price - x.comp_price) / x.comp_price

# focus on top SKUs by revenue
top = x.loc[top_skus]
median_abs_gap = top.gap.abs().median()
share_big_over = (top.gap > 0.10).mean()
```

**Thresholds:**
- **PASS:** `median_abs_gap <= 5%`
- **WARNING:** `5% < median_abs_gap <= 15%`
- **FAIL:** `median_abs_gap > 15%`

**N/A condition:** No competitor pricing data.

**Priority:** Low

### PR11 — Price Tier CVR

- **Severity:** Medium (1.5×)
- **PASS:** All price tiers have CVR > 0.5%
- **WARNING:** 1 tier below
- **FAIL:** Multiple tiers below
- **Data:** Requires session data for true CVR

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Price per SKU, category, and SKU-level conversion proxy (PDP-to-purchase or session-to-purchase).

**Pseudocode:**
```python
# assign price percentile within category
sku_cat = sku_metrics.merge(products[["sku","category_id","price"]], on="sku")
sku_cat["price_pctile"] = sku_cat.groupby("category_id")["price"].rank(pct=True)

sku_cat["tier"] = pd.cut(sku_cat.price_pctile, [0,0.25,0.75,1.0], labels=["low","mid","high"])

tier = sku_cat.groupby(["category_id","tier"]).agg(
    sessions=("sessions","sum"),
    purchases=("purchases","sum")
)
tier["cvr"] = tier.purchases / tier.sessions
tier["rel_to_cat_med"] = tier.cvr / tier.groupby("category_id")["cvr"].transform("median")
```

**Thresholds:**
- **PASS:** No tier with >= 20% of category traffic has `rel_to_cat_med < 0.60`
- **WARNING:** Any such tier has `0.40-0.60`
- **FAIL:** Any such tier has `< 0.40`

**N/A condition:** Cannot compute SKU-level sessions/purchases by tier.

**Priority:** Medium

### PR12 — Subscription Discount Appropriateness

- **Severity:** Medium (1.5×)
- **PASS:** Subscription discount < 20%
- **WARNING:** 20-30%
- **FAIL:** > 30%
- **Note:** Only applicable to stores with subscriptions; N/A otherwise

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Subscription discount %, subscription order behavior (renewals/retention), and per-order gross margin.

**Pseudocode:**
```python
# Compare subscription vs one-time gross profit over a fixed horizon (e.g., 180d or 365d)
gp_sub = gross_profit_per_subscriber_over_horizon.mean()
gp_one = gross_profit_per_similar_one_time_customer_over_horizon.mean()

delta_gp = gp_sub - gp_one
discount_pct = subscription.discount_pct  # e.g., 0.05, 0.10, 0.15
```

**Thresholds:**
- **PASS:** `delta_gp >= 0` and `discount_pct <= 15%`
- **WARNING:** `delta_gp` slightly negative (> -10% baseline) or `15% < discount_pct <= 20%`
- **FAIL:** `delta_gp <= -10%` or `discount_pct > 20%`

**N/A condition:** No subscription program data, or cannot separate subscription vs one-time customers.

**Priority:** Low

## Key Metrics

### Price Elasticity (Simple Estimate)
```
elasticity = ΔQ% / ΔP%
```
- Elastic (|e| > 1): price cuts increase total revenue
- Inelastic (|e| < 1): price increases improve revenue
- Unit elastic (|e| = 1): revenue-neutral

### Discount ROI
```
ROI = (Incremental Revenue - Discount Cost) / Discount Cost
```

### Free-Shipping Threshold Suggestion
```
Suggested threshold = Median AOV × 1.2 (rounded to nearest 100)
```
