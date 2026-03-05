"""Tests for the business review engine."""

import os
from datetime import date

import pandas as pd
import pytest

from ecom_analytics.loader import load_orders
from ecom_analytics.review_engine import (
    build_review_data,
    compute_period_comparison,
    compute_period_summary,
    _generate_hypotheses,
)
from ecom_analytics.periods import PeriodRange

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
ORDERS_CSV = os.path.join(FIXTURES_DIR, "sample_orders.csv")


@pytest.fixture
def orders():
    return load_orders(ORDERS_CSV)


class TestComputePeriodSummary:
    def test_returns_expected_keys(self, orders):
        period = PeriodRange("June 2025", date(2025, 6, 1), date(2025, 6, 30))
        result = compute_period_summary(orders, period)
        expected_keys = {
            "revenue", "orders", "aov", "customers",
            "new_customers", "returning_customers",
            "new_customer_revenue", "returning_customer_revenue",
            "avg_discount_rate",
        }
        assert expected_keys == set(result.keys())

    def test_filters_to_period(self, orders):
        period = PeriodRange("June 2025", date(2025, 6, 1), date(2025, 6, 30))
        result = compute_period_summary(orders, period)
        # Should have some data (sample_orders spans 2025)
        assert result["revenue"] >= 0
        assert result["orders"] >= 0

    def test_new_vs_returning_split(self, orders):
        period = PeriodRange("June 2025", date(2025, 6, 1), date(2025, 6, 30))
        result = compute_period_summary(orders, period)
        assert result["new_customers"] + result["returning_customers"] == result["customers"]
        assert abs(
            result["new_customer_revenue"] + result["returning_customer_revenue"]
            - result["revenue"]
        ) < 0.01

    def test_empty_period_returns_zeros(self, orders):
        period = PeriodRange("Jan 2020", date(2020, 1, 1), date(2020, 1, 31))
        result = compute_period_summary(orders, period)
        assert result["revenue"] == 0.0
        assert result["orders"] == 0
        assert result["customers"] == 0


class TestComputePeriodComparison:
    def test_positive_change(self):
        current = {"revenue": 120.0, "orders": 12}
        previous = {"revenue": 100.0, "orders": 10}
        delta = compute_period_comparison(current, previous)
        assert abs(delta["revenue"] - 0.20) < 0.001
        assert abs(delta["orders"] - 0.20) < 0.001

    def test_negative_change(self):
        current = {"revenue": 80.0}
        previous = {"revenue": 100.0}
        delta = compute_period_comparison(current, previous)
        assert abs(delta["revenue"] - (-0.20)) < 0.001

    def test_zero_previous(self):
        current = {"revenue": 100.0}
        previous = {"revenue": 0.0}
        delta = compute_period_comparison(current, previous)
        assert delta["revenue"] == float("inf")


class TestBuildReviewData:
    def test_mbr_has_required_sections(self, orders):
        # Use a ref_date within the sample data range
        data = build_review_data(orders, "mbr", ref_date=date(2025, 7, 15))
        assert data["cadence"] == "mbr"
        assert "period" in data
        assert "target_summary" in data
        assert "comparisons" in data
        assert "waterfall" in data
        assert "new_vs_returning" in data
        assert "customer_analysis" in data
        assert "product_analysis" in data
        assert "trailing" in data
        assert "findings" in data

    def test_qbr_has_required_sections(self, orders):
        data = build_review_data(orders, "qbr", ref_date=date(2025, 7, 15))
        assert data["cadence"] == "qbr"
        assert "period" in data
        assert "target_summary" in data
        assert "comparisons" in data

    def test_abr_has_required_sections(self, orders):
        # ABR needs data from prior year — may have empty summary
        data = build_review_data(orders, "abr", ref_date=date(2026, 1, 15))
        assert data["cadence"] == "abr"
        assert "period" in data

    def test_comparison_axes_mbr(self, orders):
        data = build_review_data(orders, "mbr", ref_date=date(2025, 7, 15))
        labels = [c["label"] for c in data["comparisons"]]
        assert "vs Prior Month" in labels
        assert "vs Same Month Last Year" in labels

    def test_comparison_axes_qbr(self, orders):
        data = build_review_data(orders, "qbr", ref_date=date(2025, 7, 15))
        labels = [c["label"] for c in data["comparisons"]]
        assert "vs Prior Quarter" in labels
        assert "vs Same Quarter Last Year" in labels

    def test_comparison_axes_abr(self, orders):
        data = build_review_data(orders, "abr", ref_date=date(2026, 1, 15))
        labels = [c["label"] for c in data["comparisons"]]
        assert "vs Prior Year" in labels
        # ABR has no YoY comparison
        assert len(labels) == 1

    def test_hypotheses_count_max_3(self, orders):
        data = build_review_data(orders, "mbr", ref_date=date(2025, 7, 15))
        assert len(data["findings"]) <= 3

    def test_customer_analysis_has_rfm(self, orders):
        data = build_review_data(orders, "mbr", ref_date=date(2025, 7, 15))
        ca = data["customer_analysis"]
        assert "rfm_segments" in ca
        assert "f2_rate" in ca
        assert "total_customers" in ca

    def test_product_analysis_has_abc(self, orders):
        data = build_review_data(orders, "mbr", ref_date=date(2025, 7, 15))
        pa = data["product_analysis"]
        assert "abc_summary" in pa
        assert "top_products" in pa
        assert "lifecycle_distribution" in pa


