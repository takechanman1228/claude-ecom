"""Tests for ecom_analytics.decomposition."""

import os
import pytest

from ecom_analytics.loader import load_orders
from ecom_analytics.decomposition import (
    decompose_revenue,
    detect_anomalies,
    waterfall_analysis,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
ORDERS_CSV = os.path.join(FIXTURES, "sample_orders.csv")


@pytest.fixture
def orders():
    return load_orders(ORDERS_CSV)


class TestDecomposeRevenue:
    def test_returns_result(self, orders):
        result = decompose_revenue(orders)
        assert hasattr(result, "table")
        assert hasattr(result, "summary")

    def test_table_has_expected_columns(self, orders):
        result = decompose_revenue(orders)
        for col in ("revenue", "orders", "aov"):
            assert col in result.table.columns

    def test_summary_keys(self, orders):
        result = decompose_revenue(orders)
        assert "consecutive_growth_months" in result.summary
        assert "aov_trend" in result.summary


class TestDetectAnomalies:
    def test_returns_list(self, orders):
        anomalies = detect_anomalies(orders, metric="revenue")
        assert isinstance(anomalies, list)

    def test_anomaly_structure(self, orders):
        anomalies = detect_anomalies(orders, metric="revenue")
        if anomalies:
            a = anomalies[0]
            assert hasattr(a, "date")
            assert hasattr(a, "value")
            assert a.direction in ("above", "below")


class TestWaterfallAnalysis:
    def test_returns_result(self, orders):
        result = waterfall_analysis(orders, "2025-03", "2025-06")
        assert hasattr(result, "total_change")
        assert "aov_effect" in result.components
        assert "order_count_effect" in result.components
