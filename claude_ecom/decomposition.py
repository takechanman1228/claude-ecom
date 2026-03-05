"""Revenue decomposition and trend analysis."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class WaterfallResult:
    """Revenue change waterfall between two periods."""

    period1: str
    period2: str
    total_change: float
    components: dict  # e.g. {"order_count_effect": ..., "aov_effect": ...}


def waterfall_analysis(orders: pd.DataFrame, period1: str, period2: str) -> WaterfallResult:
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
