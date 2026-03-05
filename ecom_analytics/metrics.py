"""KPI calculation engine for ecommerce datasets."""

from __future__ import annotations

import numpy as np
import pandas as pd


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
    orders["is_new"] = orders["order_date"] == orders["first_order"]
    repeat_revenue_share = (
        orders.loc[~orders["is_new"], "amount"].sum() / total_revenue
        if total_revenue
        else 0
    )

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
    daily_cv = daily.std() / daily.mean() if daily.mean() else 0

    return {
        "total_revenue": float(total_revenue),
        "total_orders": int(total_orders),
        "aov": float(avg_aov),
        "mom_growth_latest": float(monthly["mom_growth"].iloc[-1]) if len(monthly) > 1 else 0.0,
        "repeat_revenue_share": float(repeat_revenue_share),
        "avg_discount_rate": float(avg_discount_rate),
        "top10_customer_share": float(top10_share),
        "daily_revenue_cv": float(daily_cv),
        "monthly_revenue": monthly["revenue"].to_dict(),
        "monthly_aov": monthly["aov"].to_dict(),
        "monthly_orders": monthly["order_count"].to_dict(),
    }


def compute_product_kpis(orders: pd.DataFrame, products: pd.DataFrame) -> dict:
    """Compute product-level KPIs.

    ``orders`` should have per-line-item rows with ``sku`` or ``product_name``.
    """
    join_col = "sku" if "sku" in orders.columns and "sku" in products.columns else None
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

    # F2 rate: customers who ordered at least twice
    order_counts = orders.groupby("customer_id")["order_id"].nunique()
    f2_rate = (order_counts >= 2).mean() if len(order_counts) else 0

    # Average purchase interval
    cust_dates = orders.groupby("customer_id")["order_date"].apply(
        lambda s: s.sort_values().diff().dt.days.mean()
    )
    avg_purchase_interval = float(cust_dates.mean()) if not cust_dates.isna().all() else float("nan")

    return {
        "total_customers": int(total_customers),
        "f2_rate": float(f2_rate),
        "avg_purchase_interval_days": avg_purchase_interval,
    }


def compute_revenue_kpis_from_analytics(data) -> dict:
    """Compute revenue KPIs from Shopify Analytics aggregated exports.

    *data* is an ``AnalyticsData`` instance from ``load_shopify_analytics()``.
    """
    kpis: dict = {}
    sales = data.sales
    if sales is None:
        return kpis

    # Exclude partial months (< 15 days from period end)
    sales = sales.copy()

    total_revenue = float(sales["Total sales"].sum())
    total_orders = int(sales["Orders"].sum())
    total_gross = float(sales["Gross sales"].sum())
    total_discounts = float(sales["Discounts"].sum())
    total_returns = float(sales["Returns"].sum())
    total_net = float(sales["Net sales"].sum())

    aov = total_revenue / total_orders if total_orders else 0

    # MoM growth — use the last two full months
    if len(sales) >= 3:
        # Last row may be partial month; use second-to-last for latest full month
        latest = sales.iloc[-2]["Total sales"]
        prior = sales.iloc[-3]["Total sales"]
        mom_growth = (latest - prior) / prior if prior else 0
    elif len(sales) >= 2:
        latest = sales.iloc[-1]["Total sales"]
        prior = sales.iloc[-2]["Total sales"]
        mom_growth = (latest - prior) / prior if prior else 0
    else:
        mom_growth = 0.0

    # Discount rate
    discount_rate = total_discounts / total_gross if total_gross else 0
    # Return rate
    return_rate = total_returns / total_gross if total_gross else 0

    # Monthly series for charts
    monthly_revenue = dict(zip(
        sales["Month"].dt.strftime("%Y-%m"),
        sales["Total sales"],
    ))
    monthly_orders = dict(zip(
        sales["Month"].dt.strftime("%Y-%m"),
        sales["Orders"],
    ))
    monthly_aov = {
        m: rev / orders if orders else 0
        for m, rev, orders in zip(
            sales["Month"].dt.strftime("%Y-%m"),
            sales["Total sales"],
            sales["Orders"],
        )
    }

    # MoM growth series
    sales_sorted = sales.sort_values("Month")
    mom_series = sales_sorted["Total sales"].pct_change()

    kpis.update({
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "total_gross_sales": total_gross,
        "total_discounts": total_discounts,
        "total_returns": total_returns,
        "total_net_sales": total_net,
        "aov": float(aov),
        "mom_growth_latest": float(mom_growth),
        "avg_discount_rate": float(discount_rate),
        "return_rate": float(return_rate),
        "monthly_revenue": monthly_revenue,
        "monthly_orders": monthly_orders,
        "monthly_aov": monthly_aov,
        # Not available from aggregated data
        "repeat_revenue_share": 0.0,
        "top10_customer_share": 0.0,
        "daily_revenue_cv": 0.0,
    })

    # Override repeat metrics from customer segments if available
    customers = data.customers
    if customers is not None:
        returning = customers[customers["New or returning customer"] == "Returning"]
        new = customers[customers["New or returning customer"] == "New"]
        total_returning_sales = returning["Total sales"].sum()
        total_new_sales = new["Total sales"].sum()
        total_cust_sales = total_returning_sales + total_new_sales
        if total_cust_sales > 0:
            kpis["repeat_revenue_share"] = float(total_returning_sales / total_cust_sales)
        # Customer counts
        kpis["total_new_customers"] = int(new["Customers"].sum())
        kpis["total_returning_customers"] = int(returning["Customers"].sum())

    # Gross profit from profit data
    profit = data.profit
    if profit is not None and "Gross profit" in profit.columns:
        gross_profit = float(profit["Gross profit"].iloc[0])
        cogs = float(profit["Cost of goods sold"].iloc[0]) if "Cost of goods sold" in profit.columns else 0
        net_sales_profit = float(profit["Net sales"].iloc[0]) if "Net sales" in profit.columns else total_net
        kpis["gross_profit"] = gross_profit
        kpis["cogs"] = cogs
        kpis["gross_margin"] = gross_profit / net_sales_profit if net_sales_profit else 0

    return kpis


