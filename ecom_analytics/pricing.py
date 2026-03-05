"""Price and discount analysis."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class DiscountResult:
    """Discount dependency analysis output."""

    avg_discount_rate: float
    discounted_order_ratio: float
    discount_rate_trend: str  # "increasing", "stable", "decreasing"
    monthly_discount_rates: dict


@dataclass
class MarginResult:
    """Margin analysis output."""

    overall_margin: float
    margin_by_category: dict
    negative_margin_categories: list[str]


@dataclass
class ThresholdResult:
    """Free-shipping threshold analysis output."""

    current_aov: float
    suggested_threshold: float
    orders_below_threshold_pct: float
    potential_aov_lift: float


def discount_dependency(orders: pd.DataFrame) -> DiscountResult:
    """Analyse discount dependency across orders."""
    if "discount" not in orders.columns:
        return DiscountResult(
            avg_discount_rate=0.0,
            discounted_order_ratio=0.0,
            discount_rate_trend="stable",
            monthly_discount_rates={},
        )

    orders = orders.copy()
    gross = orders["amount"] + orders["discount"]
    overall_rate = orders["discount"].sum() / gross.sum() if gross.sum() else 0

    discounted = orders["discount"] > 0
    ratio = discounted.mean()

    # Monthly trend
    orders["month"] = orders["order_date"].dt.to_period("M")
    monthly = orders.groupby("month").apply(
        lambda g: g["discount"].sum() / (g["amount"] + g["discount"]).sum()
        if (g["amount"] + g["discount"]).sum()
        else 0
    )

    if len(monthly) >= 3:
        slope = np.polyfit(range(len(monthly)), monthly.values, 1)[0]
        trend = "increasing" if slope > 0.005 else ("decreasing" if slope < -0.005 else "stable")
    else:
        trend = "stable"

    return DiscountResult(
        avg_discount_rate=float(overall_rate),
        discounted_order_ratio=float(ratio),
        discount_rate_trend=trend,
        monthly_discount_rates={str(k): float(v) for k, v in monthly.items()},
    )


def price_elasticity_simple(orders: pd.DataFrame) -> pd.DataFrame:
    """Estimate simple price elasticity per product.

    Groups orders into price buckets and computes quantity sensitivity.
    This is a rough heuristic — not a causal estimate.
    """
    key = "sku" if "sku" in orders.columns else "product_name"
    if key not in orders.columns:
        return pd.DataFrame()

    price_col = "item_price" if "item_price" in orders.columns else "amount"
    qty_col = "quantity" if "quantity" in orders.columns else None

    results = []
    for prod, grp in orders.groupby(key):
        if len(grp) < 10:
            continue
        prices = grp[price_col]
        quantities = grp[qty_col] if qty_col else pd.Series(1, index=grp.index)
        if prices.std() == 0:
            continue
        # Simple log-log regression: ln(Q) = a + e*ln(P)
        log_p = np.log(prices.clip(lower=0.01))
        log_q = np.log(quantities.clip(lower=0.01))
        if log_p.std() == 0:
            continue
        elasticity = np.corrcoef(log_p, log_q)[0, 1] * (log_q.std() / log_p.std())
        results.append({key: prod, "elasticity": float(elasticity), "n_obs": len(grp)})

    return pd.DataFrame(results)


def margin_analysis(
    orders: pd.DataFrame, cost_col: str = "cost"
) -> MarginResult:
    """Compute gross margin overall and by category."""
    if cost_col not in orders.columns:
        return MarginResult(overall_margin=float("nan"), margin_by_category={}, negative_margin_categories=[])

    revenue = orders["amount"].sum()
    cost = orders[cost_col].sum()
    overall = (revenue - cost) / revenue if revenue else 0

    margin_by_cat: dict[str, float] = {}
    negative_cats: list[str] = []
    if "category" in orders.columns:
        for cat, grp in orders.groupby("category"):
            r = grp["amount"].sum()
            c = grp[cost_col].sum()
            m = (r - c) / r if r else 0
            margin_by_cat[str(cat)] = float(m)
            if m < 0:
                negative_cats.append(str(cat))

    return MarginResult(
        overall_margin=float(overall),
        margin_by_category=margin_by_cat,
        negative_margin_categories=negative_cats,
    )


def free_shipping_threshold(orders: pd.DataFrame) -> ThresholdResult:
    """Suggest an optimal free-shipping threshold based on AOV distribution."""
    aov_per_order = orders.groupby("order_id")["amount"].sum()
    current_aov = float(aov_per_order.mean())

    # Suggest threshold at ~120% of median to encourage upsell
    median_val = float(aov_per_order.median())
    suggested = round(median_val * 1.2, -2)  # round to nearest 100

    below = (aov_per_order < suggested).mean()

    # Potential AOV lift: orders just below threshold would increase
    near_threshold = aov_per_order[(aov_per_order >= suggested * 0.8) & (aov_per_order < suggested)]
    if len(near_threshold):
        lift = (suggested - near_threshold.mean()) / current_aov
    else:
        lift = 0.0

    return ThresholdResult(
        current_aov=current_aov,
        suggested_threshold=float(suggested),
        orders_below_threshold_pct=float(below),
        potential_aov_lift=float(lift),
    )
