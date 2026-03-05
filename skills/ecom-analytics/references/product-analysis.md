# Product Analysis Checklist (P01-P20)

<!-- Updated: 2026-03-04, v0.4 -->

## Framework

ABC-XYZ analysis × Product lifecycle staging × Cross-sell discovery

## Check Definitions

### P01 — Top-20% Revenue Concentration

- **Severity:** Medium (1.5×)
- **PASS:** 60-80% of revenue from top 20% products (healthy Pareto)
- **WARNING:** 80-90% (over-concentrated) or < 50% (too diffuse)
- **FAIL:** > 90% or < 40%

### P02 — C-Rank Inventory Cost

- **Severity:** High (3.0×)
- **PASS:** C-rank products hold < 15% of total inventory cost
- **WARNING:** 15-25%
- **FAIL:** > 25%

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Inventory snapshots with `on_hand_qty` and `unit_cost`, plus sales data to compute ABC rank (recommend 90-day revenue).

**Pseudocode:**
```python
# ABC rank by trailing 90-day revenue
rev90 = order_items_last_90d.groupby("sku")["item_net_revenue"].sum().sort_values(ascending=False)
cum = rev90.cumsum() / rev90.sum()
rank = pd.cut(cum, bins=[0,0.80,0.95,1.0], labels=["A","B","C"], include_lowest=True)

inv = inventory_latest.assign(value=lambda d: d.on_hand_qty * d.unit_cost)
inv = inv.join(rank.rename("abc"), on="sku")

c_value_share = inv[inv.abc=="C"].value.sum() / inv.value.sum()

carrying_rate = 0.25  # default
annual_carry_cost_c = inv[inv.abc=="C"].value.sum() * carrying_rate
```

**Thresholds:**
- **PASS:** `c_value_share <= 20%`
- **WARNING:** `20% < c_value_share <= 35%`
- **FAIL:** `c_value_share > 35%`

**N/A condition:** Missing `unit_cost` or inventory snapshot not available.

**Priority:** Medium

### P03 — New Product Launch Velocity

- **Severity:** High (3.0×)
- **PASS:** New products reach 50% of monthly target in first 30 days
- **WARNING:** 30-50% of target
- **FAIL:** < 30% of target

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Product `launch_ts` (created/published) and sales by SKU.

**Pseudocode:**
```python
new = products[products.launch_ts >= today - days(90)][["sku","launch_ts"]]

sales = order_items.groupby(["sku","order_date"]).agg(units=("qty","sum"), orders=("order_id","nunique"))
first_sale_date = sales[sales.orders>0].reset_index().groupby("sku")["order_date"].min()

days_to_first_sale = (first_sale_date - new.set_index("sku").launch_ts).dt.days
median_days = days_to_first_sale.median()

# % of new SKUs hitting 5 orders within 30 days
orders_30d = sales.reset_index().merge(new, on="sku") \
                    .query("order_date <= launch_ts + @pd.Timedelta(days=30)") \
                    .groupby("sku")["orders"].sum()

pct_hit_5 = (orders_30d >= 5).mean()
```

**Thresholds:**
- **PASS:** `median_days_to_first_sale <= 7` and `pct_hit_5_orders_30d >= 40%`
- **WARNING:** `7-14 days` or `25-40%`
- **FAIL:** `median > 14 days` or `pct_hit_5 < 25%`

**N/A condition:** Fewer than 20 new SKUs in the lookback, or missing `launch_ts`.

**Priority:** Medium

### P04 — Average Product Reviews

- **Severity:** Medium (1.5×)
- **PASS:** A-rank products have > 10 reviews each
- **WARNING:** 5-10 reviews
- **FAIL:** < 5 reviews
- **Data:** Requires review count data

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Reviews (SKU, rating, count, timestamps) plus sales (to weight by revenue).

**Pseudocode:**
```python
rev_by_sku = order_items_last_90d.groupby("sku")["item_net_revenue"].sum()

reviews_agg = reviews.groupby("sku").agg(
    review_count=("review_id","count"),
    avg_rating=("rating","mean"),
    recent_review_ts=("review_ts","max")
)

x = reviews_agg.join(rev_by_sku.rename("rev"), how="right").fillna({"review_count":0})
rev_share_reviewed = x[x.review_count >= 5].rev.sum() / x.rev.sum()

weighted_avg_rating = (x.avg_rating.fillna(0) * x.rev).sum() / max(x.rev.sum(), 1)
low_rating_rev_share = x[x.avg_rating < 3.8].rev.sum() / x.rev.sum()
```

