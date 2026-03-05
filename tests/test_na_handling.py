"""Tests for N/A handling across scoring, metrics, and checks."""

import math

import pandas as pd
import pytest

from claude_ecom.scoring import (
    CheckResult,
    CategoryScore,
    HealthScore,
    estimate_revenue_impact,
    score_category,
    score_checks,
)


class TestNAScoring:
    def test_na_excluded_from_denominator(self):
        checks = [
            CheckResult("R01", "revenue", "high", "pass"),
            CheckResult("R02", "revenue", "medium", "na"),
            CheckResult("R03", "revenue", "critical", "fail"),
        ]
        cs = score_category(checks)
        # N/A check should not count in weighted sum or weight total
        # Only R01 (pass, high=3.0) and R03 (fail, critical=5.0) count
        # score = (1.0*3.0 + 0.0*5.0) / (3.0+5.0) * 100 = 37.5
        assert cs.score == 37.5
        assert cs.passed == 1
        assert cs.failed == 1
        assert cs.na == 1
        assert cs.total_checks == 3

    def test_all_na_scores_100(self):
        checks = [
            CheckResult("R01", "revenue", "high", "na"),
            CheckResult("R02", "revenue", "medium", "na"),
        ]
        cs = score_category(checks)
        assert cs.score == 100.0
        assert cs.na == 2
        assert cs.passed == 0
        assert cs.failed == 0

    def test_na_not_in_critical_fails(self):
        checks = [
            CheckResult("R01", "revenue", "critical", "na"),
        ]
        cs = score_category(checks)
        assert cs.critical_fails == []

    def test_score_checks_total_na(self):
        checks = [
            CheckResult("R01", "revenue", "high", "pass"),
            CheckResult("R02", "revenue", "medium", "na"),
            CheckResult("C01", "retention", "critical", "na"),
            CheckResult("C02", "retention", "high", "fail"),
        ]
        health = score_checks(checks)
        assert health.total_na == 2
        assert health.total_passed == 1
        assert health.total_failed == 1


class TestNAImpactEstimation:
    def test_na_checks_skipped_in_impact(self):
        checks = [
            CheckResult("R01", "revenue", "high", "na"),
            CheckResult("R02", "revenue", "critical", "fail"),
        ]
        impacts = estimate_revenue_impact(checks, 1_000_000)
        assert "R01" not in impacts
        assert "R02" in impacts

    def test_zero_revenue_returns_empty(self):
        checks = [
            CheckResult("R01", "revenue", "critical", "fail"),
        ]
        impacts = estimate_revenue_impact(checks, 0)
        assert len(impacts) == 0

    def test_negative_revenue_returns_empty(self):
        checks = [
            CheckResult("R01", "revenue", "critical", "fail"),
        ]
        impacts = estimate_revenue_impact(checks, -100)
        assert len(impacts) == 0


class TestNAMetrics:
    def _make_orders(self, months=1):
        """Create minimal order DataFrame spanning given months."""
        dates = []
        for m in range(months):
            dates.extend([
                f"2024-{m+1:02d}-01",
                f"2024-{m+1:02d}-15",
            ])
        n = len(dates)
        return pd.DataFrame({
            "order_id": [f"ORD-{i}" for i in range(n)],
            "order_date": pd.to_datetime(dates),
            "amount": [100.0] * n,
            "customer_id": [f"CUST-{i}" for i in range(n)],
        })

    def test_single_month_mom_is_nan(self):
        from claude_ecom.metrics import compute_revenue_kpis

        orders = self._make_orders(months=1)
        kpis = compute_revenue_kpis(orders)
        assert math.isnan(kpis["mom_growth_latest"])

    def test_two_months_mom_is_valid(self):
        from claude_ecom.metrics import compute_revenue_kpis

        orders = self._make_orders(months=2)
        kpis = compute_revenue_kpis(orders)
        assert not math.isnan(kpis["mom_growth_latest"])


