"""Business review engine — unified period-based model.

Produces review.json with multi-period analysis (30d/90d/365d),
health checks, top issues, and action candidates.
"""

from __future__ import annotations

import math
from datetime import date, datetime

import pandas as pd

from .checks import (
    CheckResult,
    build_action_candidates,
    build_top_issues,
)
from .periods import (
    PeriodRange,
    compute_data_coverage,
    prior_trailing_window,
    trailing_window,
)

# ---------------------------------------------------------------------------
# Period summary (kept from original, extended)
# ---------------------------------------------------------------------------


def compute_period_summary(orders: pd.DataFrame, period: PeriodRange) -> dict:
    """Compute KPIs for a calendar period.

    Filters orders to [period.start, period.end] then computes core metrics.
    """
    mask = (orders["order_date"].dt.date >= period.start) & (orders["order_date"].dt.date <= period.end)
    filtered = orders[mask]

    if filtered.empty:
        return {
            "revenue": 0.0,
            "orders": 0,
            "aov": 0.0,
            "customers": 0,
            "new_customers": 0,
            "returning_customers": 0,
            "new_customer_revenue": 0.0,
            "returning_customer_revenue": 0.0,
            "new_customer_aov": 0.0,
            "returning_customer_aov": 0.0,
            "avg_discount_rate": 0.0,
        }

    revenue = float(filtered["amount"].sum())
    n_orders = int(filtered["order_id"].nunique())
    aov = revenue / n_orders if n_orders else 0.0
    customers = int(filtered["customer_id"].nunique())

    # Determine new vs returning based on full order history
    first_order = orders.groupby("customer_id")["order_date"].min()
    period_customers = filtered["customer_id"].unique()
    new_custs = [
        c
        for c in period_customers
        if c in first_order.index and first_order[c].date() >= period.start and first_order[c].date() <= period.end
    ]
    new_customers = len(new_custs)
    returning_customers = customers - new_customers

    new_mask = filtered["customer_id"].isin(new_custs)
    new_customer_revenue = float(filtered.loc[new_mask, "amount"].sum())
    returning_customer_revenue = float(filtered.loc[~new_mask, "amount"].sum())

    # Per-segment AOV
    new_orders = int(filtered.loc[new_mask, "order_id"].nunique()) if new_mask.any() else 0
    ret_orders = int(filtered.loc[~new_mask, "order_id"].nunique()) if (~new_mask).any() else 0
    new_customer_aov = new_customer_revenue / new_orders if new_orders else 0.0
    returning_customer_aov = returning_customer_revenue / ret_orders if ret_orders else 0.0

    avg_discount_rate = 0.0
    if "discount" in filtered.columns:
        gross = filtered["amount"] + filtered["discount"]
        gross_sum = gross.sum()
        avg_discount_rate = float(filtered["discount"].sum() / gross_sum) if gross_sum else 0.0

    return {
        "revenue": revenue,
        "orders": n_orders,
        "aov": aov,
        "customers": customers,
        "new_customers": new_customers,
        "returning_customers": returning_customers,
        "new_customer_revenue": new_customer_revenue,
        "returning_customer_revenue": returning_customer_revenue,
        "new_customer_aov": new_customer_aov,
        "returning_customer_aov": returning_customer_aov,
        "avg_discount_rate": avg_discount_rate,
    }


def compute_period_comparison(current: dict, previous: dict) -> dict:
    """Compute % change for each KPI between two periods."""
    result = {}
    for key in current:
        cur = current[key]
        prev = previous.get(key, 0)
        if isinstance(cur, (int, float)) and isinstance(prev, (int, float)):
            if prev != 0:
                result[key] = (cur - prev) / abs(prev)
            else:
                result[key] = 0.0 if cur == 0 else float("inf")
        else:
            result[key] = 0.0
    return result


# ---------------------------------------------------------------------------
# Period block computation
# ---------------------------------------------------------------------------