**Thresholds:**
- **PASS:** `rev_share_reviewed >= 70%`, `4.0 <= weighted_avg_rating <= 4.7`, and `low_rating_rev_share <= 10%`
- **WARNING:** `40-70% reviewed` or `3.8-4.0 rating` or `10-20% low-rating share`
- **FAIL:** `< 40% reviewed` or `rating < 3.8` or `low_rating_rev_share > 20%`

**N/A condition:** No review dataset available.

**Priority:** Medium

### P05 — Converting SKU Rate

- **Severity:** High (3.0×)
- **PASS:** > 70% of active SKUs have at least 1 sale
- **WARNING:** 50-70%
- **FAIL:** < 50%

### P06 — Multi-Item Order Rate

- **Severity:** Medium (1.5×)
- **PASS:** > 25% of orders contain 2+ items
- **WARNING:** 15-25%
- **FAIL:** < 15%

### P07 — Cross-Sell Pair Lift

- **Severity:** Medium (1.5×)
- **PASS:** At least 3 product pairs with lift > 2.0
- **WARNING:** 1-2 pairs with lift > 2.0
- **FAIL:** No pairs with lift > 1.5

### P08 — Category Cannibalisation

- **Severity:** High (3.0×)
- **PASS:** No existing product drops > 30% on new product launch within same category
- **WARNING:** 1 instance
- **FAIL:** 2+ instances

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Category sales by week, and a clear "launch event" marker for the new category/product-group.

**Pseudocode:**
```python
# For a launch_date and a set of "old cats" and "new cat"
pre = weekly_cat_sales.query("week < launch_date and week >= launch_date - 8w")
post = weekly_cat_sales.query("week >= launch_date and week < launch_date + 8w")

old_pre = pre[pre.cat.isin(old_cats)].sales.sum()
old_post = post[post.cat.isin(old_cats)].sales.sum()
new_post = post[post.cat==new_cat].sales.sum()

cannibalization_rate = max(0.0, (old_pre - old_post) / max(new_post, 1e-9))
```

**Thresholds:**
- **PASS:** `cannibalization_rate <= 30%` (>= 70% of new sales are incremental)
- **WARNING:** `30% < cannibalization_rate <= 60%`
- **FAIL:** `cannibalization_rate > 60%`

**N/A condition:** No identifiable launch event, or insufficient pre/post volume (e.g., < 100 orders per window).

**Priority:** Low

### P09 — Deadstock (180+ days)

- **Severity:** Critical (5.0×)
- **PASS:** < 10% of SKUs are deadstock
- **WARNING:** 10-20%
- **FAIL:** > 20%

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Inventory on hand + sales history for 180 days.

**Pseudocode:**
```python
sales180 = order_items_last_180d.groupby("sku")["qty"].sum()
inv = inventory_latest.assign(value=lambda d: d.on_hand_qty * d.unit_cost)

inv = inv.join(sales180.rename("units_180d"), on="sku").fillna({"units_180d":0})

dead = inv[(inv.on_hand_qty > 0) & (inv.units_180d == 0)]
deadstock_value_share = dead.value.sum() / inv.value.sum()
```

**Thresholds:**
- **PASS:** `deadstock_value_share <= 5%`
- **WARNING:** `5% < deadstock_value_share <= 10%`
- **FAIL:** `deadstock_value_share > 10%`

**N/A condition:** Missing inventory snapshots or unit costs.

**Priority:** High

### P10 — Lifecycle Stage Distribution

- **Severity:** Medium (1.5×)
- **PASS:** Decline-stage products < 30% of catalog
- **WARNING:** 30-50%
- **FAIL:** > 50%

### P11 — High-Return Products

- **Severity:** High (3.0×)
- **PASS:** All products return rate < 10%
- **WARNING:** Some products 10-15%
- **FAIL:** Any product > 15%

### P12 — Seasonal Stock Timing

- **Severity:** Medium (1.5×)
- **PASS:** Seasonal products stocked 30+ days before season
- **WARNING:** 15-30 days
- **FAIL:** < 15 days or stocked after season start

#### Implementation
<!-- v0.4: added per DR2 research -->

**Data requirements:** Seasonal SKU identification (tag or computed), weekly demand history, weekly/daily in-stock status.

**Pseudocode:**
```python
# identify peak window from last season
seasonal_skus = get_seasonal_skus(method="tag_or_strength", threshold=0.6)
peak_weeks = top_k_weeks_of_demand(sku, k=4, lookback="last_season")

instock_peak = in_stock_days(sku, peak_weeks) / total_days(peak_weeks)
```

