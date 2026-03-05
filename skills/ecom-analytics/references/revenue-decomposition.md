# Revenue Decomposition Checklist (R01-R15)

<!-- Updated: 2026-03-04, v0.4 -->

## Framework

Revenue = Sessions × CVR × AOV (when session data available)
Revenue = Orders × AOV (minimum decomposition)

## Check Definitions

### R01 — Monthly Revenue Trend

- **Severity:** High (3.0×)
- **Question:** Are revenues growing month-over-month?
- **PASS:** 3 consecutive months of MoM growth > 0%
- **WARNING:** Latest MoM between -5% and 0%
- **FAIL:** MoM decline > 5% or 3+ consecutive decline months
- **Data:** `orders.groupby(month).amount.sum()`

### R02 — Seasonality Detection

- **Severity:** Medium (1.5×)
- **Question:** Is the seasonal pattern understood and accounted for?
- **PASS:** Positive trend after seasonal adjustment
- **WARNING:** Flat seasonally-adjusted trend
- **FAIL:** Declining seasonally-adjusted trend
- **Data:** 12+ months of order data recommended

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** At least 18-24 months of orders with `order_ts` and `net_revenue` (or `gross_revenue - discounts - refunds`). Monthly aggregation required.

**Pseudocode:**
```python
# Aggregate monthly revenue
m = orders.assign(month=lambda d: d.order_ts.dt.to_period("M").dt.to_timestamp()) \
          .groupby("month", as_index=False)["net_revenue"].sum()

# STL decomposition (period=12 months) -> seasonal, trend, remainder
stl = STL(m.net_revenue, period=12, robust=True).fit()
seasonal = stl.seasonal
remainder = stl.resid

# Seasonality strength (0..1): 1 - Var(remainder) / Var(seasonal + remainder)
seasonal_strength = max(0.0, 1.0 - variance(remainder) / variance(seasonal + remainder))

# Peak-month share (average across full years)
m["year"] = m["month"].dt.year
peak_month_share_by_year = m.groupby("year")["net_revenue"].max() / m.groupby("year")["net_revenue"].sum()
peak_month_share = peak_month_share_by_year.mean()
```

**Thresholds:**
- **PASS:** `seasonal_strength < 0.30` and `peak_month_share <= 25%`
- **WARNING:** `0.30 <= seasonal_strength < 0.60` or `25% < peak_month_share <= 35%`
- **FAIL:** `seasonal_strength >= 0.60` or `peak_month_share > 35%`

**N/A condition:** Fewer than 18 months of revenue history, or fewer than 2 full seasonal cycles.

**Priority:** High

### R03 — AOV Trend

- **Severity:** High (3.0×)
- **Question:** Is average order value stable or growing?
- **PASS:** AOV decline < 5% per month
- **WARNING:** AOV decline 5-10% per month
- **FAIL:** AOV decline > 10% per month
- **Data:** `orders.groupby(month).amount.mean()`

### R04 — Order Count Trend

- **Severity:** High (3.0×)
- **Question:** Is order volume maintaining or growing?
- **PASS:** MoM order count > -5%
- **WARNING:** MoM between -10% and -5%
- **FAIL:** MoM < -10%
- **Data:** `orders.groupby(month).order_id.nunique()`

### R05 — Repeat Customer Revenue Share

- **Severity:** Critical (5.0×)
- **Question:** Is the store building a repeat customer base?
- **PASS:** Repeat customer revenue > 30% of total
- **WARNING:** 20-30%
- **FAIL:** < 20%
- **Impact:** Low repeat rate signals unsustainable acquisition dependency

### R06 — Day/Hour Revenue Patterns

- **Severity:** Low (0.5×)
- **Question:** Are peak selling times identified?
- **PASS:** Data provided for scheduling optimisation
- **Data:** `orders.groupby(dayofweek, hour).amount.sum()`

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Orders with precise `order_ts` (store-local timezone) and revenue.

**Pseudocode:**
```python
o = orders.assign(ts_local=to_local_tz(orders.order_ts)) \
          .assign(dow=lambda d: d.ts_local.dt.dayofweek,  # 0=Mon
                  hour=lambda d: d.ts_local.dt.hour)

rev_dow = o.groupby("dow")["net_revenue"].sum()
rev_hour = o.groupby("hour")["net_revenue"].sum()

peakiness_dow = rev_dow.max() / rev_dow.mean()
peakiness_hour = rev_hour.max() / rev_hour.mean()

# Optional: "weekend share"
weekend_share = rev_dow.loc[[5,6]].sum() / rev_dow.sum()
```

**Thresholds:**
- **PASS:** DOW peakiness <= 1.5 and hour peakiness <= 2.5
- **WARNING:** DOW 1.5-2.5 or hour 2.5-4.0
- **FAIL:** DOW > 2.5 or hour > 4.0

**N/A condition:** Fewer than 8 weeks of orders, or store timezone unknown/unreliable.

**Priority:** High

### R07 — Revenue Concentration (Top 10% Customers)

- **Severity:** Medium (1.5×)
- **Question:** Is revenue overly concentrated in few customers?
- **PASS:** Top 10% customers < 60% of revenue
- **WARNING:** 60-80%
- **FAIL:** > 80%

### R08 — Average Discount Rate Trend

- **Severity:** High (3.0×)
- **Question:** Is the store becoming discount-dependent?
- **PASS:** Avg discount rate < 15%, no upward trend > 2pt/month
- **WARNING:** 15-25%, or upward trend 1-2pt/month
- **FAIL:** > 25%, or upward trend > 2pt/month

### R09 — Geographic Revenue Distribution