def _compute_period_block(orders: pd.DataFrame, ref_date: date, days: int) -> dict:
    """Compute a single period block: summary + kpi_tree + drivers."""
    current_window = trailing_window(ref_date, days)
    prior_window = prior_trailing_window(ref_date, days)

    current_summary = compute_period_summary(orders, current_window)
    prior_summary = compute_period_summary(orders, prior_window)
    changes = compute_period_comparison(current_summary, prior_summary)

    summary = {
        "revenue": current_summary["revenue"],
        "revenue_change": changes.get("revenue", 0.0),
        "orders": current_summary["orders"],
        "orders_change": changes.get("orders", 0.0),
        "aov": current_summary["aov"],
        "aov_change": changes.get("aov", 0.0),
        "customers": current_summary["customers"],
        "customers_change": changes.get("customers", 0.0),
    }

    rev = current_summary["revenue"]
    kpi_tree = {
        "new_customer_revenue": current_summary["new_customer_revenue"],
        "new_customer_revenue_share": (current_summary["new_customer_revenue"] / rev if rev else 0.0),
        "new_customers": current_summary["new_customers"],
        "new_customers_change": changes.get("new_customers", 0.0),
        "new_customer_aov": current_summary["new_customer_aov"],
        "returning_customer_revenue": current_summary["returning_customer_revenue"],
        "returning_customer_revenue_share": (current_summary["returning_customer_revenue"] / rev if rev else 0.0),
        "returning_customers": current_summary["returning_customers"],
        "returning_customers_change": changes.get("returning_customers", 0.0),
        "returning_customer_aov": current_summary["returning_customer_aov"],
    }

    drivers = _compute_drivers(current_summary, prior_summary)

    return {
        "summary": summary,
        "kpi_tree": kpi_tree,
        "drivers": drivers,
    }


def _compute_drivers(current: dict, prior: dict) -> dict:
    """Decompose revenue change into AOV, volume, and mix effects."""
    cur_rev = current.get("revenue", 0)
    prev_rev = prior.get("revenue", 0)
    if prev_rev == 0:
        return {"aov_effect": 0, "volume_effect": 0, "mix_effect": 0}

    cur_orders = current.get("orders", 0)
    prev_orders = prior.get("orders", 0)
    cur_aov = current.get("aov", 0)
    prev_aov = prior.get("aov", 0)

    # Volume effect: change in orders at prior AOV
    volume_effect = (cur_orders - prev_orders) * prev_aov
    # AOV effect: change in AOV at current orders
    aov_effect = (cur_aov - prev_aov) * cur_orders
    # Mix effect: residual
    total_change = cur_rev - prev_rev
    mix_effect = total_change - volume_effect - aov_effect

    return {
        "aov_effect": round(aov_effect, 2),
        "volume_effect": round(volume_effect, 2),
        "mix_effect": round(mix_effect, 2),
    }


# ---------------------------------------------------------------------------
# Monthly trend (for 365d block)
# ---------------------------------------------------------------------------


def _compute_monthly_trend(orders: pd.DataFrame, ref: date, days: int = 365) -> list[dict]:
    """Compute monthly KPI series for the trailing window.

    Only includes months that actually contain data within
    [ref - days + 1, ref]. Each entry includes ``partial`` and
    ``days_with_data`` when the month has data for less than half its days.

    Returns list of dicts with keys: month, revenue, orders, aov,
    customers, new_customers, returning_customers, partial, days_with_data.
    """
    import calendar
    from datetime import timedelta

    window_start = ref - timedelta(days=days - 1)
    window_end = ref

    # Determine the range of months that overlap with the window
    start_year, start_month = window_start.year, window_start.month
    end_year, end_month = window_end.year, window_end.month

    trend = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        month_first = date(y, m, 1)
        month_last_day = calendar.monthrange(y, m)[1]
        month_last = date(y, m, month_last_day)

        # Clip to window bounds
        period_start = max(month_first, window_start)
        period_end = min(month_last, window_end)

        period = PeriodRange(
            label=f"{y}-{m:02d}",
            start=period_start,
            end=period_end,
        )
        summary = compute_period_summary(orders, period)

        # Skip months with zero data
        if summary["orders"] == 0 and summary["revenue"] == 0.0:
            # Advance month
            m += 1
            if m > 12:
                m = 1
                y += 1
            continue

        # Count actual days with data
        mask = (orders["order_date"].dt.date >= period_start) & (orders["order_date"].dt.date <= period_end)
        days_with_data = int(orders.loc[mask, "order_date"].dt.date.nunique())
        is_partial = days_with_data < month_last_day / 2

        entry = {
            "month": f"{y}-{m:02d}",
            "revenue": summary["revenue"],
            "orders": summary["orders"],
            "aov": summary["aov"],
            "customers": summary["customers"],
            "new_customers": summary["new_customers"],
            "returning_customers": summary["returning_customers"],
            "days_with_data": days_with_data,
        }
        if is_partial:
            entry["partial"] = True
        trend.append(entry)

        # Advance month
        m += 1
        if m > 12:
            m = 1
            y += 1

    return trend


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def _build_metadata(orders: pd.DataFrame) -> dict:
    """Build metadata block from orders data."""
    total_revenue = float(orders["amount"].sum())
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "data_start": str(orders["order_date"].min().date()),
        "data_end": str(orders["order_date"].max().date()),
        "total_orders": int(orders["order_id"].nunique()),
        "total_customers": int(orders["customer_id"].nunique()),
        "total_revenue": total_revenue,
        "currency": "USD",
        "revenue_definition": "Net sales after discounts, before tax and shipping",
    }