def compute_funnel_kpis_from_analytics(data) -> dict:
    """Compute conversion funnel KPIs from Shopify Analytics exports."""
    kpis: dict = {}
    conv = data.conversion
    if conv is None:
        return kpis

    total_sessions = int(conv["Sessions"].sum())
    total_cart = int(conv["Sessions with cart additions"].sum())
    total_checkout = int(conv["Sessions that reached checkout"].sum())
    total_completed = int(conv["Sessions that completed checkout"].sum())

    overall_cvr = total_completed / total_sessions if total_sessions else 0
    cart_rate = total_cart / total_sessions if total_sessions else 0
    checkout_rate = total_checkout / total_cart if total_cart else 0
    purchase_rate = total_completed / total_checkout if total_checkout else 0

    # Cart abandonment = reached cart but didn't complete checkout
    cart_abandonment = 1 - (total_completed / total_cart) if total_cart else 0
    # Checkout abandonment = reached checkout but didn't complete
    checkout_abandonment = 1 - (total_completed / total_checkout) if total_checkout else 0

    # Latest month CVR vs average
    if len(conv) >= 2:
        latest_cvr = float(conv.iloc[-2]["Conversion rate"]) if len(conv) >= 3 else float(conv.iloc[-1]["Conversion rate"])
    else:
        latest_cvr = overall_cvr

    # Monthly CVR series
    monthly_cvr = dict(zip(
        conv["Month"].dt.strftime("%Y-%m"),
        conv["Conversion rate"],
    ))

    kpis.update({
        "total_sessions": total_sessions,
        "total_cart_additions": total_cart,
        "total_checkout_reached": total_checkout,
        "total_checkout_completed": total_completed,
        "overall_cvr": float(overall_cvr),
        "cart_addition_rate": float(cart_rate),
        "checkout_rate": float(checkout_rate),
        "purchase_completion_rate": float(purchase_rate),
        "cart_abandonment_rate": float(cart_abandonment),
        "checkout_abandonment_rate": float(checkout_abandonment),
        "latest_month_cvr": float(latest_cvr),
        "monthly_cvr": monthly_cvr,
    })

    # Sessions data
    sessions = data.sessions
    if sessions is not None:
        total_visitors = int(sessions["Online store visitors"].sum())
        kpis["total_visitors"] = total_visitors

    return kpis


