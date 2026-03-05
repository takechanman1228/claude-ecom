# Conversion Funnel Checklist (CV01-CV12)

<!-- Updated: 2026-03-04, v0.4 -->

## Framework

Full funnel: Visit → Product View → Add to Cart → Begin Checkout → Purchase
Minimum (order data only): proxy CVR from order frequency and customer behaviour

## Check Definitions

### CV01 — Overall CVR Level

- **Severity:** Critical (5.0×)
- **Question:** Is the store converting at industry-appropriate rates?
- **PASS:** Within industry benchmark ±1 standard deviation
- **WARNING:** Below benchmark but within 2σ
- **FAIL:** More than 2σ below benchmark
- **Benchmark:** ~2.5% median (see benchmarks.md by vertical)

### CV02 — Mobile vs Desktop CVR Gap

- **Severity:** High (3.0×)
- **Question:** Is mobile conversion significantly lagging desktop?
- **PASS:** Mobile CVR ≥ 50% of Desktop CVR
- **WARNING:** 33-50% of Desktop CVR
- **FAIL:** < 33% of Desktop CVR
- **Data:** Requires `device` column

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Sessions with `device_category` and purchase attribution (session-to-order or event-based purchase).

**Pseudocode:**
```python
s = sessions.merge(purchases_by_session, on="session_id", how="left").fillna({"purchased":0})

def cvr(df):
    return df.purchased.sum() / df.session_id.nunique()

cvr_mobile = cvr(s[s.device_category=="mobile"])
cvr_desktop = cvr(s[s.device_category=="desktop"])

ratio = cvr_mobile / max(cvr_desktop, 1e-9)
```

**Thresholds:**
- **PASS:** `ratio >= 0.70`
- **WARNING:** `0.50 <= ratio < 0.70`
- **FAIL:** `ratio < 0.50`

**N/A condition:** < 1,000 sessions on either device in the lookback window (default 28-90 days).

**Priority:** High

### CV03 — Cart Abandonment Rate

- **Severity:** Critical (5.0×)
- **Question:** How many carts are abandoned?
- **PASS:** < 75%
- **WARNING:** 75-85%
- **FAIL:** > 85%
- **Data:** Requires session/funnel data; mark N/A if unavailable

### CV04 — Cart-to-Purchase Completion Rate

- **Severity:** High (3.0×)
- **Question:** What percentage of carts convert to orders?
- **PASS:** > 40%
- **WARNING:** 25-40%
- **FAIL:** < 25%

### CV05 — New Visitor CVR

- **Severity:** High (3.0×)
- **Question:** Are new visitors converting?
- **PASS:** > 1.0%
- **WARNING:** 0.5-1.0%
- **FAIL:** < 0.5%

### CV06 — Returning Visitor CVR

- **Severity:** Medium (1.5×)
- **Question:** Are returning visitors converting at higher rates?
- **PASS:** > 3.0%
- **WARNING:** 1.5-3.0%
- **FAIL:** < 1.5%

### CV07 — Channel-Level CVR

- **Severity:** Medium (1.5×)
- **Question:** Are all major channels converting?
- **PASS:** All major channels CVR > 0.5%
- **WARNING:** 1-2 channels below 0.5%
- **FAIL:** 3+ channels below 0.5%
- **Data:** Requires `channel` column

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Sessions with `channel_group` (or `source/medium`) and purchases; optionally marketing spend by channel.

**Pseudocode:**
```python
sitewide_cvr = total_purchases / total_sessions

by_channel = s.groupby("channel_group").agg(
    sessions=("session_id","nunique"),
    purchases=("purchased","sum")
)
by_channel["cvr"] = by_channel.purchases / by_channel.sessions
by_channel["rel"] = by_channel.cvr / sitewide_cvr

major = by_channel[by_channel.sessions >= 500]  # and/or >=5% traffic
worst_rel = major.rel.min()
```

**Thresholds:**
- **PASS:** No major channel has `rel < 0.60`
- **WARNING:** Any major channel has `0.40 <= rel < 0.60`
- **FAIL:** Any major channel has `rel < 0.40`, especially if high spend share

**N/A condition:** No channel attribution (or all sessions are "(direct)/(none)"), or channels lack sufficient volume.

**Priority:** Medium

### CV08 — Landing Page CVR

- **Severity:** High (3.0×)
- **Question:** Are top landing pages converting well?
- **PASS:** Top pages CVR > 2.0%
- **WARNING:** 1.0-2.0%
- **FAIL:** < 1.0%
- **Data:** Requires page-level data

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** `landing_page_url` per session and purchases by session.

**Pseudocode:**
```python
lp = s.groupby("landing_page_url").agg(
    sessions=("session_id","nunique"),
    purchases=("purchased","sum")
)
lp["cvr"] = lp.purchases / lp.sessions

# focus on top landing pages by traffic
top_lp = lp.sort_values("sessions", ascending=False).head(20)
share_good = (top_lp.cvr >= 0.75 * sitewide_cvr).mean()
```

