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

    def test_health_has_checks(self, orders):
        data = build_review_data(orders)
        health = data["health"]
        assert "checks" in health
        assert "top_issues" in health
        assert isinstance(health["checks"], list)
        assert len(health["checks"]) > 0

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
    def test_returns_only_data_months(self, orders):
        ref = orders["order_date"].max().date()
        trend = _compute_monthly_trend(orders, ref, days=365)
        # Should not have months with zero data
        for entry in trend:
            assert entry["orders"] > 0 or entry["revenue"] > 0

    def test_no_future_months_with_zero(self, orders):
        ref = orders["order_date"].max().date()
        trend = _compute_monthly_trend(orders, ref, days=365)
        for entry in trend:
            assert entry["revenue"] > 0 or entry["orders"] > 0, (
                f"Month {entry['month']} has zero data but was included"
            )

    def test_trailing_window_bounds(self, orders):
        ref = orders["order_date"].max().date()
        trend = _compute_monthly_trend(orders, ref, days=365)
        from datetime import timedelta
        window_start = ref - timedelta(days=364)
        for entry in trend:
            year, month = map(int, entry["month"].split("-"))
            # Month must overlap with [window_start, ref]
            assert date(year, month, 1) <= ref
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            assert date(year, month, last_day) >= window_start

    def test_each_entry_has_keys(self, orders):
        ref = orders["order_date"].max().date()
        trend = _compute_monthly_trend(orders, ref, days=365)
        for entry in trend:
            assert "month" in entry
            assert "revenue" in entry
            assert "orders" in entry
            assert "aov" in entry
            assert "customers" in entry
            assert "new_customers" in entry
            assert "returning_customers" in entry
            assert "days_with_data" in entry

    def test_partial_flag_on_short_month(self):
        """A month with only 3 days of data should have partial=True."""
        dates = pd.date_range("2025-12-01", "2025-12-31", freq="D")
        rows = []
        for i, d in enumerate(dates):
            rows.append({
                "order_id": f"O-{i}", "order_date": d,
                "customer_id": f"C-{i}", "amount": 100.0,
            })
        # Add 3 days in Jan 2026
        for i in range(3):
            d = pd.Timestamp("2026-01-01") + pd.Timedelta(days=i)
            rows.append({
                "order_id": f"O-jan-{i}", "order_date": d,
                "customer_id": f"C-jan-{i}", "amount": 100.0,
            })
        df = pd.DataFrame(rows)
        df["order_date"] = pd.to_datetime(df["order_date"])

        trend = _compute_monthly_trend(df, date(2026, 1, 3), days=365)
        jan_entry = [e for e in trend if e["month"] == "2026-01"]
        assert len(jan_entry) == 1
        assert jan_entry[0].get("partial") is True
        assert jan_entry[0]["days_with_data"] == 3


class TestPartialMonth:
    """Tests that partial last month does not cause false-positive MoM checks."""

    def _make_orders_with_partial_month(self):
        """Create orders: full Dec + 3 days of Jan."""
        rows = []
        # Full December
        for i in range(31):
            d = pd.Timestamp("2025-12-01") + pd.Timedelta(days=i)
            rows.append({
                "order_id": f"O-dec-{i}", "order_date": d,
                "customer_id": f"C-{i}", "amount": 1000.0,
                "sku": "SKU-1", "product_name": "P1",
            })
        # Full November
        for i in range(30):
            d = pd.Timestamp("2025-11-01") + pd.Timedelta(days=i)
            rows.append({
                "order_id": f"O-nov-{i}", "order_date": d,
                "customer_id": f"C-{i}", "amount": 1000.0,
                "sku": "SKU-1", "product_name": "P1",
            })
        # 3 days of January (partial)
        for i in range(3):
            d = pd.Timestamp("2026-01-01") + pd.Timedelta(days=i)
            rows.append({
                "order_id": f"O-jan-{i}", "order_date": d,
                "customer_id": f"C-jan-{i}", "amount": 100.0,
                "sku": "SKU-1", "product_name": "P1",
            })
        df = pd.DataFrame(rows)
        df["order_date"] = pd.to_datetime(df["order_date"])
        return df

    def test_mom_not_false_negative(self):
        """MoM should not report -87.8% from 3 days vs full month."""
        from claude_ecom.metrics import compute_revenue_kpis
        orders = self._make_orders_with_partial_month()
        kpis = compute_revenue_kpis(orders)
        assert kpis["partial_last_month"] is True
        # MoM should compare Nov vs Dec (both full), not Jan(partial) vs Dec
        mom = kpis["mom_growth_latest"]
        # Nov and Dec have similar revenue, so MoM should be close to 0
        assert abs(mom) < 0.2, f"MoM {mom:.1%} looks like a partial-month false positive"

    def test_r01_check_has_partial_note(self):
        """R01 check message should note partial month exclusion."""
        from claude_ecom.metrics import compute_revenue_kpis, compute_cohort_kpis
        orders = self._make_orders_with_partial_month()
        rev_kpis = compute_revenue_kpis(orders)
        cohort_kpis = compute_cohort_kpis(orders)
        from claude_ecom.review_engine import _build_checks
        checks = _build_checks(rev_kpis, cohort_kpis, orders)
        r01 = [c for c in checks if c.check_id == "R01"][0]
        assert "partial month excluded" in r01.message


class TestDataQuality:
    def test_data_quality_in_review_json(self, orders):
        data = build_review_data(orders)
        assert "data_quality" in data
        assert isinstance(data["data_quality"], list)

    def test_short_data_warns(self):
        """Fewer than 90 days of data should produce a short_data_span warning."""
        rows = []
        for i in range(30):
            d = pd.Timestamp("2025-12-01") + pd.Timedelta(days=i)
            rows.append({
                "order_id": f"O-{i}", "order_date": d,
                "customer_id": f"C-{i}", "amount": 100.0,
                "sku": "SKU-1", "product_name": "P1",
            })
        df = pd.DataFrame(rows)
        df["order_date"] = pd.to_datetime(df["order_date"])
        data = build_review_data(df)
        types = [w["type"] for w in data["data_quality"]]
        assert "short_data_span" in types

    def test_partial_month_warning(self):
        """Partial last month should produce a partial_period warning."""
        rows = []
        # Full November + December
        for i in range(61):
            d = pd.Timestamp("2025-11-01") + pd.Timedelta(days=i)
            rows.append({
                "order_id": f"O-{i}", "order_date": d,
                "customer_id": f"C-{i % 20}", "amount": 100.0,
                "sku": "SKU-1", "product_name": "P1",
            })
        # 3 days of January (partial)
        for i in range(3):
            d = pd.Timestamp("2026-01-01") + pd.Timedelta(days=i)
            rows.append({
                "order_id": f"O-jan-{i}", "order_date": d,
                "customer_id": f"C-jan-{i}", "amount": 100.0,
                "sku": "SKU-1", "product_name": "P1",
            })
        df = pd.DataFrame(rows)
        df["order_date"] = pd.to_datetime(df["order_date"])
        data = build_review_data(df)
        types = [w["type"] for w in data["data_quality"]]
        assert "partial_period" in types


class TestMonthlyTrendIn365dBlock:
    def test_365d_has_monthly_trend(self, orders):
        data = build_review_data(orders)
        if data["data_coverage"]["365d"] and "365d" in data["periods"]:
            assert "monthly_trend" in data["periods"]["365d"]
            trend = data["periods"]["365d"]["monthly_trend"]
            # All entries should have data
            for entry in trend:
                assert entry["orders"] > 0 or entry["revenue"] > 0
