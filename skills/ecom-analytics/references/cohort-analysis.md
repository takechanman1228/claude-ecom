# Cohort Analysis Checklist (C01-C15)

<!-- Updated: 2026-03-04, v0.4 -->

## Framework

Monthly cohort retention × RFM segmentation × LTV estimation × Churn risk scoring

## Check Definitions

### C01 — F2 Conversion Rate

- **Severity:** Critical (5.0×)
- **Question:** What % of first-time buyers make a second purchase?
- **PASS:** > 25%
- **WARNING:** 15-25%
- **FAIL:** < 15%
- **Impact:** F2 is the single most important retention metric — drives LTV

### C02 — 3-Month Retention Rate

- **Severity:** High (3.0×)
- **PASS:** > 20% of cohort active at month 3
- **WARNING:** 10-20%
- **FAIL:** < 10%

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Customer first purchase date, orders by customer; cohorting by acquisition month/week.

**Pseudocode:**
```python
# Cohort by first order month
first = orders.sort_values("order_ts").groupby("customer_id").first()
first["cohort_month"] = first.order_ts.dt.to_period("M")

orders2 = orders.merge(first[["order_ts","cohort_month"]].rename(columns={"order_ts":"first_ts"}),
                       on="customer_id")
orders2["days_since_first"] = (orders2.order_ts - orders2.first_ts).dt.days

repeat_90 = orders2.query("days_since_first > 0 and days_since_first <= 90") \
                  .groupby("customer_id").size()

cohort = first.groupby("cohort_month").size().rename("cohort_size")
ret90 = repeat_90.reset_index().merge(first[["cohort_month"]], on="customer_id") \
                 .groupby("cohort_month").customer_id.nunique() / cohort
```

**Thresholds:**
- **PASS:** `ret90 >= 15%` (default; override by vertical)
- **WARNING:** `10% <= ret90 < 15%`
- **FAIL:** `ret90 < 10%`

**N/A condition:** Cohorts not aged 90 days (e.g., last 3 months).

**Priority:** High

### C03 — 12-Month Retention Rate

- **Severity:** High (3.0×)
- **PASS:** > 10% of cohort active at month 12
- **WARNING:** 5-10%
- **FAIL:** < 5%
- **Note:** Requires 12+ months of data

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Same as C02, but with 12-month aging.

**Pseudocode:**
```python
ret365 = customers_with_second_order_within(365) / cohort_size
```

**Thresholds:**
- **PASS:** `ret365 >= 20%` (default; override by vertical)
- **WARNING:** `15% <= ret365 < 20%`
- **FAIL:** `ret365 < 15%`

**N/A condition:** Cohorts not aged 365 days.

**Priority:** High

### C04 — Cohort Retention Trend

- **Severity:** High (3.0×)
- **Question:** Are newer cohorts retaining better or worse?
- **PASS:** Recent cohorts equal or better than historical average
- **WARNING:** 5-15% decline
- **FAIL:** > 15% decline vs historical

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** At least 6 cohorts worth of retention (90-day and/or 365-day).

**Pseudocode:**
```python
# use last 6 completed cohorts
y = ret90_series.tail(6).values  # or ret365
slope_pp_per_cohort = linregress(range(len(y)), y).slope * 100
drop_pp = (y[-1] - y[0]) * 100
```

**Thresholds:**
- **PASS:** Stable or improving, or decline < 1pp over 6 cohorts
- **WARNING:** Decline 1-3pp over 6 cohorts
- **FAIL:** Decline > 3pp over 6 cohorts

**N/A condition:** < 6 completed cohorts.

**Priority:** High

### C05 — Average Purchase Interval

- **Severity:** Medium (1.5×)
- **PASS:** Within ±30% of industry benchmark
- **WARNING:** 30-50% deviation
- **FAIL:** > 50% deviation
- **Benchmarks:** Beauty 45-60d, Food 14-30d, Fashion 60-90d

### C06 — 1-Year LTV Estimate

- **Severity:** Critical (5.0×)
- **PASS:** LTV > 3× CAC
- **WARNING:** 2-3× CAC
- **FAIL:** < 2× CAC
- **Note:** If CAC is unknown, compare LTV to AOV (healthy: LTV > 2× AOV)

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Orders for 365-day windows + COGS to compute gross profit.

**Pseudocode:**
```python
# Historic 365-day gross profit LTV per acquisition cohort
orders_gp = orders.assign(gross_profit=lambda d: d.net_revenue - d.cogs)  # simplified
ltv365 = gp_in_first_365_days_per_customer.mean()

coverage = pct_of_customers_in_analysis_acquired_at_least_365d_ago
```

**Thresholds:**
- **PASS:** `coverage >= 80%` and `ltv365 > 0`
- **WARNING:** `50% <= coverage < 80%` (estimate is partial/unstable)
- **FAIL:** `coverage < 50%` or `ltv365 <= 0`

**N/A condition:** No COGS (cannot compute gross profit LTV) or no cohorts aged 365 days.

**Priority:** Medium

### C07 — LTV Cohort Comparison

- **Severity:** High (3.0×)
- **PASS:** Recent cohort LTV ≥ 80% of historical average
- **WARNING:** 60-80%
- **FAIL:** < 60%

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** LTV by cohort (from C06).