**Thresholds:**
- **PASS:** `share_good >= 0.70` (>= 70% of top LPs meet >= 0.75x sitewide CVR)
- **WARNING:** `0.50 <= share_good < 0.70`
- **FAIL:** `share_good < 0.50`

**N/A condition:** Landing page not available; or < 1,000 sessions across the top landing pages combined.

**Priority:** High

### CV09 — Search-to-Product View Rate

- **Severity:** Medium (1.5×)
- **Question:** Are search users finding products?
- **PASS:** > 30%
- **WARNING:** 15-30%
- **FAIL:** < 15%
- **Data:** Requires on-site search data

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Tracked internal search events and product views in the same session (or within X minutes).

**Pseudocode:**
```python
search_sessions = events[events.event_name=="view_search_results"][["session_id","event_ts"]] \
                  .drop_duplicates("session_id")

# product view after search: view_item that occurs after first search event in session
first_search_ts = search_sessions.set_index("session_id")["event_ts"]

view_item = events[events.event_name=="view_item"][["session_id","event_ts"]]
view_item_after = view_item[view_item.event_ts > view_item.session_id.map(first_search_ts)]

sessions_with_view_after_search = view_item_after.session_id.nunique()
rate = sessions_with_view_after_search / max(search_sessions.session_id.nunique(), 1)
```

**Thresholds:**
- **PASS:** `rate >= 40%`
- **WARNING:** `25% <= rate < 40%`
- **FAIL:** `rate < 25%`

**N/A condition:** Search not tracked, or < 500 sessions containing search in lookback.

**Priority:** Medium

### CV10 — Product Page Add-to-Cart Rate

- **Severity:** High (3.0×)
- **Question:** Are product pages driving cart additions?
- **PASS:** > 8%
- **WARNING:** 4-8%
- **FAIL:** < 4%

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Product view events (`view_item`) and add-to-cart events (`add_to_cart`), ideally with `product_id`/`sku`.

**Pseudocode:**
```python
views = events[events.event_name=="view_item"].groupby("product_id").size()
atc = events[events.event_name=="add_to_cart"].groupby("product_id").size()

pdp = (views.to_frame("views").join(atc.to_frame("atc"), how="left").fillna(0))
pdp["atc_rate"] = pdp.atc / pdp.views

sitewide_atc_rate = pdp.atc.sum() / pdp.views.sum()

# view-weighted share of PDP views on products with decent ATC rate
good_views = (pdp[pdp.atc_rate >= 0.04].views.sum()) / pdp.views.sum()
```

**Thresholds:**
- **PASS:** `sitewide_atc_rate >= 6%` and `good_views >= 50%`
- **WARNING:** `4-6%` or `30-50%`
- **FAIL:** `sitewide_atc_rate < 4%` or `good_views < 30%`

**N/A condition:** Missing event instrumentation, or < 5,000 product views in lookback.

**Priority:** High

### CV11 — Checkout Step Drop-off

- **Severity:** Critical (5.0×)
- **Question:** Is each checkout step retaining users?
- **PASS:** Each step drop-off < 20%
- **WARNING:** 20-30%
- **FAIL:** Any step > 30% drop-off

#### Implementation
<!-- v0.4: added per DR2 research -->
<!-- v0.4: threshold updated per DR2 research -->

**Data requirements:** Checkout funnel events: `begin_checkout`, `add_shipping_info`, `add_payment_info`, `purchase`.

**Pseudocode:**
```python
sessions_begin = unique_sessions(events, "begin_checkout")
sessions_ship  = unique_sessions(events, "add_shipping_info")
sessions_pay   = unique_sessions(events, "add_payment_info")
sessions_buy   = unique_sessions(events, "purchase")

rate_ship = sessions_ship / max(sessions_begin, 1)
rate_pay  = sessions_pay  / max(sessions_ship, 1)
rate_buy  = sessions_buy  / max(sessions_pay, 1)

checkout_completion = sessions_buy / max(sessions_begin, 1)
worst_step_dropoff = 1.0 - min(rate_ship, rate_pay, rate_buy)
```

**Thresholds:**
- **PASS:** `checkout_completion >= 30%` and `worst_step_dropoff <= 35%`
- **WARNING:** `20-30% completion` or `35-50% worst step drop-off`
- **FAIL:** `completion < 20%` or `worst_step_dropoff > 50%`

**N/A condition:** Missing step events, or < 500 begin_checkout sessions in lookback.

**Priority:** High

### CV12 — CVR Time-Series Trend

- **Severity:** High (3.0×)
- **Question:** Is CVR improving or declining?
- **PASS:** MoM decline < 0.3pt
- **WARNING:** 0.3-0.5pt decline
- **FAIL:** > 0.5pt decline per month

## N/A Handling

Many conversion checks require session or funnel data that may not be in the
orders CSV. When data is unavailable:
- Mark the check as **N/A**
- Exclude from scoring (do not penalise)
- Note in the report which checks need additional data sources
