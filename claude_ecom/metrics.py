"""KPI calculation engine for ecommerce datasets."""

from __future__ import annotations

import calendar
import math

import pandas as pd


def _safe_float(val: float) -> float:
    """Return NaN if val is NaN or inf, otherwise float(val)."""
    if math.isnan(val) or math.isinf(val):
        return float("nan")
    return float(val)


def compute_revenue_kpis(orders: pd.DataFrame) -> dict:
    """Compute revenue-related KPIs from an orders DataFrame.

    Expected columns: ``order_date``, ``amount``, ``order_id``, ``customer_id``.
    Optional: ``discount``.
    """
    orders = orders.copy()
    orders["month"] = orders["order_date"].dt.to_period("M")

    monthly = orders.groupby("month").agg(
        revenue=("amount", "sum"),
        order_count=("order_id", "nunique"),
    )
    monthly["aov"] = monthly["revenue"] / monthly["order_count"]
    monthly["mom_growth"] = monthly["revenue"].pct_change()

    total_revenue = orders["amount"].sum()
    total_orders = orders["order_id"].nunique()
    avg_aov = total_revenue / total_orders if total_orders else 0

    # New vs repeat
    first_order = orders.groupby("customer_id")["order_date"].min().rename("first_order")
    orders = orders.merge(first_order, on="customer_id", how="left")
    # Normalize both sides to date-only to avoid tz/time mismatches
    orders["is_new"] = orders["order_date"].dt.normalize() == orders["first_order"].dt.normalize()
    repeat_revenue_share = orders.loc[~orders["is_new"], "amount"].sum() / total_revenue if total_revenue else 0

    # Discount
    avg_discount_rate = 0.0
    if "discount" in orders.columns:
        gross = orders["amount"] + orders["discount"]
        avg_discount_rate = (orders["discount"].sum() / gross.sum()) if gross.sum() else 0

    # Revenue concentration (top 10% customers)
    cust_rev = orders.groupby("customer_id")["amount"].sum().sort_values(ascending=False)
    top10_pct = int(max(1, len(cust_rev) * 0.1))
    top10_share = cust_rev.iloc[:top10_pct].sum() / total_revenue if total_revenue else 0

    # Daily CV
    daily = orders.groupby(orders["order_date"].dt.date)["amount"].sum()
    if len(daily) > 1 and daily.mean():
        daily_cv = daily.std() / daily.mean()
        daily_cv = _safe_float(daily_cv)
    else:
        daily_cv = float("nan")

    # Partial last month detection
    last_period = monthly.index[-1] if len(monthly) else None
    partial_last_month = False
    partial_last_month_days = 0
    partial_last_month_label = ""
    if last_period is not None:
        lp_year = last_period.start_time.year
        lp_month = last_period.start_time.month
        days_in_month = calendar.monthrange(lp_year, lp_month)[1]
        # Count actual days with data in the last month
        last_month_dates = orders.loc[orders["month"] == last_period, "order_date"].dt.date.nunique()
        partial_last_month_days = int(last_month_dates)
        partial_last_month_label = f"{lp_year}-{lp_month:02d}"
        if last_month_dates < days_in_month / 2:
            partial_last_month = True

    # MoM growth — guard NaN/inf; skip partial last month
    if partial_last_month and len(monthly) > 2:
        # Use the two most recent complete months
        raw_mom = monthly["mom_growth"].iloc[-2]
        mom_growth_latest = _safe_float(raw_mom)
    elif not partial_last_month and len(monthly) > 1:
        raw_mom = monthly["mom_growth"].iloc[-1]
        mom_growth_latest = _safe_float(raw_mom)
    else:
        mom_growth_latest = float("nan")

    return {
        "total_revenue": float(total_revenue),
        "total_orders": int(total_orders),
        "aov": float(avg_aov),
        "mom_growth_latest": float(mom_growth_latest),
        "repeat_revenue_share": float(repeat_revenue_share),
        "avg_discount_rate": float(avg_discount_rate),
        "top10_customer_share": float(top10_share),
        "daily_revenue_cv": float(daily_cv),
        "monthly_revenue": monthly["revenue"].to_dict(),
        "monthly_aov": monthly["aov"].to_dict(),
        "monthly_orders": monthly["order_count"].to_dict(),
        "partial_last_month": partial_last_month,
        "partial_last_month_days": partial_last_month_days,
        "partial_last_month_label": partial_last_month_label,
    }


