"""Tests for the business review engine."""

import os
from datetime import date

import pandas as pd
import pytest

from claude_ecom.loader import load_orders
from claude_ecom.review_engine import (
    build_review_data,
    compute_period_comparison,
    compute_period_summary,
    _assess_risks,
    _compute_growth_drivers,
    _compute_monthly_trend,
    _generate_hypotheses,
    _generate_recommendations,
)
from claude_ecom.periods import PeriodRange, auto_detect_cadence

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


class TestFindingsCapByCadence:
    """Findings cap varies by cadence: mbr=3, qbr=4, abr=5."""

    def test_mbr_cap_3(self, orders):
        data = build_review_data(orders, "mbr", ref_date=date(2025, 7, 15))
        assert len(data["findings"]) <= 3

    def test_qbr_cap_4(self, orders):
        data = build_review_data(orders, "qbr", ref_date=date(2025, 7, 15))
        assert len(data["findings"]) <= 4

    def test_abr_cap_5(self, orders):
        data = build_review_data(orders, "abr", ref_date=date(2026, 1, 15))
        assert len(data["findings"]) <= 5


class TestBuildReviewDataGeneralCadence:
    def test_general_cadence_resolves(self, orders):
        data = build_review_data(orders, "general", ref_date=date(2025, 7, 15))
        assert data["cadence"] == "general"
        assert data["effective_cadence"] in ("mbr", "qbr", "abr")

    def test_general_has_required_sections(self, orders):
        data = build_review_data(orders, "general", ref_date=date(2025, 7, 15))
        assert "period" in data
        assert "target_summary" in data
        assert "comparisons" in data
        assert "risks" in data
        assert "recommendations" in data
        assert "findings" in data

    def test_period_start_end_override(self, orders):
        data = build_review_data(
            orders, "general",
            period_start=date(2025, 4, 1), period_end=date(2025, 6, 30),
        )
        assert data["period"]["start"] == "2025-04-01"
        assert data["period"]["end"] == "2025-06-30"


class TestAssessRisks:
    def _make_review_data(self, **overrides):
        base = {
            "target_summary": {
                "revenue": 1000, "orders": 100, "aov": 10,
                "avg_discount_rate": 0.05,
            },
            "comparisons": [{
                "label": "vs Prior",
                "period": PeriodRange("Prior", date(2025, 5, 1), date(2025, 5, 31)),
                "summary": {"revenue": 1000},
                "delta": {"revenue": 0.0, "new_customers": 0.0, "avg_discount_rate": 0.0},
            }],
            "new_vs_returning": {"returning_share": 0.50},
            "product_analysis": {
                "top_products": [{"revenue_share": 0.30}],
                "lifecycle_distribution": {"Growth": 10, "Decline": 5},
            },
        }
        base.update(overrides)
        return base

    def test_returns_list(self):
        data = self._make_review_data()
        risks = _assess_risks(data, "mbr")
        assert isinstance(risks, list)

    def test_high_concentration_risk(self):
        data = self._make_review_data(
            product_analysis={
                "top_products": [{"revenue_share": 0.60}],
                "lifecycle_distribution": {},
            }
        )
        risks = _assess_risks(data, "mbr")
        titles = [r["title"] for r in risks]
        assert "Revenue Concentration" in titles

    def test_acquisition_dependency_risk(self):
        data = self._make_review_data(
            new_vs_returning={"returning_share": 0.20}
        )
        risks = _assess_risks(data, "mbr")
        titles = [r["title"] for r in risks]
        assert "Customer Acquisition Dependency" in titles

    def test_max_3_risks(self):
        data = self._make_review_data(
            new_vs_returning={"returning_share": 0.15},
            product_analysis={
                "top_products": [{"revenue_share": 0.70}],
                "lifecycle_distribution": {"Decline": 8, "Growth": 2},
            },
        )
        data["comparisons"][0]["delta"]["avg_discount_rate"] = 0.05
        data["comparisons"][0]["delta"]["revenue"] = -0.10
        data["comparisons"][0]["delta"]["new_customers"] = -0.10
        data["target_summary"]["avg_discount_rate"] = 0.30
        risks = _assess_risks(data, "mbr")
        assert len(risks) <= 3


class TestGenerateRecommendations:
    def test_returns_list(self):
        data = {"findings": [], "risks": []}
        recs = _generate_recommendations(data, "mbr")
        assert isinstance(recs, list)

    def test_generates_from_risks(self):
        data = {
            "findings": [],
            "risks": [{"title": "Revenue Concentration", "severity": "High", "description": "test"}],
        }
        recs = _generate_recommendations(data, "qbr")
        assert len(recs) >= 1
        assert recs[0]["title"] == "Diversify Revenue Sources"

    def test_max_5_recommendations(self):
        data = {
            "findings": [],
            "risks": [
                {"title": "Revenue Concentration", "severity": "High", "description": ""},
                {"title": "Customer Acquisition Dependency", "severity": "High", "description": ""},
                {"title": "Discount Dependency", "severity": "Medium", "description": ""},
                {"title": "Product Lifecycle Risk", "severity": "Medium", "description": ""},
                {"title": "Growth Sustainability", "severity": "High", "description": ""},
            ],
        }
        recs = _generate_recommendations(data, "abr")
        assert len(recs) <= 5


class TestMonthlyTrend:
    def test_returns_12_months(self, orders):
        trend = _compute_monthly_trend(orders, 2025)
        assert len(trend) == 12
        assert trend[0]["month"] == "2025-01"
        assert trend[11]["month"] == "2025-12"

    def test_each_entry_has_keys(self, orders):
        trend = _compute_monthly_trend(orders, 2025)
        for entry in trend:
            assert "month" in entry
            assert "revenue" in entry
            assert "orders" in entry
            assert "aov" in entry
            assert "customers" in entry


class TestGrowthDrivers:
    def test_basic_decomposition(self):
        target = {"revenue": 1200, "new_customer_revenue": 700, "returning_customer_revenue": 500}
        prev = {"revenue": 1000, "new_customer_revenue": 600, "returning_customer_revenue": 400}
        drivers = _compute_growth_drivers(target, prev)
        assert drivers["total_change"] == 200
        assert drivers["acquisition_effect"] == 100
        assert drivers["retention_effect"] == 100

    def test_zero_prev_revenue(self):
        target = {"revenue": 1000, "new_customer_revenue": 600, "returning_customer_revenue": 400}
        prev = {"revenue": 0, "new_customer_revenue": 0, "returning_customer_revenue": 0}
        drivers = _compute_growth_drivers(target, prev)
        assert drivers["total_change"] == 0.0


class TestAutoDetectCadence:
    def test_short_span_is_mbr(self):
        df = pd.DataFrame({
            "order_date": pd.to_datetime(["2025-06-01", "2025-06-30"]),
        })
        assert auto_detect_cadence(df) == "mbr"

    def test_medium_span_is_qbr(self):
        df = pd.DataFrame({
            "order_date": pd.to_datetime(["2025-01-01", "2025-06-01"]),
        })
        assert auto_detect_cadence(df) == "qbr"

    def test_long_span_is_abr(self):
        df = pd.DataFrame({
            "order_date": pd.to_datetime(["2024-01-01", "2025-06-01"]),
        })
        assert auto_detect_cadence(df) == "abr"