- **Severity:** Medium (1.5×)
- **Question:** Is revenue geographically diversified?
- **PASS:** Top 1 region < 70% of revenue
- **WARNING:** 70-85%
- **FAIL:** > 85%
- **Data:** Requires `city` or `region` column

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Orders with `shipping_country` (and ideally `shipping_region`) and `net_revenue`.

**Pseudocode:**
```python
g = orders.dropna(subset=["shipping_country"]) \
          .groupby("shipping_country")["net_revenue"].sum()
shares = g / g.sum()

top1_share = shares.max()
top3_share = shares.sort_values(ascending=False).head(3).sum()

# HHI on 0..10,000 scale
hhi = 10000.0 * (shares**2).sum()
```

**Thresholds:**
- **PASS:** `top1_share <= 70%` and `HHI < 2500`
- **WARNING:** `70% < top1_share <= 85%` or `2500 <= HHI < 4000`
- **FAIL:** `top1_share > 85%` or `HHI >= 4000`

**N/A condition:** Missing geography for > 20% of orders, or < 200 total orders in lookback window.

**Priority:** Medium

### R10 — Category Mix Stability

- **Severity:** Medium (1.5×)
- **Question:** Is the category mix stable?
- **PASS:** No category with > 20pt share change in 3 months
- **WARNING:** One category with 10-20pt shift
- **FAIL:** Multiple categories with > 20pt shifts

### R11 — Return Rate

- **Severity:** High (3.0×)
- **Question:** Is the return rate within acceptable bounds?
- **PASS:** < 5%
- **WARNING:** 5-10%
- **FAIL:** > 10%
- **Data:** Requires `financial_status` or `refund` column

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Returns/refunds joined to order_items (units) and orders (counts).

**Pseudocode:**
```python
sold_units = order_items.groupby("order_date")["qty"].sum().sum()
returned_units = returns.groupby("return_date")["qty"].sum().sum()

return_rate_units = returned_units / sold_units

orders_with_return = returns["order_id"].nunique()
total_orders = orders["order_id"].nunique()
return_rate_orders = orders_with_return / total_orders

refund_rate_revenue = returns["refunded_amount"].sum() / orders["gross_revenue"].sum()
```

**Thresholds:**
- **PASS:** `return_rate_orders <= 15%` (or <= vertical baseline)
- **WARNING:** `15% < return_rate_orders <= 25%`
- **FAIL:** `return_rate_orders > 25%`; also FAIL if return rate up > 5pp vs prior 90 days

**N/A condition:** No returns/refunds dataset, or returns cannot be linked to orders/items.

**Priority:** Medium

### R12 — Gross Margin Trend

- **Severity:** Critical (5.0×)
- **Question:** Is gross margin stable?
- **PASS:** Margin decline < 2pt per quarter
- **WARNING:** 2-5pt per quarter
- **FAIL:** > 5pt per quarter
- **Data:** Requires `cost` column

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Order items with `item_net_revenue` and `item_cogs` (or unit COGS).

**Pseudocode:**
```python
oi = order_items.assign(month=lambda d: d.order_ts.dt.to_period("M").dt.to_timestamp())
m = oi.groupby("month").agg(rev=("item_net_revenue","sum"),
                            cogs=("item_cogs","sum")).reset_index()
m["gm_pct"] = (m.rev - m.cogs) / m.rev

# Trend slope over last 6 months, in percentage points/month
last6 = m.sort_values("month").tail(6)
slope_pp_per_month = linregress(x=range(6), y=last6.gm_pct).slope * 100

gm_12m_avg = m.sort_values("month").tail(12).gm_pct.mean() * 100
gm_latest = m.sort_values("month").tail(1).gm_pct.iloc[0] * 100
delta_vs_12m_pp = gm_latest - gm_12m_avg
```

**Thresholds:**
- **PASS:** `slope >= -0.2 pp/mo` and `delta_vs_12m >= -2pp`
- **WARNING:** `-0.5 <= slope < -0.2` or `-5 <= delta < -2pp`
- **FAIL:** `slope < -0.5 pp/mo` or `delta < -5pp`

**N/A condition:** COGS missing for > 20% of net revenue, or fewer than 6 recent months with reliable data.

**Priority:** Medium

### R13 — Daily Revenue Volatility (CV)

- **Severity:** Medium (1.5×)
- **Question:** Is daily revenue predictable?
- **PASS:** Coefficient of variation < 0.5
- **WARNING:** 0.5-0.8
- **FAIL:** > 0.8

### R14 — Large Order Dependency

- **Severity:** Medium (1.5×)
- **Question:** Is revenue dependent on individual large orders?
- **PASS:** Largest single order < 5% of period revenue
- **WARNING:** 5-10%
- **FAIL:** > 10%

### R15 — Revenue Forecast Accuracy

- **Severity:** Low (0.5×)
- **Question:** Can revenue be predicted reliably?
- **PASS:** Forecast error < 15% (if forecasts exist)
- **WARNING:** 15-25%
- **FAIL:** > 25%
- **Note:** Requires historical forecasts; mark N/A if unavailable

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Forecasts aligned to actuals at SKU/category level for a consistent horizon (e.g., weekly forecast for next week).

**Pseudocode:**
```python
# Join forecasts to actuals at (sku, target_date)
f = forecasts.merge(actuals, on=["sku","target_date"], how="inner")

abs_err = (f.actual_units - f.forecast_units).abs()
wmape = abs_err.sum() / f.actual_units.sum()

bias = (f.forecast_units - f.actual_units).sum() / f.actual_units.sum()
```

**Thresholds:**
- **PASS:** `WMAPE <= 20%` and `|bias| <= 10%`
- **WARNING:** `20% < WMAPE <= 35%` or `10% < |bias| <= 20%`
- **FAIL:** `WMAPE > 35%` or `|bias| > 20%`

**N/A condition:** No forecast table, or forecasts cannot be aligned to actuals by target period.

**Priority:** Low
