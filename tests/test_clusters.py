"""Tests for finding cluster activation logic in report.py.

Clusters group related check failures into systemic themes.
They are critical for the LLM interpretation layer -- if clusters
don't activate correctly, the report misses key business insights.
"""

import pytest

from claude_ecom.report import _build_clusters
from claude_ecom.scoring import CheckResult


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
            _make_check("PR01", "pricing", "high", "pass"),
            _make_check("C01", "retention", "critical", "pass"),
        ]
        clusters = _build_clusters(checks)
        assert len(clusters) == 0

    def test_no_cluster_with_single_fail(self):
        checks = [
            _make_check("R08", "revenue", "high", "fail"),
            _make_check("PR02", "pricing", "high", "pass"),
        ]
        clusters = _build_clusters(checks)
        # Single fail in a cluster should NOT activate it (needs >= 2)
        discount_clusters = [c for c in clusters if c["name"] == "Discount Dependency"]
        assert len(discount_clusters) == 0

    def test_discount_dependency_activates(self):
        checks = [
            _make_check("R08", "revenue", "high", "fail"),
            _make_check("PR01", "pricing", "high", "fail"),
        ]
        clusters = _build_clusters(checks)
        names = [c["name"] for c in clusters]
        assert "Discount Dependency" in names

    def test_catalog_inventory_activates(self):
        checks = [
            _make_check("O03", "inventory", "critical", "fail"),
            _make_check("O06", "inventory", "high", "fail"),
        ]
        clusters = _build_clusters(checks)
        names = [c["name"] for c in clusters]
        assert "Catalog & Inventory Health" in names

    def test_retention_loyalty_activates(self):
        checks = [
            _make_check("R05", "revenue", "critical", "fail"),
            _make_check("C01", "retention", "critical", "fail"),
            _make_check("C09", "retention", "high", "warning"),
        ]
        clusters = _build_clusters(checks)
        names = [c["name"] for c in clusters]
        assert "Retention & Loyalty Erosion" in names

    def test_revenue_concentration_activates(self):
        checks = [
            _make_check("R07", "revenue", "medium", "warning"),
            _make_check("P01", "product", "medium", "fail"),
        ]
        clusters = _build_clusters(checks)
        names = [c["name"] for c in clusters]
        assert "Revenue Concentration Risk" in names


class TestClusterContent:
    """Each cluster should have useful content for the LLM."""

    def test_cluster_has_name(self):
        checks = [
            _make_check("O03", "inventory", "critical", "fail"),
            _make_check("O06", "inventory", "high", "fail"),
        ]
        clusters = _build_clusters(checks)
        assert clusters[0]["name"]

    def test_cluster_has_count(self):
        checks = [
            _make_check("O03", "inventory", "critical", "fail"),
            _make_check("O06", "inventory", "high", "fail"),
        ]
        clusters = _build_clusters(checks)
        assert clusters[0]["count"] == 2

    def test_cluster_has_hypothesis(self):
        checks = [
            _make_check("O03", "inventory", "critical", "fail"),
            _make_check("O06", "inventory", "high", "fail"),
        ]
        clusters = _build_clusters(checks)
        assert len(clusters[0]["hypothesis"]) > 10

    def test_cluster_hypothesis_mentions_worst_check(self):
        checks = [
            _make_check("O03", "inventory", "critical", "fail"),
            _make_check("O06", "inventory", "high", "fail"),
        ]
        clusters = _build_clusters(checks)
        # O03 is critical, so it should be worst
        assert "O03" in clusters[0]["hypothesis"]

    def test_cluster_has_approach(self):
        checks = [
            _make_check("O03", "inventory", "critical", "fail"),
            _make_check("O06", "inventory", "high", "fail"),
        ]
        clusters = _build_clusters(checks)
        assert len(clusters[0]["approach"]) > 10

    def test_cluster_has_check_ids(self):
        checks = [
            _make_check("O03", "inventory", "critical", "fail"),
            _make_check("O06", "inventory", "high", "fail"),
        ]
        clusters = _build_clusters(checks)
        assert "O03" in clusters[0]["check_ids"]
        assert "O06" in clusters[0]["check_ids"]


class TestClusterWorstCheck:
    """The worst check should be the most severe."""

    def test_critical_fail_is_worst(self):
        checks = [
            _make_check("R05", "revenue", "critical", "fail"),
            _make_check("C01", "retention", "critical", "warning"),
            _make_check("C08", "retention", "medium", "fail"),
        ]
        clusters = _build_clusters(checks)
        retention_cluster = [c for c in clusters if c["name"] == "Retention & Loyalty Erosion"]
        if retention_cluster:
            # R05 or C01 (critical) should be mentioned as worst, not C08 (medium)
            assert "R05" in retention_cluster[0]["hypothesis"] or "C01" in retention_cluster[0]["hypothesis"]

    def test_fail_beats_warning_at_same_severity(self):
        checks = [
            _make_check("R08", "revenue", "high", "warning"),
            _make_check("PR01", "pricing", "high", "fail"),
        ]
        clusters = _build_clusters(checks)
        discount_cluster = [c for c in clusters if c["name"] == "Discount Dependency"]
        if discount_cluster:
            # PR01 (fail) should be worst over R08 (warning)
            assert "PR01" in discount_cluster[0]["hypothesis"]


class TestMultipleClusters:
    """Multiple clusters can activate simultaneously."""

    def test_two_clusters_activate(self):
        checks = [
            # Discount Dependency
            _make_check("R08", "revenue", "high", "fail"),
            _make_check("PR01", "pricing", "high", "fail"),
            # Catalog & Inventory
            _make_check("O03", "inventory", "critical", "fail"),
            _make_check("O06", "inventory", "high", "fail"),
        ]
        clusters = _build_clusters(checks)
        names = [c["name"] for c in clusters]
        assert "Discount Dependency" in names
        assert "Catalog & Inventory Health" in names

    def test_na_checks_do_not_activate_clusters(self):
        checks = [
            _make_check("R08", "revenue", "high", "na"),
            _make_check("PR01", "pricing", "high", "na"),
        ]
        clusters = _build_clusters(checks)
        assert len(clusters) == 0

    def test_pass_checks_do_not_activate_clusters(self):
        checks = [
            _make_check("R08", "revenue", "high", "pass"),
            _make_check("PR01", "pricing", "high", "fail"),
        ]
        clusters = _build_clusters(checks)
        discount_clusters = [c for c in clusters if c["name"] == "Discount Dependency"]
        assert len(discount_clusters) == 0