**Thresholds:**
- **PASS:** `instock_peak >= 97%`
- **WARNING:** `92% <= instock_peak < 97%`
- **FAIL:** `instock_peak < 92%`

**N/A condition:** No way to identify seasonal SKUs (no tags and insufficient history for detection).

**Priority:** Low

### P13 — Product Content Richness

- **Severity:** Medium (1.5×)
- **PASS:** 3+ images and 200+ char description for A-rank products
- **WARNING:** Partial compliance
- **FAIL:** Missing images or < 100 char descriptions
- **Data:** Requires product content metadata

#### Implementation
<!-- v0.4: added per DR2 research -->

**Data requirements:** Product content fields: title length, description text length, bullets, images count, video count, attributes completeness; plus revenue to weight.

**Pseudocode:**
```python
def score_product(p):
    points = 0
    points += (len(p.title or "") >= 80)
    points += (len(p.description or "") >= 250)
    points += (p.bullet_count >= 5)
    points += (p.image_count >= 5)
    points += (p.video_count >= 1)
    points += (p.attribute_fill_rate >= 0.80)
    return points / 6.0

pc = products.apply(score_product, axis=1).rename("content_score")
rev = order_items_last_90d.groupby("sku")["item_net_revenue"].sum()

x = products.set_index("sku").join(pc).join(rev.rename("rev")).fillna({"rev":0})
rev_weighted_share_good = x[x.content_score >= 0.8].rev.sum() / max(x.rev.sum(), 1)
```

**Thresholds:**
- **PASS:** `rev_weighted_share_good >= 80%`
- **WARNING:** `50% <= rev_weighted_share_good < 80%`
- **FAIL:** `rev_weighted_share_good < 50%`

**N/A condition:** Product content fields unavailable (e.g., only SKU + price).

**Priority:** Medium

### P14 — Category Gross Margin

- **Severity:** High (3.0×)
- **PASS:** All categories have positive gross margin
- **WARNING:** 1 category at break-even
- **FAIL:** Any category with negative margin

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Order items with `category_id`, net revenue, and COGS.

**Pseudocode:**
```python
cat = order_items_last_90d.groupby("category_id").agg(
    rev=("item_net_revenue","sum"),
    cogs=("item_cogs","sum"),
    orders=("order_id","nunique"),
)
cat["gm_pct"] = (cat.rev - cat.cogs) / cat.rev

overall_gm = (cat.rev.sum() - cat.cogs.sum()) / cat.rev.sum()

cat["rev_share"] = cat.rev / cat.rev.sum()
top_cats = cat[cat.rev_share >= 0.10]  # important categories
worst_gap_pp = ((top_cats.gm_pct - overall_gm) * 100).min()  # negative gap
```

**Thresholds:**
- **PASS:** No top category (>= 10% revenue) is more than 5pp below overall gross margin
- **WARNING:** Any top category is 5-10pp below overall
- **FAIL:** Any top category is > 10pp below overall (or low-margin categories jointly > 30% of revenue)

**N/A condition:** Missing COGS by category or SKU.

**Priority:** Medium

### P15 — A-Rank Stockout Frequency

- **Severity:** Critical (5.0×)
- **PASS:** 0 stockout events for A-rank products
- **WARNING:** 1-2 events in period
- **FAIL:** 3+ events

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Daily availability (`available_to_sell_qty` or in-stock) and ABC ranks.

**Pseudocode:**
```python
a_skus = get_abc_rank(rev_90d).query("abc == 'A'").index

snap = inventory_snapshots_last_90d
snap["in_stock"] = (snap.available_to_sell_qty > 0).astype(int)

instock_by_sku = snap[snap.sku.isin(a_skus)].groupby("sku")["in_stock"].mean()  # % days in stock
rev_weight = rev90[a_skus] / rev90[a_skus].sum()

rev_weighted_in_stock = (instock_by_sku * rev_weight).sum()
```

**Thresholds:**
- **PASS:** `rev_weighted_in_stock >= 98%`
- **WARNING:** `95% <= rev_weighted_in_stock < 98%`
- **FAIL:** `rev_weighted_in_stock < 95%`

**N/A condition:** No availability snapshots (or only "current inventory" without history).

**Priority:** Medium

### P16 — Bundle Effectiveness

- **Severity:** Medium (1.5×)
- **PASS:** Bundle AOV > 1.2× non-bundle AOV
- **WARNING:** 1.0-1.2×
- **FAIL:** < 1.0× (bundles decrease AOV)

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Bundle definitions and order_items that identify bundles (either as distinct SKUs or via bundle_id) and component mapping.

