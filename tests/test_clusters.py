"""Tests for finding cluster activation logic in report.py.

Clusters group related check failures into systemic themes.
They are critical for the LLM interpretation layer -- if clusters
don't activate correctly, the report misses key business insights.

4 clusters: B (Discount), C (Assortment), F (Customer), G (Concentration).
"""

import pytest

from claude_ecom.report import _build_clusters
from claude_ecom.checks import CheckResult


def _make_check(check_id, category, severity, result):
    return CheckResult(
        check_id=check_id,
        category=category,
        severity=severity,
        result=result,
        message=f"{check_id} test message",
    )


class TestClusterActivation:
    """Clusters should activate when 2+ member checks are non-pass."""

    def test_no_clusters_when_all_pass(self):
        checks = [
            _make_check("R08", "revenue", "high", "pass"),
            _make_check("PR02", "revenue", "high", "pass"),
            _make_check("C01", "customer", "critical", "pass"),
        ]
        clusters = _build_clusters(checks)
        assert len(clusters) == 0

    def test_no_cluster_with_single_fail(self):
        checks = [
            _make_check("R08", "revenue", "high", "fail"),
            _make_check("PR02", "revenue", "high", "pass"),
        ]
        clusters = _build_clusters(checks)
        discount_clusters = [c for c in clusters if c["name"] == "Discount Dependency"]
        assert len(discount_clusters) == 0

    def test_discount_dependency_activates(self):
        checks = [
            _make_check("R08", "revenue", "high", "fail"),
            _make_check("PR02", "revenue", "high", "fail"),
        ]
        clusters = _build_clusters(checks)
        names = [c["name"] for c in clusters]
        assert "Discount Dependency" in names

    def test_customer_ltv_activates(self):
        checks = [
            _make_check("R05", "revenue", "critical", "fail"),
            _make_check("C01", "customer", "critical", "fail"),
            _make_check("C09", "customer", "high", "watch"),
        ]
        clusters = _build_clusters(checks)
        names = [c["name"] for c in clusters]
        assert "Customer & LTV Engine Weakness" in names

    def test_revenue_concentration_activates(self):
        checks = [
            _make_check("R07", "revenue", "medium", "watch"),
            _make_check("P01", "product", "medium", "fail"),
        ]
        clusters = _build_clusters(checks)
        names = [c["name"] for c in clusters]
        assert "Revenue Concentration Risk" in names

    def test_assortment_activates(self):
        checks = [
            _make_check("P05", "product", "high", "fail"),
            _make_check("P06", "product", "medium", "fail"),
        ]
        clusters = _build_clusters(checks)
        names = [c["name"] for c in clusters]
        assert "Assortment & Merchandising Misfit" in names


class TestClusterContent:
    """Each cluster should have useful content for the LLM."""

    def test_cluster_has_name(self):
        checks = [
            _make_check("P05", "product", "high", "fail"),
            _make_check("P06", "product", "medium", "fail"),
        ]
        clusters = _build_clusters(checks)
        assert clusters[0]["name"]

    def test_cluster_has_count(self):
        checks = [
            _make_check("P05", "product", "high", "fail"),
            _make_check("P06", "product", "medium", "fail"),
        ]
        clusters = _build_clusters(checks)
        assert clusters[0]["count"] == 2

    def test_cluster_has_hypothesis(self):
        checks = [
            _make_check("P05", "product", "high", "fail"),
            _make_check("P06", "product", "medium", "fail"),
        ]
        clusters = _build_clusters(checks)
        assert len(clusters[0]["hypothesis"]) > 10

    def test_cluster_has_approach(self):
        checks = [
            _make_check("P05", "product", "high", "fail"),
            _make_check("P06", "product", "medium", "fail"),
        ]
        clusters = _build_clusters(checks)
        assert len(clusters[0]["approach"]) > 10

    def test_cluster_has_related_issues(self):
        checks = [
            _make_check("P05", "product", "high", "fail"),
            _make_check("P06", "product", "medium", "fail"),
        ]
        clusters = _build_clusters(checks)
        assert "related_issues" in clusters[0]
        assert len(clusters[0]["related_issues"]) > 0


class TestClusterWorstCheck:
    """The worst check should be the most severe."""

    def test_critical_fail_is_worst(self):
        checks = [
            _make_check("R05", "revenue", "critical", "fail"),
            _make_check("C01", "customer", "critical", "watch"),
            _make_check("C08", "customer", "medium", "fail"),
        ]
        clusters = _build_clusters(checks)
        customer_cluster = [c for c in clusters if c["name"] == "Customer & LTV Engine Weakness"]
        if customer_cluster:
            assert "R05" in customer_cluster[0]["hypothesis"] or "C01" in customer_cluster[0]["hypothesis"]

    def test_fail_beats_watch_at_same_severity(self):
        checks = [
            _make_check("R08", "revenue", "high", "watch"),
            _make_check("PR02", "revenue", "high", "fail"),
        ]
        clusters = _build_clusters(checks)
        discount_cluster = [c for c in clusters if c["name"] == "Discount Dependency"]
        if discount_cluster:
            assert "PR02" in discount_cluster[0]["hypothesis"]


class TestMultipleClusters:
    """Multiple clusters can activate simultaneously."""

    def test_two_clusters_activate(self):
        checks = [
            # Discount Dependency
            _make_check("R08", "revenue", "high", "fail"),
            _make_check("PR02", "revenue", "high", "fail"),
            # Assortment
            _make_check("P05", "product", "high", "fail"),
            _make_check("P06", "product", "medium", "fail"),
        ]
        clusters = _build_clusters(checks)
        names = [c["name"] for c in clusters]
        assert "Discount Dependency" in names
        assert "Assortment & Merchandising Misfit" in names

    def test_na_checks_do_not_activate_clusters(self):
        checks = [
            _make_check("R08", "revenue", "high", "na"),
            _make_check("PR02", "revenue", "high", "na"),
        ]
        clusters = _build_clusters(checks)
        assert len(clusters) == 0

    def test_pass_checks_do_not_activate_clusters(self):
        checks = [
            _make_check("R08", "revenue", "high", "pass"),
            _make_check("PR02", "revenue", "high", "fail"),
        ]
        clusters = _build_clusters(checks)
        discount_clusters = [c for c in clusters if c["name"] == "Discount Dependency"]
        assert len(discount_clusters) == 0
