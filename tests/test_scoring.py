"""Tests for claude_ecom.scoring."""

import pytest

from claude_ecom.scoring import (
    CheckResult,
    CATEGORY_WEIGHTS,
    SEVERITY_MULTIPLIERS,
    assign_grade,
    score_category,
    score_checks,
    aggregate_score,
    estimate_revenue_impact,
)


class TestWeights:
    def test_category_weights_sum_to_110(self):
        """Weights sum to 1.10 (7 categories); aggregate_score renormalizes."""
        total = sum(CATEGORY_WEIGHTS.values())
        assert abs(total - 1.10) < 1e-9, f"Weights sum to {total}, expected 1.10"

    def test_seven_categories_defined(self):
        expected = {"revenue", "conversion", "product", "inventory", "retention", "pricing", "site"}
        assert set(CATEGORY_WEIGHTS.keys()) == expected

    def test_severity_multipliers_defined(self):
        assert SEVERITY_MULTIPLIERS["critical"] == 5.0
        assert SEVERITY_MULTIPLIERS["high"] == 3.0
        assert SEVERITY_MULTIPLIERS["medium"] == 1.5
        assert SEVERITY_MULTIPLIERS["low"] == 0.5


class TestAssignGrade:
    @pytest.mark.parametrize(
        "score, expected",
        [(95, "A"), (90, "A"), (80, "B"), (75, "B"), (65, "C"), (60, "C"), (50, "D"), (40, "D"), (30, "F"), (0, "F")],
    )
    def test_grade_thresholds(self, score, expected):
        assert assign_grade(score) == expected


class TestScoreCategory:
    def test_all_pass_scores_100(self):
        checks = [
            CheckResult("R01", "revenue", "high", "pass"),
            CheckResult("R02", "revenue", "medium", "pass"),
        ]
        cs = score_category(checks)
        assert cs.score == 100.0
        assert cs.grade == "A"

    def test_all_fail_scores_0(self):
        checks = [
            CheckResult("R01", "revenue", "high", "fail"),
            CheckResult("R02", "revenue", "critical", "fail"),
        ]
        cs = score_category(checks)
        assert cs.score == 0.0
        assert cs.grade == "F"

    def test_mixed_results(self):
        checks = [
            CheckResult("R01", "revenue", "critical", "pass"),
            CheckResult("R02", "revenue", "high", "warning"),
            CheckResult("R03", "revenue", "medium", "fail"),
        ]
        cs = score_category(checks)
        # (1.0*5.0 + 0.5*3.0 + 0.0*1.5) / (5.0+3.0+1.5) * 100 = 6.5/9.5*100 ≈ 68.4
        assert 68 <= cs.score <= 69
        assert cs.grade == "C"

    def test_counts(self):
        checks = [
            CheckResult("R01", "revenue", "high", "pass"),
            CheckResult("R02", "revenue", "medium", "warning"),
            CheckResult("R03", "revenue", "low", "fail"),
        ]
        cs = score_category(checks)
        assert cs.passed == 1
        assert cs.warnings == 1
        assert cs.failed == 1


class TestScoreChecks:
    def test_overall_score(self):
        checks = [
            CheckResult("R01", "revenue", "high", "pass"),
            CheckResult("C01", "retention", "critical", "pass"),
        ]
        health = score_checks(checks)
        assert health.overall_score == 100.0
        assert health.overall_grade == "A"

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
        scores = {"revenue": 80, "conversion": 60}
        weights = {"revenue": 0.25, "conversion": 0.20}
        result = aggregate_score(scores, weights)
        expected = (80 * 0.25 + 60 * 0.20) / (0.25 + 0.20)
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
