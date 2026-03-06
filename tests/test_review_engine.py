"""Tests for the unified business review engine."""

import os
from datetime import date

import pandas as pd
import pytest

from claude_ecom.loader import load_orders
from claude_ecom.review_engine import (
    build_review_data,
    compute_period_comparison,
    compute_period_summary,
    _compute_drivers,
    _compute_monthly_trend,
)
from claude_ecom.periods import PeriodRange

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
            "new_customer_aov", "returning_customer_aov",
            "avg_discount_rate",
        }
        assert expected_keys == set(result.keys())

    def test_filters_to_period(self, orders):
        period = PeriodRange("June 2025", date(2025, 6, 1), date(2025, 6, 30))
        result = compute_period_summary(orders, period)
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

    def test_has_segment_aov(self, orders):
        period = PeriodRange("June 2025", date(2025, 6, 1), date(2025, 6, 30))
        result = compute_period_summary(orders, period)
        assert "new_customer_aov" in result
        assert "returning_customer_aov" in result


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
    def test_has_required_top_level_keys(self, orders):
        data = build_review_data(orders)
        assert "version" in data
        assert "metadata" in data
        assert "data_coverage" in data
        assert "periods" in data
        assert "health" in data
        assert "action_candidates" in data

    def test_metadata_fields(self, orders):
        data = build_review_data(orders)
        md = data["metadata"]
        assert "generated_at" in md
        assert "data_start" in md
        assert "data_end" in md
        assert "total_orders" in md
        assert "total_customers" in md
        assert "total_revenue" in md

    def test_data_coverage_has_three_periods(self, orders):
        data = build_review_data(orders)
        cov = data["data_coverage"]
        assert "30d" in cov
        assert "90d" in cov
        assert "365d" in cov

    def test_period_blocks_have_expected_structure(self, orders):
        data = build_review_data(orders)
        for period_key, block in data["periods"].items():
            assert "summary" in block
            assert "kpi_tree" in block
            assert "drivers" in block
            summary = block["summary"]
            assert "revenue" in summary
            assert "revenue_change" in summary
            assert "orders" in summary
            assert "aov" in summary

    def test_health_has_category_scores(self, orders):
        data = build_review_data(orders)
        health = data["health"]
        assert "category_scores" in health
        assert "checks" in health
        assert "top_issues" in health
        for cat, info in health["category_scores"].items():
            assert "score" in info
            assert "level" in info

    def test_specific_period_filter(self, orders):
        data = build_review_data(orders, period="30d")
        cov = data["data_coverage"]
        if cov["30d"]:
            assert "30d" in data["periods"]
            # Should not have other periods when specific period requested
            assert len(data["periods"]) <= 1

    def test_action_candidates_structure(self, orders):
        data = build_review_data(orders)
        for action in data["action_candidates"]:
            assert "action" in action
            assert "source_check" in action
            assert "severity" in action
            assert "timeline" in action

    def test_top_issues_max_10(self, orders):
        data = build_review_data(orders)
        assert len(data["health"]["top_issues"]) <= 10


class TestComputeDrivers:
    def test_basic_decomposition(self):
        current = {"revenue": 1200, "orders": 12, "aov": 100}
        prior = {"revenue": 1000, "orders": 10, "aov": 100}
        drivers = _compute_drivers(current, prior)
        assert drivers["volume_effect"] == 200.0  # 2 extra orders * 100 AOV
        assert drivers["aov_effect"] == 0.0

    def test_zero_prior_revenue(self):
        current = {"revenue": 1000, "orders": 10, "aov": 100}
        prior = {"revenue": 0, "orders": 0, "aov": 0}
        drivers = _compute_drivers(current, prior)
        assert drivers["volume_effect"] == 0
        assert drivers["aov_effect"] == 0
        assert drivers["mix_effect"] == 0


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
            assert "new_customers" in entry
            assert "returning_customers" in entry


class TestMonthlyTrendIn365dBlock:
    def test_365d_has_monthly_trend(self, orders):
        data = build_review_data(orders)
        if data["data_coverage"]["365d"] and "365d" in data["periods"]:
            assert "monthly_trend" in data["periods"]["365d"]
            assert len(data["periods"]["365d"]["monthly_trend"]) == 12
