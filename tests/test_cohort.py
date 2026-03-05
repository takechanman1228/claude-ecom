"""Tests for ecom_analytics.cohort."""

import os
import pytest
import pandas as pd

from ecom_analytics.loader import load_orders
from ecom_analytics.cohort import (
    build_cohort_matrix,
    compute_retention_curve,
    estimate_ltv,
    rfm_segmentation,
    churn_risk_score,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
ORDERS_CSV = os.path.join(FIXTURES, "sample_orders.csv")


@pytest.fixture
def orders():
    return load_orders(ORDERS_CSV)


class TestCohortMatrix:
    def test_returns_dataframe(self, orders):
        matrix = build_cohort_matrix(orders)
        assert isinstance(matrix, pd.DataFrame)

    def test_period_zero_has_all_customers(self, orders):
        matrix = build_cohort_matrix(orders)
        # Period 0 should be the cohort acquisition month — values > 0
        assert (matrix[0] > 0).all()


class TestRetentionCurve:
    def test_returns_series(self, orders):
        matrix = build_cohort_matrix(orders)
        curve = compute_retention_curve(matrix)
        assert isinstance(curve, pd.Series)

    def test_starts_at_one(self, orders):
        matrix = build_cohort_matrix(orders)
        curve = compute_retention_curve(matrix)
        assert abs(curve.iloc[0] - 1.0) < 0.01


class TestEstimateLTV:
    def test_returns_result(self, orders):
        ltv = estimate_ltv(orders, horizon_months=12)
        assert ltv.avg_ltv > 0
        assert ltv.horizon_months == 12

    def test_ltv_by_cohort_not_empty(self, orders):
        ltv = estimate_ltv(orders, horizon_months=12)
        assert len(ltv.ltv_by_cohort) > 0


class TestRFMSegmentation:
    def test_returns_dataframe(self, orders):
        rfm = rfm_segmentation(orders)
        assert isinstance(rfm, pd.DataFrame)

    def test_has_segment_column(self, orders):
        rfm = rfm_segmentation(orders)
        assert "segment" in rfm.columns

    def test_valid_segments(self, orders):
        rfm = rfm_segmentation(orders)
        valid = {"Champions", "Loyal", "New Customers", "At Risk", "Lost", "Potential"}
        assert set(rfm["segment"].unique()).issubset(valid)


class TestChurnRisk:
    def test_returns_dataframe(self, orders):
        risk = churn_risk_score(orders)
        assert isinstance(risk, pd.DataFrame)

    def test_risk_bounded(self, orders):
        risk = churn_risk_score(orders)
        assert (risk["churn_risk"] >= 0).all()
        assert (risk["churn_risk"] <= 1).all()