**Pseudocode:**
```python
bundle_orders = orders[orders.order_id.isin(order_items[order_items.is_bundle==1].order_id)]
attach_rate = bundle_orders.order_id.nunique() / orders.order_id.nunique()

aov_bundle = bundle_orders.net_revenue.mean()
aov_all = orders.net_revenue.mean()
delta_aov_pct = (aov_bundle - aov_all) / aov_all

gp_bundle = bundle_orders.gross_profit.mean()  # if available
gp_all = orders.gross_profit.mean()
delta_gp_pct = (gp_bundle - gp_all) / gp_all
```

**Thresholds:**
- **PASS:** `attach_rate >= 5%` and `delta_gp_pct >= 0%`
- **WARNING:** `2-5% attach` or `-10% < delta_gp < 0%`
- **FAIL:** `attach_rate < 2%` or `delta_gp_pct <= -10%`

**N/A condition:** No bundles offered / cannot identify bundle orders.

**Priority:** Medium

### P17 — Rating-Sales Correlation

- **Severity:** Low (0.5×)
- **PASS:** Data analysis provided
- **Note:** Informational only

#### Implementation
<!-- v0.4: added per DR2 research -->

**Data requirements:** SKU ratings and SKU sales (units or revenue).

**Pseudocode:**
```python
x = sku_metrics.query("orders_90d >= 30 and review_count >= 5")
rho, p = spearmanr(x.avg_rating, x.units_90d)
```

**Thresholds:**
- **PASS:** `rho >= 0.20` and `p < 0.05` (ratings align with demand)
- **WARNING:** `-0.20 < rho < 0.20` or `p >= 0.05` (no clear relationship)
- **FAIL:** `rho <= -0.20` with adequate sample

**N/A condition:** Too few SKUs with both meaningful sales and reviews.

**Priority:** Low

### P18 — New Product Introduction Frequency

- **Severity:** Medium (1.5×)
- **PASS:** 1+ new products per month
- **WARNING:** 1 per quarter
- **FAIL:** < 1 per quarter

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Product catalog with `created_ts` (or first published date) and an "active SKU" definition.

**Pseudocode:**
```python
active = products[products.status=="active"]
new_90d = active[active.created_ts >= today - days(90)]

ratio = len(new_90d) / max(len(active), 1)
```

**Thresholds:**
- **PASS:** `2% <= ratio <= 10%` (healthy newness without operational overload)
- **WARNING:** `1-2%` or `10-20%`
- **FAIL:** `ratio < 1%` or `ratio > 20%`

**N/A condition:** Missing product creation dates.

**Priority:** High

### P19 — Price Tier Distribution

- **Severity:** Medium (1.5×)
- **PASS:** Products span 3+ distinct price tiers
- **WARNING:** 2 tiers
- **FAIL:** Single price tier

### P20 — Consumable Repurchase Rate

- **Severity:** High (3.0×)
- **PASS:** Consumable/replenishable products have > 20% repurchase rate
- **WARNING:** 10-20%
- **FAIL:** < 10%
- **Note:** Only applicable to stores with consumable products; N/A otherwise

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Customer order history at SKU level and a "consumable" flag (or inferred by reorder behavior).

**Pseudocode:**
```python
consumables = products[products.is_consumable==1]["sku"]

# For each SKU, compute first-time buyers in last 180d and whether they repurchase in window
window_min, window_max = 15, 90  # configurable; ideally derived per SKU

first_purchase = orders_items[orders_items.sku.isin(consumables)] \
    .sort_values("order_ts") \
    .groupby(["customer_id","sku"]).first().reset_index()

repurchase = orders_items[orders_items.sku.isin(consumables)] \
    .merge(first_purchase, on=["customer_id","sku"], suffixes=("","_first")) \
    .assign(days_since=lambda d: (d.order_ts - d.order_ts_first).dt.days) \
    .query("days_since >= @window_min and days_since <= @window_max")

repurchase_rate = repurchase[["customer_id","sku"]].drop_duplicates().shape[0] / \
                  max(first_purchase.shape[0], 1)
```

**Thresholds:**
- **PASS:** `repurchase_rate >= 30%`
- **WARNING:** `15% <= repurchase_rate < 30%`
- **FAIL:** `repurchase_rate < 15%`

**N/A condition:** No consumable tagging (and no reliable way to infer replenishment windows).

**Priority:** Medium
