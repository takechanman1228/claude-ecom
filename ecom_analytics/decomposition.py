"""Revenue decomposition and trend analysis."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class DecompositionResult:
    """Monthly decomposition of revenue into components."""

    table: pd.DataFrame  # columns: month, revenue, orders, aov, (sessions, cvr if available)
    summary: dict


@dataclass
class AnomalyPoint:
    """A single anomaly detected in the time series."""

    date: str
    metric: str
    value: float
    expected_range: tuple[float, float]
    direction: str  # "above" | "below"


@dataclass
class WaterfallResult:
    """Revenue change waterfall between two periods."""

    period1: str
    period2: str
    total_change: float
    components: dict  # e.g. {"order_count_effect": ..., "aov_effect": ...}


def decompose_revenue(
    orders: pd.DataFrame, period: str = "monthly"
) -> DecompositionResult:
    """Decompose revenue = orders × AOV (and sessions × CVR × AOV if session data present).

    Parameters
    ----------
    period : str
        ``"monthly"`` or ``"weekly"``.
    """
    orders = orders.copy()
    if period == "weekly":
        orders["period"] = orders["order_date"].dt.isocalendar().week
    else:
        orders["period"] = orders["order_date"].dt.to_period("M")

    agg = orders.groupby("period").agg(
        revenue=("amount", "sum"),
        orders=("order_id", "nunique"),
        customers=("customer_id", "nunique"),
    )
    agg["aov"] = agg["revenue"] / agg["orders"]
    agg["revenue_mom"] = agg["revenue"].pct_change()
    agg["orders_mom"] = agg["orders"].pct_change()
    agg["aov_mom"] = agg["aov"].pct_change()

    summary = {
        "avg_mom_revenue_growth": float(agg["revenue_mom"].mean()),
        "consecutive_growth_months": _consecutive_growth(agg["revenue_mom"]),
        "aov_trend": _trend_direction(agg["aov"]),
        "orders_trend": _trend_direction(agg["orders"]),
    }

    return DecompositionResult(table=agg.reset_index(), summary=summary)


def detect_anomalies(
    orders: pd.DataFrame, metric: str = "revenue", method: str = "iqr"
) -> list[AnomalyPoint]:
    """Detect anomalies in daily metric using IQR method."""
    daily = orders.groupby(orders["order_date"].dt.date).agg(
        revenue=("amount", "sum"),
        orders=("order_id", "nunique"),
    )
    if metric == "aov":
        daily["aov"] = daily["revenue"] / daily["orders"]

    series = daily[metric]
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    anomalies: list[AnomalyPoint] = []
    for date, value in series.items():
        if value < lower:
            anomalies.append(
                AnomalyPoint(
                    date=str(date),
                    metric=metric,
                    value=float(value),
                    expected_range=(float(lower), float(upper)),
                    direction="below",
                )
            )
        elif value > upper:
            anomalies.append(
                AnomalyPoint(
                    date=str(date),
                    metric=metric,
                    value=float(value),
                    expected_range=(float(lower), float(upper)),
                    direction="above",
                )
            )
    return anomalies


def waterfall_analysis(
    orders: pd.DataFrame, period1: str, period2: str
) -> WaterfallResult:
    """Compute revenue change waterfall between two monthly periods.

    *period1* and *period2* should be strings like ``"2026-01"``.
    """
    orders = orders.copy()
    orders["month"] = orders["order_date"].dt.to_period("M").astype(str)

    def _period_stats(month: str) -> dict:
        sub = orders[orders["month"] == month]
        rev = sub["amount"].sum()
        n = sub["order_id"].nunique()
        aov = rev / n if n else 0
        return {"revenue": rev, "orders": n, "aov": aov}

    s1 = _period_stats(period1)
    s2 = _period_stats(period2)

    # Decompose: ΔRevenue = ΔAOV × Orders_1 + ΔOrders × AOV_2
    d_aov = s2["aov"] - s1["aov"]
    d_orders = s2["orders"] - s1["orders"]
    aov_effect = d_aov * s1["orders"]
    order_effect = d_orders * s2["aov"]

    return WaterfallResult(
        period1=period1,
        period2=period2,
        total_change=float(s2["revenue"] - s1["revenue"]),
        components={
            "aov_effect": float(aov_effect),
            "order_count_effect": float(order_effect),
        },
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _consecutive_growth(series: pd.Series) -> int:
    """Count trailing consecutive periods of positive growth."""
    count = 0
    for val in reversed(series.dropna().values):
        if val > 0:
            count += 1
        else:
            break
    return count


def _trend_direction(series: pd.Series) -> str:
    """Return ``"up"``, ``"down"``, or ``"stable"`` based on simple linear fit."""
    if len(series) < 2:
        return "stable"
    x = np.arange(len(series))
    slope = np.polyfit(x, series.values.astype(float), 1)[0]
    mean_val = series.mean()
    if mean_val == 0:
        return "stable"
    rel_slope = slope / mean_val
    if rel_slope > 0.02:
        return "up"
    elif rel_slope < -0.02:
        return "down"
    return "stable"