def compute_product_kpis_from_analytics(data) -> dict:
    """Compute product KPIs from Shopify Analytics product variant data."""
    kpis: dict = {}
    products = data.products
    if products is None:
        return kpis

    total_items = int(products["Net items sold"].sum())
    total_revenue = float(products["Net sales"].sum())
    total_skus = len(products)

    # Top 20% SKUs revenue share (Pareto)
    prod_sorted = products.sort_values("Net sales", ascending=False)
    top20_n = max(1, int(total_skus * 0.2))
    top20_share = prod_sorted.iloc[:top20_n]["Net sales"].sum() / total_revenue if total_revenue else 0

    # Revenue by product title (aggregate variants)
    by_product = products.groupby("Product title").agg({
        "Net items sold": "sum",
        "Net sales": "sum",
        "Gross sales": "sum",
        "Discounts": "sum",
        "Returns": "sum",
    }).sort_values("Net sales", ascending=False)
    total_products = len(by_product)

    # SKUs with zero or negative net sales
    zero_sales_skus = int((products["Net sales"] <= 0).sum())
    # SKU return rate
    products_with_returns = int((products["Returns"] > 0).sum())

    # Top 10 products by revenue
    top10_products = by_product.head(10).reset_index()[["Product title", "Net sales", "Net items sold"]]

    kpis.update({
        "total_skus": total_skus,
        "total_products": total_products,
        "total_items_sold": total_items,
        "total_product_revenue": float(total_revenue),
        "top20_sku_revenue_share": float(top20_share),
        "zero_sales_skus": zero_sales_skus,
        "skus_with_returns": products_with_returns,
        "top10_products": top10_products.to_dict("records"),
    })

    return kpis


def compute_retention_kpis_from_analytics(data) -> dict:
    """Compute retention/cohort-proxy KPIs from new vs returning customer data."""
    kpis: dict = {}
    customers = data.customers
    if customers is None:
        return kpis

    returning = customers[customers["New or returning customer"] == "Returning"]
    new = customers[customers["New or returning customer"] == "New"]

    total_returning_orders = int(returning["Orders"].sum())
    total_new_orders = int(new["Orders"].sum())
    total_orders = total_returning_orders + total_new_orders

    # Returning customer ratio (proxy for F2+)
    total_returning_customers = int(returning["Customers"].sum())
    total_new_customers = int(new["Customers"].sum())
    total_customers = total_returning_customers + total_new_customers

    returning_customer_ratio = total_returning_customers / total_customers if total_customers else 0
    returning_order_ratio = total_returning_orders / total_orders if total_orders else 0

    # Avg orders per returning customer
    avg_orders_per_returning = total_returning_orders / total_returning_customers if total_returning_customers else 0
    # Avg revenue per returning customer
    returning_revenue = float(returning["Total sales"].sum())
    new_revenue = float(new["Total sales"].sum())
    avg_rev_per_returning = returning_revenue / total_returning_customers if total_returning_customers else 0
    avg_rev_per_new = new_revenue / total_new_customers if total_new_customers else 0

    # Monthly new vs returning trend
    monthly_new = dict(zip(
        new.groupby("Month")["Customers"].sum().index.strftime("%Y-%m") if hasattr(new.groupby("Month")["Customers"].sum().index, 'strftime') else [],
        new.groupby("Month")["Customers"].sum().values,
    ))
    monthly_returning = dict(zip(
        returning.groupby("Month")["Customers"].sum().index.strftime("%Y-%m") if hasattr(returning.groupby("Month")["Customers"].sum().index, 'strftime') else [],
        returning.groupby("Month")["Customers"].sum().values,
    ))

    kpis.update({
        "total_customers": total_customers,
        "total_new_customers": total_new_customers,
        "total_returning_customers": total_returning_customers,
        "returning_customer_ratio": float(returning_customer_ratio),
        "returning_order_ratio": float(returning_order_ratio),
        "avg_orders_per_returning": float(avg_orders_per_returning),
        "avg_rev_per_returning": float(avg_rev_per_returning),
        "avg_rev_per_new": float(avg_rev_per_new),
        "returning_revenue": float(returning_revenue),
        "new_revenue": float(new_revenue),
        "monthly_new_customers": monthly_new,
        "monthly_returning_customers": monthly_returning,
        # Proxy F2 rate: returning / (new + returning) over full period
        "f2_rate": float(returning_customer_ratio),
        "avg_purchase_interval_days": float("nan"),  # Not available from aggregated data
    })

    return kpis


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
