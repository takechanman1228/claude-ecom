"""Cohort analysis, LTV estimation, and RFM segmentation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class LTVResult:
    """LTV estimation output."""

    avg_ltv: float
    median_ltv: float
    ltv_by_cohort: dict  # cohort_month → estimated LTV
    horizon_months: int


def build_cohort_matrix(
    orders: pd.DataFrame, period: str = "monthly"
) -> pd.DataFrame:
    """Build a cohort retention matrix.

    Returns a DataFrame where rows = cohort month, columns = period offset,
    values = number of unique customers active in that offset.
    """
    orders = orders.copy()
    orders["order_month"] = orders["order_date"].dt.to_period("M")
    first_month = (
        orders.groupby("customer_id")["order_month"]
        .min()
        .rename("cohort_month")
    )
    orders = orders.merge(first_month, on="customer_id", how="left")
    orders["period_offset"] = (
        orders["order_month"].astype(int) - orders["cohort_month"].astype(int)
    )

    matrix = (
        orders.groupby(["cohort_month", "period_offset"])["customer_id"]
        .nunique()
        .unstack(fill_value=0)
    )
    return matrix


def compute_retention_curve(cohort_matrix: pd.DataFrame) -> pd.Series:
    """Average retention rate across cohorts for each period offset.

    Values normalised against period-0 size (100%).
    """
    normalised = cohort_matrix.div(cohort_matrix[0], axis=0)
    return normalised.mean(axis=0)


def estimate_ltv(
    orders: pd.DataFrame, horizon_months: int = 12
) -> LTVResult:
    """Estimate per-customer LTV over a given horizon using historical spend.

    Simple approach: for each customer, compute total spend within
    *horizon_months* of their first purchase, then average.
    """
    orders = orders.copy()
    first_order = (
        orders.groupby("customer_id")["order_date"]
        .min()
        .rename("first_order_date")
    )
    orders = orders.merge(first_order, on="customer_id", how="left")
    cutoff = orders["first_order_date"] + pd.DateOffset(months=horizon_months)
    in_window = orders[orders["order_date"] <= cutoff]
    cust_spend = in_window.groupby("customer_id")["amount"].sum()

    # By cohort
    cust_cohort = (
        orders.groupby("customer_id")["first_order_date"]
        .first()
        .dt.to_period("M")
        .rename("cohort")
    )
    cust_data = pd.DataFrame({"spend": cust_spend, "cohort": cust_cohort})
    ltv_by_cohort = cust_data.groupby("cohort")["spend"].mean().to_dict()
    ltv_by_cohort = {str(k): float(v) for k, v in ltv_by_cohort.items()}

    return LTVResult(
        avg_ltv=float(cust_spend.mean()) if len(cust_spend) else 0.0,
        median_ltv=float(cust_spend.median()) if len(cust_spend) else 0.0,
        ltv_by_cohort=ltv_by_cohort,
        horizon_months=horizon_months,
    )


def rfm_segmentation(
    orders: pd.DataFrame, n_segments: int = 5
) -> pd.DataFrame:
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
    rfm["f_score"] = pd.qcut(
        rfm["frequency"].rank(method="first"), n_segments, labels=False, duplicates="drop"
    ) + 1
    rfm["m_score"] = pd.qcut(
        rfm["monetary"].rank(method="first"), n_segments, labels=False, duplicates="drop"
    ) + 1

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


def churn_risk_score(orders: pd.DataFrame) -> pd.DataFrame:
    """Assign a simple churn-risk score (0–1) per customer.

    Uses recency relative to average purchase interval.  Higher score = higher risk.
    """
    now = orders["order_date"].max()
    cust = orders.groupby("customer_id").agg(
        last_order=("order_date", "max"),
        order_count=("order_id", "nunique"),
        first_order=("order_date", "min"),
    )
    cust["recency_days"] = (now - cust["last_order"]).dt.days
    cust["tenure_days"] = (cust["last_order"] - cust["first_order"]).dt.days
    cust["avg_interval"] = cust["tenure_days"] / (cust["order_count"] - 1).clip(lower=1)
    cust["overdue_ratio"] = cust["recency_days"] / cust["avg_interval"].clip(lower=1)
    # Sigmoid-style normalisation
    cust["churn_risk"] = 1 / (1 + np.exp(-0.5 * (cust["overdue_ratio"] - 2)))
    return cust[["recency_days", "order_count", "avg_interval", "churn_risk"]].reset_index()
