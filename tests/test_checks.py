"""Tests for claude_ecom.checks."""

from claude_ecom.checks import (
    CheckResult,
    build_action_candidates,
    build_top_issues,
    estimate_revenue_impact,
)


class TestEstimateImpact:
    def test_pass_excluded(self):
        checks = [CheckResult("R01", "revenue", "high", "pass")]
        impacts = estimate_revenue_impact(checks, 1_000_000)
        assert len(impacts) == 0

    def test_fail_has_impact(self):
        checks = [CheckResult("R01", "revenue", "critical", "fail")]
        impacts = estimate_revenue_impact(checks, 1_000_000)
        assert "R01" in impacts
        assert impacts["R01"]["annual_revenue_impact"] > 0
        assert impacts["R01"]["confidence"] == "high"


class TestBuildTopIssues:
    def test_excludes_pass(self):
        checks = [
            CheckResult("R01", "revenue", "high", "pass"),
            CheckResult("R05", "revenue", "critical", "fail", "test", 0.1, 0.3),
        ]
        issues = build_top_issues(checks, 1_000_000)
        assert len(issues) == 1
        assert issues[0]["id"] == "R05"

    def test_sorted_by_severity(self):
        checks = [
            CheckResult("R13", "revenue", "medium", "watch", "low sev"),
            CheckResult("R05", "revenue", "critical", "fail", "high sev"),
        ]
        issues = build_top_issues(checks, 1_000_000)
        assert issues[0]["id"] == "R05"

    def test_max_issues(self):
        checks = [CheckResult(f"R{i:02d}", "revenue", "medium", "fail") for i in range(20)]
        issues = build_top_issues(checks, 1_000_000, max_issues=5)
        assert len(issues) <= 5

    def test_has_estimated_impact(self):
        checks = [CheckResult("R05", "revenue", "critical", "fail", "test", 0.1, 0.3)]
        issues = build_top_issues(checks, 1_000_000)
        assert "estimated_annual_impact" in issues[0]


class TestBuildActionCandidates:
    def test_generates_actions(self):
        issues = [
            {
                "id": "P06",
                "category": "product",
                "severity": "high",
                "result": "fail",
                "message": "test",
                "estimated_annual_impact": 50000,
            },
        ]
        actions = build_action_candidates(issues)
        assert len(actions) >= 1
        assert actions[0]["source_check"] == "P06"
        assert actions[0]["timeline"] == "this_month"

    def test_max_actions(self):
        issues = [
            {
                "id": f"R{i:02d}",
                "category": "revenue",
                "severity": "medium",
                "result": "fail",
                "message": "test",
                "estimated_annual_impact": 1000,
            }
            for i in range(20)
        ]
        actions = build_action_candidates(issues, max_actions=5)
        assert len(actions) <= 5

    def test_severity_timeline_mapping(self):
        issues = [
            {
                "id": "R05",
                "category": "revenue",
                "severity": "critical",
                "result": "fail",
                "message": "test",
                "estimated_annual_impact": 100000,
            },
        ]
        actions = build_action_candidates(issues)
        assert actions[0]["timeline"] == "this_week"
