"""Product analysis — ABC classification, cross-sell, lifecycle."""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd


def abc_analysis(orders: pd.DataFrame, metric: str = "revenue") -> pd.DataFrame:
    """Classify products into A/B/C tiers by cumulative revenue share.

    A = top 80%, B = next 15%, C = remaining 5%.
    """
    key = "sku" if "sku" in orders.columns else "product_name"
    if metric == "revenue":
        prod = orders.groupby(key)["amount"].sum().sort_values(ascending=False)
    else:
        prod = orders.groupby(key).size().sort_values(ascending=False)

    prod = prod.reset_index()
    prod.columns = [key, metric]
    total = prod[metric].sum()
    prod["cumulative_share"] = prod[metric].cumsum() / total

    def _rank(share: float) -> str:
        if share <= 0.80:
            return "A"
        if share <= 0.95:
            return "B"
        return "C"

    prod["abc_rank"] = prod["cumulative_share"].apply(_rank)
    prod["revenue_share"] = prod[metric] / total
    return prod


def cross_sell_matrix(
    orders: pd.DataFrame, min_support: float = 0.01
) -> pd.DataFrame:
    """Find co-purchased product pairs with lift > 1.

    Returns a DataFrame with columns: product_a, product_b, support, lift.
    """
    key = "sku" if "sku" in orders.columns else "product_name"
    basket = orders.groupby("order_id")[key].apply(set)
    n_orders = len(basket)
    min_count = max(2, int(n_orders * min_support))

    # Single item frequencies
    from collections import Counter

    item_counts: Counter[str] = Counter()
    pair_counts: Counter[tuple[str, str]] = Counter()

    for items in basket:
        items = {i for i in items if i is not None}
        for item in items:
            item_counts[item] += 1
        for pair in combinations(sorted(items), 2):
            pair_counts[pair] += 1

    rows = []
    for (a, b), count in pair_counts.items():
        if count < min_count:
            continue
        support = count / n_orders
        pa = item_counts[a] / n_orders
        pb = item_counts[b] / n_orders
        lift = support / (pa * pb) if (pa * pb) else 0
        rows.append({"product_a": a, "product_b": b, "support": support, "lift": lift, "count": count})

    df = pd.DataFrame(rows)
    if len(df):
        df = df.sort_values("lift", ascending=False).reset_index(drop=True)
    return df


def product_lifecycle(
    orders: pd.DataFrame, products: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Assign lifecycle stage (Launch / Growth / Mature / Decline) per product.

    Uses 3-month trailing revenue trend.
    """
    key = "sku" if "sku" in orders.columns else "product_name"
    orders = orders.copy()
    orders["month"] = orders["order_date"].dt.to_period("M")

    monthly = orders.groupby([key, "month"])["amount"].sum().reset_index()
    monthly = monthly.sort_values(["month"])

    results = []
    for prod_id, grp in monthly.groupby(key):
        if len(grp) < 2:
            stage = "Launch"
        else:
            recent = grp.tail(3)["amount"].values
            if len(recent) < 2:
                stage = "Launch"
            else:
                slope = np.polyfit(range(len(recent)), recent, 1)[0]
                mean_val = recent.mean()
                rel_slope = slope / mean_val if mean_val else 0
                if rel_slope > 0.10:
                    stage = "Growth"
                elif rel_slope < -0.10:
                    stage = "Decline"
                else:
                    stage = "Mature"
        results.append(
            {
                key: prod_id,
                "total_revenue": float(grp["amount"].sum()),
                "months_active": int(grp["month"].nunique()),
                "lifecycle_stage": stage,
            }
        )
    return pd.DataFrame(results)


def category_performance(orders: pd.DataFrame) -> pd.DataFrame:
    """Revenue and order stats by product category."""
    if "category" not in orders.columns:
        return pd.DataFrame()
    agg = orders.groupby("category").agg(
        revenue=("amount", "sum"),
        orders=("order_id", "nunique"),
        avg_price=("amount", "mean"),
    )
    total = agg["revenue"].sum()
    agg["revenue_share"] = agg["revenue"] / total if total else 0
    return agg.sort_values("revenue", ascending=False).reset_index()
