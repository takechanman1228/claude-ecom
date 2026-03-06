"""Tests for claude_ecom.scoring."""

import pytest

from claude_ecom.scoring import (
    CheckResult,
    CATEGORY_WEIGHTS,
    SEVERITY_MULTIPLIERS,
    HEALTH_LEVELS,
    assign_level,
    score_category,
    score_checks,
    aggregate_score,
    estimate_revenue_impact,
    build_top_issues,
    build_action_candidates,
)


class TestWeights:
    def test_category_weights_sum_to_100(self):
        """Weights sum to 1.00 (3 categories)."""
        total = sum(CATEGORY_WEIGHTS.values())
        assert abs(total - 1.00) < 1e-9, f"Weights sum to {total}, expected 1.00"

    def test_three_categories_defined(self):
        expected = {"revenue", "customer", "product"}
        assert set(CATEGORY_WEIGHTS.keys()) == expected

    def test_severity_multipliers_defined(self):
        assert SEVERITY_MULTIPLIERS["critical"] == 5.0
        assert SEVERITY_MULTIPLIERS["high"] == 3.0
        assert SEVERITY_MULTIPLIERS["medium"] == 1.5
        assert SEVERITY_MULTIPLIERS["low"] == 0.5


class TestAssignLevel:
    @pytest.mark.parametrize(
        "score, expected",
        [(80, "strong"), (75, "strong"), (60, "needs_attention"), (50, "needs_attention"), (40, "weak"), (0, "weak")],
    )
    def test_level_thresholds(self, score, expected):
        assert assign_level(score) == expected


class TestScoreCategory:
    def test_all_pass_scores_100(self):
        checks = [
            CheckResult("R01", "revenue", "high", "pass"),
            CheckResult("R02", "revenue", "medium", "pass"),
        ]
        cs = score_category(checks)
        assert cs.score == 100.0
        assert cs.level == "strong"

    def test_all_fail_scores_0(self):
        checks = [
            CheckResult("R01", "revenue", "high", "fail"),
            CheckResult("R02", "revenue", "critical", "fail"),
        ]
        cs = score_category(checks)
        assert cs.score == 0.0
        assert cs.level == "weak"

    def test_mixed_results(self):
        checks = [
            CheckResult("R01", "revenue", "critical", "pass"),
            CheckResult("R02", "revenue", "high", "watch"),
            CheckResult("R03", "revenue", "medium", "fail"),
        ]
        cs = score_category(checks)
        # (1.0*5.0 + 0.5*3.0 + 0.0*1.5) / (5.0+3.0+1.5) * 100 = 6.5/9.5*100 ≈ 68.4
        assert 68 <= cs.score <= 69
        assert cs.level == "needs_attention"

    def test_counts(self):
        checks = [
            CheckResult("R01", "revenue", "high", "pass"),
            CheckResult("R02", "revenue", "medium", "watch"),
            CheckResult("R03", "revenue", "low", "fail"),
        ]
        cs = score_category(checks)
        assert cs.passed == 1
        assert cs.warnings == 1
        assert cs.failed == 1

    def test_watch_scores_same_as_warning(self):
        """'watch' and 'warning' both score 0.5."""
        checks_watch = [CheckResult("R01", "revenue", "high", "watch")]
        checks_warn = [CheckResult("R01", "revenue", "high", "warning")]
        assert score_category(checks_watch).score == score_category(checks_warn).score


class TestScoreChecks:
    def test_overall_score(self):
        checks = [
            CheckResult("R01", "revenue", "high", "pass"),
            CheckResult("C01", "customer", "critical", "pass"),
        ]
        health = score_checks(checks)
        assert health.overall_score == 100.0

    def test_total_counts(self):
        checks = [
            CheckResult("R01", "revenue", "high", "pass"),
            CheckResult("R02", "revenue", "medium", "fail"),
        ]
        health = score_checks(checks)
        assert health.total_checks == 2
        assert health.total_passed == 1
        assert health.total_failed == 1


class TestAggregateScore:
    def test_weighted_average(self):
        scores = {"revenue": 80, "customer": 60}
        weights = {"revenue": 0.40, "customer": 0.30}
        result = aggregate_score(scores, weights)
        expected = (80 * 0.40 + 60 * 0.30) / (0.40 + 0.30)
        assert abs(result - expected) < 0.01


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
            {"id": "P06", "category": "product", "severity": "high",
             "result": "fail", "message": "test", "estimated_annual_impact": 50000},
        ]
        actions = build_action_candidates(issues)
        assert len(actions) >= 1
        assert actions[0]["source_check"] == "P06"
        assert actions[0]["timeline"] == "this_month"

    def test_max_actions(self):
        issues = [
            {"id": f"R{i:02d}", "category": "revenue", "severity": "medium",
             "result": "fail", "message": "test", "estimated_annual_impact": 1000}
            for i in range(20)
        ]
        actions = build_action_candidates(issues, max_actions=5)
        assert len(actions) <= 5

    def test_severity_timeline_mapping(self):
        issues = [
            {"id": "R05", "category": "revenue", "severity": "critical",
             "result": "fail", "message": "test", "estimated_annual_impact": 100000},
        ]
        actions = build_action_candidates(issues)
        assert actions[0]["timeline"] == "this_week"