def compute_product_kpis(orders: pd.DataFrame, products: pd.DataFrame) -> dict:
    """Compute product-level KPIs.

    ``orders`` should have per-line-item rows with ``sku`` or ``product_name``.
    """
    total_revenue = orders["amount"].sum()

    # Product revenue ranking
    if "sku" in orders.columns:
        prod_rev = orders.groupby("sku")["amount"].sum().sort_values(ascending=False)
    elif "product_name" in orders.columns:
        prod_rev = orders.groupby("product_name")["amount"].sum().sort_values(ascending=False)
    else:
        prod_rev = pd.Series(dtype=float)

    # Pareto — top 20% share
    top20_n = int(max(1, len(prod_rev) * 0.2))
    top20_share = prod_rev.iloc[:top20_n].sum() / total_revenue if total_revenue else 0

    # Multi-item order rate
    items_per_order = orders.groupby("order_id").size()
    multi_item_rate = (items_per_order > 1).mean() if len(items_per_order) else 0

    total_skus = int(products["product_id"].nunique()) if "product_id" in products.columns else 0

    return {
        "total_skus": total_skus,
        "top20_revenue_share": float(top20_share),
        "multi_item_order_rate": float(multi_item_rate),
    }


def compute_cohort_kpis(orders: pd.DataFrame) -> dict:
    """Compute retention / cohort KPIs from orders."""
    orders = orders.copy()
    orders["order_month"] = orders["order_date"].dt.to_period("M")

    first_month = orders.groupby("customer_id")["order_month"].min().rename("cohort_month")
    orders = orders.merge(first_month, on="customer_id", how="left")

    total_customers = orders["customer_id"].nunique()

    # Repeat purchase rate: customers who ordered at least twice
    order_counts = orders.groupby("customer_id")["order_id"].nunique()
    repeat_purchase_rate = (order_counts >= 2).mean() if len(order_counts) else 0

    # Average purchase interval
    cust_dates = orders.groupby("customer_id")["order_date"].apply(lambda s: s.sort_values().diff().dt.days.mean())
    avg_purchase_interval = float(cust_dates.mean()) if not cust_dates.isna().all() else float("nan")

    return {
        "total_customers": int(total_customers),
        "repeat_purchase_rate": float(repeat_purchase_rate),
        "avg_purchase_interval_days": avg_purchase_interval,
    }


def compute_inventory_kpis(inventory: pd.DataFrame, orders: pd.DataFrame) -> dict:
    """Compute inventory-level KPIs."""
    total_skus = int(inventory["sku"].nunique())

    # Stockout SKUs
    stockout_skus = int((inventory["quantity_on_hand"] <= 0).sum())
    stockout_rate = stockout_skus / total_skus if total_skus else 0

    # Overstock (90+ days)
    if "days_on_hand" in inventory.columns:
        overstock_skus = int((inventory["days_on_hand"] > 90).sum())
    else:
        overstock_skus = 0

    # Inventory value
    if "cost" in inventory.columns:
        total_inventory_value = float((inventory["quantity_on_hand"] * inventory["cost"]).sum())
    else:
        total_inventory_value = float("nan")

    return {
        "total_skus": total_skus,
        "stockout_skus": stockout_skus,
        "stockout_rate": float(stockout_rate),
        "overstock_skus": overstock_skus,
        "total_inventory_value": total_inventory_value,
    }