class TestGenerateHypotheses:
    def _make_review_data(self, target_summary, pop_delta, pop_summary, cadence="mbr"):
        """Helper to build minimal review_data for hypothesis testing."""
        return {
            "cadence": cadence,
            "target_summary": target_summary,
            "comparisons": [
                {
                    "label": "vs Prior",
                    "period": PeriodRange("Prior", date(2025, 5, 1), date(2025, 5, 31)),
                    "summary": pop_summary,
                    "delta": pop_delta,
                }
            ],
            "new_vs_returning": {
                "new_revenue": target_summary.get("new_customer_revenue", 50),
                "returning_revenue": target_summary.get("returning_customer_revenue", 50),
                "returning_share": 0.50,
            },
            "customer_analysis": {
                "rfm_segments": {"Champions": 10, "Loyal": 20, "At Risk": 15, "Lost": 5},
                "f2_rate": 0.25,
                "avg_purchase_interval_days": 45,
                "total_customers": 100,
            },
            "product_analysis": {
                "abc_summary": {"A": 5, "B": 15, "C": 30},
                "top_products": [],
                "lifecycle_distribution": {"Growth": 10, "Mature": 20, "Decline": 5},
                "category_performance": [],
            },
        }

    def test_revenue_down_orders_down(self):
        target = {"revenue": 90, "orders": 9, "aov": 10, "new_customers": 5,
                  "returning_customer_revenue": 45, "avg_discount_rate": 0.05,
                  "new_customer_revenue": 45, "returning_customers": 4, "customers": 9}
        pop_delta = {"revenue": -0.10, "orders": -0.10, "aov": 0.0,
                     "new_customers": -0.10, "returning_customer_revenue": -0.05,
                     "avg_discount_rate": 0.0}
        pop_summary = {"revenue": 100, "orders": 10, "aov": 10, "new_customers": 6,
                       "returning_customer_revenue": 50, "avg_discount_rate": 0.05,
                       "new_customer_revenue": 50, "returning_customers": 4, "customers": 10}
        data = self._make_review_data(target, pop_delta, pop_summary)
        findings = _generate_hypotheses(data, "mbr")
        titles = [f["title"] for f in findings]
        assert "Traffic or Acquisition Drop" in titles

    def test_revenue_down_aov_down(self):
        target = {"revenue": 85, "orders": 10, "aov": 8.5, "new_customers": 5,
                  "returning_customer_revenue": 40, "avg_discount_rate": 0.05,
                  "new_customer_revenue": 45, "returning_customers": 5, "customers": 10}
        pop_delta = {"revenue": -0.15, "orders": 0.0, "aov": -0.15,
                     "new_customers": 0.0, "returning_customer_revenue": -0.05,
                     "avg_discount_rate": 0.0}
        pop_summary = {"revenue": 100, "orders": 10, "aov": 10, "new_customers": 5,
                       "returning_customer_revenue": 50, "avg_discount_rate": 0.05,
                       "new_customer_revenue": 50, "returning_customers": 5, "customers": 10}
        data = self._make_review_data(target, pop_delta, pop_summary)
        findings = _generate_hypotheses(data, "mbr")
        titles = [f["title"] for f in findings]
        assert "Mix Shift or Heavier Discounting" in titles

    def test_returning_revenue_down(self):
        target = {"revenue": 90, "orders": 10, "aov": 9, "new_customers": 5,
                  "returning_customer_revenue": 30, "avg_discount_rate": 0.05,
                  "new_customer_revenue": 60, "returning_customers": 5, "customers": 10}
        pop_delta = {"revenue": -0.05, "orders": 0.0, "aov": -0.05,
                     "new_customers": 0.0, "returning_customer_revenue": -0.40,
                     "avg_discount_rate": 0.0}
        pop_summary = {"revenue": 100, "orders": 10, "aov": 10, "new_customers": 5,
                       "returning_customer_revenue": 50, "avg_discount_rate": 0.05,
                       "new_customer_revenue": 50, "returning_customers": 5, "customers": 10}
        data = self._make_review_data(target, pop_delta, pop_summary)
        findings = _generate_hypotheses(data, "mbr")
        titles = [f["title"] for f in findings]
        assert "Returning Customer Revenue Drop" in titles

    def test_qbr_low_f2(self):
        target = {"revenue": 1000, "orders": 100, "aov": 10, "new_customers": 50,
                  "returning_customer_revenue": 200, "avg_discount_rate": 0.05,
                  "new_customer_revenue": 800, "returning_customers": 50, "customers": 100}
        pop_delta = {"revenue": 0.0, "orders": 0.0, "aov": 0.0,
                     "new_customers": 0.0, "returning_customer_revenue": 0.0,
                     "avg_discount_rate": 0.0}
        pop_summary = target.copy()
        data = self._make_review_data(target, pop_delta, pop_summary, cadence="qbr")
        data["customer_analysis"]["f2_rate"] = 0.15
        findings = _generate_hypotheses(data, "qbr")
        titles = [f["title"] for f in findings]
        assert "Low F2 Conversion Rate" in titles
