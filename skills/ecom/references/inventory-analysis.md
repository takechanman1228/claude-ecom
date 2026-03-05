# Inventory Analysis Checklist (O01-O10)

<!-- Updated: 2026-03-04, v0.4 -->

## Framework

ABC classification × Inventory turnover × Safety stock model

## Check Definitions

### O01 — Overall Inventory Turnover Rate

- **Severity:** High (3.0×)
- **PASS:** > 6× per year (industry-dependent)
- **WARNING:** 4-6× per year
- **FAIL:** < 4× per year
- **Calculation:** Annual COGS / Average Inventory Value
- **Note:** Benchmarks vary by vertical (Fashion 4-6×, Food 12-24×, Electronics 4-8×)

### O02 — A-Rank Product Days of Stock

- **Severity:** Critical (5.0×)
- **PASS:** 14-45 days of stock for all A-rank products
- **WARNING:** 7-14 days or 45-60 days
- **FAIL:** < 7 days (imminent stockout) or > 60 days (excess)
- **Calculation:** quantity_on_hand / daily_sales_velocity

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Inventory on-hand and a demand rate for each SKU (e.g., trailing 30-60 day average daily units sold).

**Pseudocode:**
```python
a_skus = get_abc_rank(rev_90d).query("abc=='A'").index

daily_units = order_items_last_60d.groupby(["sku","date"])["qty"].sum()
avg_daily = daily_units.groupby("sku").mean()

on_hand = inventory_latest.set_index("sku")["on_hand_qty"]

dos = (on_hand / avg_daily).replace([np.inf], np.nan)

median_dos = dos[a_skus].median()
share_lt_14 = (dos[a_skus] < 14).mean()
```

**Thresholds:**
- **PASS:** `21 <= median_dos <= 60` and `share_lt_14 <= 10%`
- **WARNING:** `14-21 or 60-90 median_dos` or `10-20% share_lt_14`
- **FAIL:** `median_dos < 14` or `median_dos > 90` or `share_lt_14 > 20%`

**N/A condition:** Missing inventory snapshot or insufficient sales to compute demand rate.

**Priority:** Medium

### O03 — Stockout SKU Rate

- **Severity:** Critical (5.0×)
- **PASS:** < 5% of SKUs have zero stock
- **WARNING:** 5-10%
- **FAIL:** > 10%
- **Calculation:** count(quantity_on_hand <= 0) / total_skus

### O04 — Stockout Opportunity Cost

- **Severity:** Critical (5.0×)
- **PASS:** Estimated lost revenue < 3% of monthly revenue
- **WARNING:** 3-5%
- **FAIL:** > 5%
- **Calculation:** Σ(daily_avg_revenue × days_out_of_stock) for stockout SKUs

### O05 — Overstock Value (>90 Days)

- **Severity:** High (3.0×)
- **PASS:** Overstock value < 20% of total inventory value
- **WARNING:** 20-35%
- **FAIL:** > 35%
- **Calculation:** Σ(quantity × cost) for SKUs with days_on_hand > 90

### O06 — Deadstock Rate (>180 Days)

- **Severity:** High (3.0×)
- **PASS:** < 10% of SKUs are deadstock
- **WARNING:** 10-20%
- **FAIL:** > 20%

### O07 — Safety Stock Adequacy

- **Severity:** Medium (1.5×)
- **PASS:** A-rank products ≥ 95% safety stock adequacy
- **WARNING:** 85-95%
- **FAIL:** < 85%
- **Calculation:** safety_stock = Z × σ_daily_demand × √lead_time

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Demand variability (std dev of daily demand), lead time, and target service level.

**Pseudocode:**
```python
# simplified: SS = z * sigma_demand * sqrt(lead_time_days)
z = norm.ppf(target_cycle_service_level)  # e.g., CSL=0.98
sigma = stddev(daily_demand_last_90d)
L = mean_lead_time_days

ss_recommended = z * sigma * sqrt(L)

expected_demand_LT = mean_daily_demand * L
current_ss = max(inventory_position - expected_demand_LT, 0)

adequacy = current_ss / max(ss_recommended, 1e-9)
```

**Thresholds:**
- **PASS:** `adequacy >= 90%`
- **WARNING:** `70% <= adequacy < 90%`
- **FAIL:** `adequacy < 70%`

**N/A condition:** Lead time not available, demand history too sparse, or no inventory position visibility.

**Priority:** Low

### O08 — Lead Time Accuracy

- **Severity:** Medium (1.5×)
- **PASS:** Actual vs configured lead time error < 20%
- **WARNING:** 20-35%
- **FAIL:** > 35%
- **Data:** Requires actual receipt dates vs expected

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** PO create dates and receipt dates, and (ideally) promised receipt dates.

**Pseudocode:**
```python
po["planned_lt"] = (po.promised_receipt_ts - po.po_created_ts).dt.days
po["actual_lt"]  = (po.actual_receipt_ts - po.po_created_ts).dt.days

po = po[(po.planned_lt > 0) & (po.actual_lt > 0)]
po["ape"] = (po.actual_lt - po.planned_lt).abs() / po.planned_lt

median_ape = po["ape"].median()
```

**Thresholds:**
- **PASS:** `median_ape <= 10%`
- **WARNING:** `10% < median_ape <= 20%`
- **FAIL:** `median_ape > 20%`

**N/A condition:** No PO/receipt data or missing promised dates.

**Priority:** Low

### O09 — Seasonal Stockout Prevention

- **Severity:** Medium (1.5×)
- **PASS:** Zero stockouts during peak month
- **WARNING:** 1-2 SKUs stocked out during peak
- **FAIL:** 3+ SKUs stocked out during peak
- **Note:** Peak month identified from historical sales

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Seasonal SKU identification and daily/weekly in-stock during peak demand windows.

**Pseudocode:**
```python
peak_days = seasonal_peak_days(sku, last_season=True)
oos_days = count_days(available_to_sell_qty <= 0 over peak_days)
peak_stockout_rate = oos_days / len(peak_days)
```

**Thresholds:**
- **PASS:** `peak_stockout_rate <= 1%`
- **WARNING:** `1% < peak_stockout_rate <= 3%`
- **FAIL:** `peak_stockout_rate > 3%`

**N/A condition:** No seasonal tagging/detection.

**Priority:** Low

### O10 — Inventory Cost as % of Revenue

- **Severity:** Medium (1.5×)
- **PASS:** Total inventory cost < 25% of period revenue
- **WARNING:** 25-40%
- **FAIL:** > 40%

## Key Formulas

### Safety Stock
```
SS = Z × σ_demand × √(lead_time_days)
```
- Z = 1.65 for 95% service level, 2.33 for 99%

### Reorder Point
```
ROP = (daily_demand × lead_time) + safety_stock
```

### Inventory Turnover
```
Turnover = Annual_COGS / Avg_Inventory_Value
Days_of_Inventory = 365 / Turnover
```

### Opportunity Cost
```
Lost_Revenue = daily_avg_revenue_per_sku × days_out_of_stock
```