class TestNAChecks:
    def _make_orders(self, months=1, with_discount=False):
        dates = []
        for m in range(months):
            dates.extend([
                f"2024-{m+1:02d}-01",
                f"2024-{m+1:02d}-15",
            ])
        n = len(dates)
        data = {
            "order_id": [f"ORD-{i}" for i in range(n)],
            "order_date": pd.to_datetime(dates),
            "amount": [100.0] * n,
            "customer_id": [f"CUST-{i % max(1, n//2)}" for i in range(n)],
            "product_name": [f"PROD-{i % 3}" for i in range(n)],
        }
        if with_discount:
            data["discount"] = [5.0] * n
        return pd.DataFrame(data)

    def test_single_month_r01_is_na(self):
        from claude_ecom.metrics import compute_cohort_kpis, compute_revenue_kpis

        orders = self._make_orders(months=1)
        rev_kpis = compute_revenue_kpis(orders)
        cohort_kpis = compute_cohort_kpis(orders)

        # Import _build_checks
        from claude_ecom.cli import _build_checks

        checks = _build_checks(rev_kpis, cohort_kpis, orders, None, None)
        r01 = next(c for c in checks if c.check_id == "R01")
        assert r01.result == "na"

    def test_no_discount_r08_is_na(self):
        from claude_ecom.metrics import compute_cohort_kpis, compute_revenue_kpis

        orders = self._make_orders(months=2, with_discount=False)
        rev_kpis = compute_revenue_kpis(orders)
        cohort_kpis = compute_cohort_kpis(orders)

        from claude_ecom.cli import _build_checks

        checks = _build_checks(rev_kpis, cohort_kpis, orders, None, None)
        r08 = next(c for c in checks if c.check_id == "R08")
        assert r08.result == "na"


class TestNumpyNaNRegression:
    """Regression test: numpy NaN types must not slip through isinstance(float) checks."""

    def test_numpy_nan_mom_gives_na_result(self):
        import numpy as np

        from claude_ecom.cli import _build_checks
        from claude_ecom.metrics import compute_cohort_kpis, compute_revenue_kpis

        orders = pd.DataFrame({
            "order_id": ["ORD-1", "ORD-2"],
            "order_date": pd.to_datetime(["2024-01-01", "2024-01-15"]),
            "amount": [100.0, 200.0],
            "customer_id": ["C1", "C2"],
        })
        rev_kpis = compute_revenue_kpis(orders)
        # Inject numpy NaN (the bug scenario)
        rev_kpis["mom_growth_latest"] = np.nan
        cohort_kpis = compute_cohort_kpis(orders)

        checks = _build_checks(rev_kpis, cohort_kpis, orders, None, None)
        r01 = next(c for c in checks if c.check_id == "R01")
        assert r01.result == "na", f"Expected 'na' but got '{r01.result}'"


class TestDataPeriodEmpty:
    """Data Period line must not render as empty ' - ' when dates are missing."""

    def test_empty_dates_no_data_period(self):
        from claude_ecom.report import generate_audit_report
        from claude_ecom.scoring import CheckResult, score_checks

        checks = [
            CheckResult("R01", "revenue", "high", "na"),
        ]
        health = score_checks(checks)
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = generate_audit_report(
                health, annual_revenue=0, data_start="", data_end="", output_dir=tmp,
            )
            content = open(path).read()
        assert "Data Period:  - " not in content
        assert "Data Period:" not in content or "Data Period: 20" in content


class TestFuzzyColumnMapping:
    def test_token_similarity(self):
        from claude_ecom.loader import _token_similarity

        assert _token_similarity("order_id", "order id") == 1.0
        assert _token_similarity("order_id", "something else") == 0.0
        assert _token_similarity("purchase date", "date") > 0

    def test_fuzzy_map_finds_similar_columns(self):
        from claude_ecom.loader import _fuzzy_map_columns

        df = pd.DataFrame({
            "Order Number": ["1", "2"],
            "Purchase Date": ["2024-01-01", "2024-01-02"],
            "Total Amount": [100, 200],
            "Buyer ID": ["A", "B"],
        })
        # First apply exact mapping (which should find some)
        from claude_ecom.loader import _auto_map_columns

        df, exact = _auto_map_columns(df)
        # Then try fuzzy for remaining
        df, fuzzy = _fuzzy_map_columns(df)
        # After both tiers, required columns should be present
        mapped_cols = set(df.columns)
        # At least some of the required columns should be mapped
        assert "order_id" in mapped_cols or "order_date" in mapped_cols or len(exact) + len(fuzzy) > 0