# ---------------------------------------------------------------------------
# Health checks (moved from cli.py, adapted for 3-category model)
# ---------------------------------------------------------------------------


def _build_checks(
    rev_kpis: dict,
    cohort_kpis: dict,
    orders: pd.DataFrame,
) -> list[CheckResult]:
    """Build check results from computed KPIs.

    3 categories: revenue, customer, product.
    Orders-only input (no products/inventory params).
    """
    checks: list[CheckResult] = []

    # ===== Revenue checks (R01, R03, R04, R05, R07, R08, R13, R14) =====
    partial_last = rev_kpis.get("partial_last_month", False)

    mom = rev_kpis.get("mom_growth_latest", float("nan"))
    try:
        mom = float(mom)
    except (ValueError, TypeError):
        mom = float("nan")
    if math.isnan(mom):
        checks.append(
            CheckResult("R01", "revenue", "high", "na", "Insufficient data for MoM growth (<2 months)", None, 0.0)
        )
    else:
        suffix = " (partial month excluded)" if partial_last else ""
        checks.append(
            CheckResult(
                "R01",
                "revenue",
                "high",
                "pass" if mom > 0 else ("watch" if mom > -0.05 else "fail"),
                f"MoM revenue growth: {mom:.1%}{suffix}",
                mom,
                0.0,
            )
        )

    # R03 — AOV Trend (skip partial last month)
    monthly_aov = rev_kpis.get("monthly_aov", {})
    aov_vals = list(monthly_aov.values())
    if partial_last and len(aov_vals) >= 3:
        aov_change = (aov_vals[-2] - aov_vals[-3]) / aov_vals[-3] if aov_vals[-3] else 0
        checks.append(
            CheckResult(
                "R03",
                "revenue",
                "high",
                "pass" if aov_change > -0.05 else ("watch" if aov_change > -0.1 else "fail"),
                f"AOV MoM change: {aov_change:.1%} (partial month excluded)",
                aov_change,
                -0.05,
            )
        )
    elif not partial_last and len(aov_vals) >= 2:
        aov_change = (aov_vals[-1] - aov_vals[-2]) / aov_vals[-2] if aov_vals[-2] else 0
        checks.append(
            CheckResult(
                "R03",
                "revenue",
                "high",
                "pass" if aov_change > -0.05 else ("watch" if aov_change > -0.1 else "fail"),
                f"AOV MoM change: {aov_change:.1%}",
                aov_change,
                -0.05,
            )
        )

    # R04 — Order Count Trend (skip partial last month)
    monthly_orders = rev_kpis.get("monthly_orders", {})
    ord_vals = list(monthly_orders.values())
    if partial_last and len(ord_vals) >= 3:
        ord_change = (ord_vals[-2] - ord_vals[-3]) / ord_vals[-3] if ord_vals[-3] else 0
        checks.append(
            CheckResult(
                "R04",
                "revenue",
                "high",
                "pass" if ord_change > -0.05 else ("watch" if ord_change > -0.1 else "fail"),
                f"MoM order count change: {ord_change:.1%} (partial month excluded)",
                ord_change,
                -0.05,
            )
        )
    elif not partial_last and len(ord_vals) >= 2:
        ord_change = (ord_vals[-1] - ord_vals[-2]) / ord_vals[-2] if ord_vals[-2] else 0
        checks.append(
            CheckResult(
                "R04",
                "revenue",
                "high",
                "pass" if ord_change > -0.05 else ("watch" if ord_change > -0.1 else "fail"),
                f"MoM order count change: {ord_change:.1%}",
                ord_change,
                -0.05,
            )
        )

    # R05 — Repeat Customer Revenue Share
    repeat_share = rev_kpis.get("repeat_revenue_share", 0)
    rpr_for_cross_check = cohort_kpis.get("repeat_purchase_rate", 0)
    if repeat_share == 0 and rpr_for_cross_check > 0.3:
        checks.append(
            CheckResult(
                "R05",
                "revenue",
                "critical",
                "watch",
                f"Repeat customer revenue share: {repeat_share:.1%} "
                f"(data quality issue: repeat purchase rate={rpr_for_cross_check:.1%})",
                repeat_share,
                0.3,
            )
        )
    else:
        checks.append(
            CheckResult(
                "R05",
                "revenue",
                "critical",
                "pass" if repeat_share >= 0.3 else ("watch" if repeat_share >= 0.2 else "fail"),
                f"Repeat customer revenue share: {repeat_share:.1%}",
                repeat_share,
                0.3,
            )
        )

    # R07 — Revenue Concentration (Top 10% Customers)
    top10 = rev_kpis.get("top10_customer_share", 0)
    if rev_kpis.get("total_revenue", 0) == 0:
        checks.append(
            CheckResult("R07", "revenue", "medium", "na", "No revenue data for concentration analysis", None, 0.6)
        )
    else:
        checks.append(
            CheckResult(
                "R07",
                "revenue",
                "medium",
                "pass" if top10 < 0.6 else ("watch" if top10 < 0.8 else "fail"),
                f"Top 10% customer revenue share: {top10:.1%}",
                top10,
                0.6,
            )
        )

    # R08 — Average Discount Rate (subsumes old PR01)
    discount_rate = rev_kpis.get("avg_discount_rate", 0)
    if "discount" not in orders.columns and discount_rate == 0:
        checks.append(CheckResult("R08", "revenue", "high", "na", "No discount data available", None, 0.15))
    else:
        checks.append(
            CheckResult(
                "R08",
                "revenue",
                "high",
                "pass" if discount_rate < 0.15 else ("watch" if discount_rate < 0.25 else "fail"),
                f"Average discount rate: {discount_rate:.1%}",
                discount_rate,
                0.15,
            )
        )

    # R13 — Daily Revenue Volatility (CV)
    daily_cv = rev_kpis.get("daily_revenue_cv", 0)
    if isinstance(daily_cv, float) and math.isnan(daily_cv):
        checks.append(
            CheckResult("R13", "revenue", "medium", "na", "Insufficient daily data for CV calculation", None, 0.5)
        )
    elif rev_kpis.get("total_revenue", 0) == 0:
        checks.append(CheckResult("R13", "revenue", "medium", "na", "No revenue data for CV calculation", None, 0.5))
    else:
        checks.append(
            CheckResult(
                "R13",
                "revenue",
                "medium",
                "pass" if daily_cv < 0.5 else ("watch" if daily_cv < 0.8 else "fail"),
                f"Daily revenue coefficient of variation: {daily_cv:.2f}",
                daily_cv,
                0.5,
            )
        )

    # R14 — Large Order Dependency
    if rev_kpis.get("total_revenue", 0) > 0:
        order_amounts = orders.groupby("order_id")["amount"].sum()
        largest_share = order_amounts.max() / rev_kpis["total_revenue"]
        checks.append(
            CheckResult(
                "R14",
                "revenue",
                "medium",
                "pass" if largest_share < 0.05 else ("watch" if largest_share < 0.1 else "fail"),
                f"Largest order share of revenue: {largest_share:.1%}",
                largest_share,
                0.05,
            )
        )

    # ===== Pricing checks (now under revenue: PR02, PR03, PR07, PR08) =====
    if "discount" in orders.columns:
        from .pricing import discount_dependency as dd_fn

        dd = dd_fn(orders)
        checks.append(
            CheckResult(
                "PR02",
                "revenue",
                "high",
                "pass" if dd.discounted_order_ratio < 0.4 else ("watch" if dd.discounted_order_ratio < 0.6 else "fail"),
                f"Discounted order ratio: {dd.discounted_order_ratio:.1%}",
                dd.discounted_order_ratio,
                0.4,
            )
        )
        trend = dd.discount_rate_trend
        checks.append(
            CheckResult(
                "PR03",
                "revenue",
                "critical",
                "pass" if trend in ("stable", "decreasing") else "watch",
                f"Discount depth trend: {trend}",
                trend,
                "stable",
            )
        )

    # PR07 — Category Margin Variance (if cost data available)
    if "cost" in orders.columns:
        from .pricing import margin_analysis

        ma = margin_analysis(orders)
        neg_cats = len(ma.negative_margin_categories)
        checks.append(
            CheckResult(
                "PR07",
                "revenue",
                "medium",
                "pass" if neg_cats == 0 else ("watch" if neg_cats == 1 else "fail"),
                f"Categories with negative margin: {neg_cats}",
                neg_cats,
                0,
            )
        )

    # PR08 — Free-Shipping Threshold
    from .pricing import free_shipping_threshold

    fst = free_shipping_threshold(orders)
    if fst.suggested_threshold == 0 or fst.current_aov == 0:
        checks.append(
            CheckResult(
                "PR08",
                "revenue",
                "high",
                "na",
                "Insufficient order data for free-shipping threshold analysis",
                None,
                0.1,
            )
        )
    else:
        checks.append(
            CheckResult(
                "PR08",
                "revenue",
                "high",
                "pass" if fst.potential_aov_lift >= 0.1 else ("watch" if fst.potential_aov_lift >= 0.05 else "fail"),
                f"Free-shipping threshold AOV lift potential: {fst.potential_aov_lift:.1%} "
                f"(suggested: {fst.suggested_threshold:,.0f})",
                fst.potential_aov_lift,
                0.1,
            )
        )

    # ===== Customer checks (C01, C08, C09, C10, C11) =====
    rpr = cohort_kpis.get("repeat_purchase_rate", 0)
    checks.append(
        CheckResult(
            "C01",
            "customer",
            "critical",
            "pass" if rpr >= 0.25 else ("watch" if rpr >= 0.15 else "fail"),
            f"Repeat purchase rate: {rpr:.1%}",
            rpr,
            0.25,
        )
    )

    avg_interval = cohort_kpis.get("avg_purchase_interval_days", float("nan"))
    if isinstance(avg_interval, float) and math.isnan(avg_interval):
        checks.append(
            CheckResult(
                "C11", "customer", "high", "na", "Insufficient data for purchase interval calculation", None, 60
            )
        )
    else:
        checks.append(
            CheckResult(
                "C11",
                "customer",
                "high",
                "pass" if avg_interval < 60 else ("watch" if avg_interval < 90 else "fail"),
                f"Avg days to 2nd purchase: {avg_interval:.0f}",
                avg_interval,
                60,
            )
        )

    # C08/C09/C10 — RFM Segment Distribution
    order_counts = orders.groupby("customer_id")["order_id"].nunique()
    total_cust = len(order_counts)
    if total_cust > 0:
        from .cohort import rfm_segmentation

        try:
            rfm = rfm_segmentation(orders)
            seg_dist = rfm["segment"].value_counts(normalize=True)

            champions_loyal = seg_dist.get("Champions", 0) + seg_dist.get("Loyal", 0)
            checks.append(
                CheckResult(
                    "C08",
                    "customer",
                    "medium",
                    "pass" if champions_loyal >= 0.2 else ("watch" if champions_loyal >= 0.1 else "fail"),
                    f"Champions + Loyal segment share: {champions_loyal:.1%}",
                    champions_loyal,
                    0.2,
                )
            )

            at_risk = seg_dist.get("At Risk", 0)
            checks.append(
                CheckResult(
                    "C09",
                    "customer",
                    "high",
                    "pass" if at_risk < 0.25 else ("watch" if at_risk < 0.35 else "fail"),
                    f"At-Risk segment share: {at_risk:.1%}",
                    at_risk,
                    0.25,
                )
            )

            lost = seg_dist.get("Lost", 0)
            checks.append(
                CheckResult(
                    "C10",
                    "customer",
                    "medium",
                    "pass" if lost < 0.3 else ("watch" if lost < 0.45 else "fail"),
                    f"Lost segment share: {lost:.1%}",
                    lost,
                    0.3,
                )
            )
        except Exception:
            pass

    # ===== Product checks (P01, P05, P06, P07, P10, P19) =====
    key = "sku" if "sku" in orders.columns else "product_name" if "product_name" in orders.columns else None

    # P01 — Top-20% Revenue Concentration (orders-only approximation)
    if key:
        product_rev = orders.groupby(key)["amount"].sum().sort_values(ascending=False)
        total_rev = product_rev.sum()
        if total_rev > 0 and len(product_rev) > 0:
            top20_count = max(1, int(len(product_rev) * 0.2))
            top20_share = product_rev.head(top20_count).sum() / total_rev
            checks.append(
                CheckResult(
                    "P01",
                    "product",
                    "medium",
                    "pass" if 0.5 <= top20_share <= 0.8 else ("watch" if top20_share <= 0.9 else "fail"),
                    f"Top 20% SKU revenue concentration: {top20_share:.1%}",
                    top20_share,
                    0.8,
                )
            )

    # P05 — Converting SKU Rate
    if key:
        total_active = orders[key].nunique()
        selling = orders.groupby(key)["amount"].sum()
        converting = (selling > 0).sum()
        convert_rate = converting / total_active if total_active else 0
        if total_active == 0:
            checks.append(
                CheckResult(
                    "P05", "product", "high", "na", "No SKU/product data available for conversion analysis", None, 0.7
                )
            )
        else:
            checks.append(
                CheckResult(
                    "P05",
                    "product",
                    "high",
                    "pass" if convert_rate >= 0.7 else ("watch" if convert_rate >= 0.5 else "fail"),
                    f"Converting SKU rate: {convert_rate:.1%} ({converting}/{total_active})",
                    convert_rate,
                    0.7,
                )
            )

    # P06 — Multi-Item Order Rate
    if key:
        items_per_order = orders.groupby("order_id")[key].nunique()
        multi_item = (items_per_order > 1).mean() if len(items_per_order) else 0
        checks.append(
            CheckResult(
                "P06",
                "product",
                "medium",
                "pass" if multi_item >= 0.25 else ("watch" if multi_item >= 0.15 else "fail"),
                f"Multi-item order rate: {multi_item:.1%}",
                multi_item,
                0.25,
            )
        )

    # P07 — Cross-Sell Pair Lift
    if key:
        from .product import cross_sell_matrix

        xs = cross_sell_matrix(orders)
        high_lift = len(xs[xs["lift"] > 2.0]) if len(xs) else 0
        checks.append(
            CheckResult(
                "P07",
                "product",
                "medium",
                "pass" if high_lift >= 3 else ("watch" if high_lift >= 1 else "fail"),
                f"Cross-sell pairs with lift > 2.0: {high_lift}",
                high_lift,
                3,
            )
        )

    # P10 — Lifecycle Stage Distribution
    if key:
        from .product import product_lifecycle

        lifecycle = product_lifecycle(orders)
        if len(lifecycle):
            decline_pct = (lifecycle["lifecycle_stage"] == "Decline").mean()
            checks.append(
                CheckResult(
                    "P10",
                    "product",
                    "medium",
                    "pass" if decline_pct < 0.3 else ("watch" if decline_pct < 0.5 else "fail"),
                    f"Decline-stage products: {decline_pct:.1%}",
                    decline_pct,
                    0.3,
                )
            )

    # P19 — Price Tier Distribution
    if key:
        prices = orders.groupby(key)["amount"].mean()
        if len(prices) == 0:
            checks.append(
                CheckResult("P19", "product", "medium", "na", "No price data available for tier analysis", None, 3)
            )
        else:
            try:
                n_tiers = len(pd.qcut(prices, q=min(4, len(prices)), duplicates="drop").cat.categories)
            except (ValueError, TypeError):
                n_tiers = 1
            checks.append(
                CheckResult(
                    "P19",
                    "product",
                    "medium",
                    "pass" if n_tiers >= 3 else ("watch" if n_tiers >= 2 else "fail"),
                    f"Distinct price tiers: {n_tiers}",
                    n_tiers,
                    3,
                )
            )

    return checks


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def build_review_data(
    orders: pd.DataFrame,
    period: str | None = None,
    ref_date: date | None = None,
) -> dict:
    """Build the full review.json data structure.

    Parameters
    ----------
    orders : DataFrame
        Order transaction data with columns: order_id, order_date, customer_id, amount.
    period : str, optional
        One of ``"30d"``, ``"90d"``, ``"365d"``, or ``None`` (auto-select all covered).
    ref_date : date, optional
        Reference date for trailing windows. Defaults to max order date.
    """
    from .metrics import compute_cohort_kpis, compute_revenue_kpis

    ref = ref_date or orders["order_date"].max().date()

    # 1. Metadata
    metadata = _build_metadata(orders)

    # 2. Data coverage
    data_coverage = compute_data_coverage(orders)

    # 3. Determine which periods to compute
    if period:
        periods_to_compute = [period] if data_coverage.get(period, False) else []
    else:
        periods_to_compute = [p for p in ("30d", "90d", "365d") if data_coverage[p]]

    # 4. Compute period blocks
    period_days = {"30d": 30, "90d": 90, "365d": 365}
    periods_data: dict[str, dict] = {}
    for p in periods_to_compute:
        block = _compute_period_block(orders, ref, period_days[p])
        periods_data[p] = block

    # 5. Monthly trend + repeat purchase rate for 365d
    if "365d" in periods_data:
        periods_data["365d"]["monthly_trend"] = _compute_monthly_trend(orders, ref, days=365)

    # 6. Health checks on longest available period's data
    rev_kpis = compute_revenue_kpis(orders)
    cohort_kpis = compute_cohort_kpis(orders)
    checks = _build_checks(rev_kpis, cohort_kpis, orders)

    # 6a. Add repeat_purchase_rate to 365d block (computed from all data)
    if "365d" in periods_data:
        periods_data["365d"]["repeat_purchase_rate"] = cohort_kpis.get("repeat_purchase_rate", 0.0)

    # 6b. Data quality warnings
    data_quality: list[dict] = []
    data_span_days = (orders["order_date"].max() - orders["order_date"].min()).days

    if rev_kpis.get("partial_last_month"):
        data_quality.append(
            {
                "type": "partial_period",
                "period": rev_kpis["partial_last_month_label"],
                "days_with_data": rev_kpis["partial_last_month_days"],
                "message": (
                    f"Latest month ({rev_kpis['partial_last_month_label']}) has only "
                    f"{rev_kpis['partial_last_month_days']} days of data. "
                    "MoM comparisons use prior complete months."
                ),
            }
        )

    if data_span_days < 90:
        data_quality.append(
            {
                "type": "short_data_span",
                "days": data_span_days,
                "message": (
                    f"Data spans only {data_span_days} days. "
                    "90d and 365d analyses are unavailable; interpret results with caution."
                ),
            }
        )
    elif data_span_days < 365:
        data_quality.append(
            {
                "type": "limited_data_span",
                "days": data_span_days,
                "message": (
                    f"Data spans {data_span_days} days (<1 year). "
                    "365d analysis may be unavailable; year-over-year comparisons are limited."
                ),
            }
        )

    # Annualize revenue
    total_revenue = rev_kpis["total_revenue"]
    if 0 < data_span_days < 365:
        annual_revenue = total_revenue * (365 / data_span_days)
    else:
        annual_revenue = total_revenue
    if annual_revenue <= 0:
        annual_revenue = 0.0

    # 8. Top issues + action candidates
    top_issues = build_top_issues(checks, annual_revenue)
    action_candidates = build_action_candidates(top_issues)

    # 9. Assemble review.json
    from . import __version__

    review_data = {
        "version": __version__,
        "metadata": metadata,
        "data_quality": data_quality,
        "data_coverage": data_coverage,
        "periods": periods_data,
        "health": {
            "checks": [
                {
                    "id": c.check_id,
                    "category": c.category,
                    "severity": c.severity,
                    "result": c.result,
                    "message": c.message,
                    "value": c.current_value,
                    "threshold": c.threshold,
                }
                for c in checks
            ],
            "top_issues": top_issues,
        },
        "action_candidates": action_candidates,
    }

    return review_data