**Pseudocode:**
```python
ratio = ltv365_recent_cohorts.mean() / ltv365_prior_cohorts.mean()
```

**Thresholds:**
- **PASS:** `ratio >= 0.90`
- **WARNING:** `0.75 <= ratio < 0.90`
- **FAIL:** `ratio < 0.75`

**N/A condition:** Not enough matured cohorts for both comparison windows.

**Priority:** Medium

### C08 — Champions + Loyal Segment Share

- **Severity:** Medium (1.5×)
- **PASS:** > 20% of customers in Champions or Loyal segments
- **WARNING:** 10-20%
- **FAIL:** < 10%

### C09 — At-Risk Segment Share

- **Severity:** High (3.0×)
- **PASS:** < 25% of customers in At-Risk segment
- **WARNING:** 25-35%
- **FAIL:** > 35%

### C10 — Lost Segment Share

- **Severity:** Medium (1.5×)
- **PASS:** < 30% of customers in Lost segment
- **WARNING:** 30-45%
- **FAIL:** > 45%

### C11 — Days to Second Purchase

- **Severity:** High (3.0×)
- **PASS:** Median days to 2nd purchase < 60
- **WARNING:** 60-90 days
- **FAIL:** > 90 days
- **Impact:** Longer gaps correlate with lower F2 rate

### C12 — Customer Spend Growth Over Time

- **Severity:** Medium (1.5×)
- **PASS:** AOV increases with purchase frequency (nth order > (n-1)th)
- **WARNING:** Flat
- **FAIL:** Decreasing with repeat purchases

### C13 — LTV / CAC Ratio

- **Severity:** Critical (5.0×)
- **PASS:** > 3.0
- **WARNING:** 2.0-3.0
- **FAIL:** < 2.0
- **Note:** If CAC unavailable, this check is N/A

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Cohort LTV (preferably gross margin LTV) and CAC per cohort (marketing spend / new customers, by channel or blended).

**Pseudocode:**
```python
cac = marketing_spend_cohort / new_customers_cohort
ltv_cac = ltv365_gp / cac
```

**Thresholds:**
- **PASS:** `ltv_cac >= 3.0`
- **WARNING:** `1.5 <= ltv_cac < 3.0`
- **FAIL:** `ltv_cac < 1.5`

**N/A condition:** CAC not measurable (no spend, no attribution).

**Priority:** Medium

### C14 — Sale-Month Cohort Quality

- **Severity:** Medium (1.5×)
- **Question:** Do customers acquired during sales have lower LTV?
- **PASS:** Sale-month cohort LTV ≥ 70% of normal-month cohort
- **WARNING:** 50-70%
- **FAIL:** < 50%

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Identify sale cohorts (e.g., acquisition months with high discount incidence on first order), then compare retention and LTV.

**Pseudocode:**
```python
is_sale_month = cohort_month_discount_share > 0.30  # configurable

ratio_ltv = ltv_sale / ltv_non_sale
ratio_ret90 = ret90_sale / ret90_non_sale
```

**Thresholds:**
- **PASS:** `ratio_ltv >= 0.90` and `ratio_ret90 >= 0.90`
- **WARNING:** Any ratio in `[0.75, 0.90)`
- **FAIL:** Any ratio `< 0.75`

**N/A condition:** Cannot identify sale cohorts (no discount flags), or insufficient matured cohorts.

**Priority:** Medium

### C15 — High-Risk Churn Share

- **Severity:** Medium (1.5×)
- **PASS:** < 15% of customers flagged as high churn risk
- **WARNING:** 15-25%
- **FAIL:** > 25%

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Customer order history.

**Pseudocode:**
```python
# expected interval per segment: median days between purchases among repeat buyers
expected = median_interpurchase_days_by_segment

customers["days_since_last"] = (today - customers.last_order_ts).dt.days
customers["at_risk"] = customers.days_since_last > 1.5 * customers.segment.map(expected)

high_risk_share = customers.at_risk.mean()
```

**Thresholds:**
- **PASS:** `high_risk_share <= 35%`
- **WARNING:** `35% < high_risk_share <= 50%`
- **FAIL:** `high_risk_share > 50%`

**N/A condition:** Too little repeat history to estimate expected interpurchase intervals reliably.

**Priority:** High

## RFM Segment Definitions

| Segment | R Score | F Score | Description |
|---------|---------|---------|-------------|
| Champions | 4-5 | 4-5 | Recent, frequent, high-spend |
| Loyal | 3-4 | 3-4 | Regular purchasers |
| New Customers | 4-5 | 1-2 | Recent first-time buyers |
| Potential | 3 | 2-3 | Could become loyal with engagement |
| At Risk | 1-2 | 3-5 | Were frequent, now inactive |
| Lost | 1-2 | 1-2 | Long inactive, low frequency |

## Churn Risk Model

Simple sigmoid-based overdue ratio:

```
overdue_ratio = recency_days / avg_purchase_interval
churn_risk = 1 / (1 + exp(-0.5 × (overdue_ratio - 2)))
```

| Risk Level | Score | Action |
|-----------|-------|--------|
| Low | < 0.2 | Normal engagement |
| Medium | 0.2-0.5 | Proactive outreach |
| High | 0.5-0.8 | Win-back campaign |
| Critical | > 0.8 | Last-chance offer |
