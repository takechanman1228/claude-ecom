"""Cohort analysis and RFM segmentation."""

from __future__ import annotations

import pandas as pd


def rfm_segmentation(orders: pd.DataFrame, n_segments: int = 5) -> pd.DataFrame:
    """Compute RFM scores and assign customer segments.

    Returns a DataFrame with columns: customer_id, recency_days,
    frequency, monetary, r_score, f_score, m_score, segment.
    """
    now = orders["order_date"].max()
    rfm = orders.groupby("customer_id").agg(
        recency_days=("order_date", lambda x: (now - x.max()).days),
        frequency=("order_id", "nunique"),
        monetary=("amount", "sum"),
    )

    # Quintile scoring (1=worst, 5=best for F and M; inverted for R)
    rfm["r_score"] = pd.qcut(rfm["recency_days"], n_segments, labels=False, duplicates="drop")
    rfm["r_score"] = n_segments - rfm["r_score"]  # lower recency = better
    rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), n_segments, labels=False, duplicates="drop") + 1
    rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first"), n_segments, labels=False, duplicates="drop") + 1

    rfm["rfm_sum"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

    def _label(row: pd.Series) -> str:
        r, f = row["r_score"], row["f_score"]
        if r >= 4 and f >= 4:
            return "Champions"
        if r >= 3 and f >= 3:
            return "Loyal"
        if r >= 4 and f <= 2:
            return "New Customers"
        if r <= 2 and f >= 3:
            return "At Risk"
        if r <= 2 and f <= 2:
            return "Lost"
        return "Potential"

    rfm["segment"] = rfm.apply(_label, axis=1)
    return rfm.reset_index()
