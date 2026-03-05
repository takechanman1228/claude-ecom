"""Tests for scores.json schema stability.

scores.json is the contract between the Python compute engine and the LLM
interpretation layer. If the schema breaks, the LLM cannot interpret results.
"""

import json
import os

import pytest
from click.testing import CliRunner

from claude_ecom.cli import cli
from claude_ecom.report import generate_scores_json
from claude_ecom.scoring import CheckResult, score_checks

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
ORDERS_CSV = os.path.join(FIXTURES_DIR, "sample_orders.csv")


@pytest.fixture
def sample_health():
    checks = [
        CheckResult("R01", "revenue", "high", "fail", "MoM revenue growth: -10.0%", -0.10, 0.0),
        CheckResult("R05", "revenue", "critical", "pass", "Repeat revenue share: 35.0%", 0.35, 0.3),
        CheckResult("C01", "retention", "critical", "warning", "F2 rate: 20.0%", 0.20, 0.25),
        CheckResult("O03", "inventory", "critical", "fail", "Stockout rate: 47.5%", 0.475, 0.05),
        CheckResult("PR01", "pricing", "high", "pass", "Discount rate: 5.0%", 0.05, 0.15),
        CheckResult("R08", "revenue", "high", "na", "No discount data available", None, 0.15),
    ]
    return score_checks(checks)


class TestScoresJsonTopLevel:
    """Top-level fields that the LLM reads first."""

    def test_has_required_top_level_fields(self, sample_health, tmp_path):
        generate_scores_json(sample_health, output_dir=str(tmp_path), business_model="D2C")
        data = json.loads((tmp_path / "scores.json").read_text())

        required = {"version", "date", "business_model", "overall_score", "overall_grade", "categories", "checks"}
        assert required.issubset(set(data.keys()))

    def test_overall_score_is_number(self, sample_health, tmp_path):
        generate_scores_json(sample_health, output_dir=str(tmp_path))
        data = json.loads((tmp_path / "scores.json").read_text())
        assert isinstance(data["overall_score"], (int, float))
        assert 0 <= data["overall_score"] <= 100

    def test_overall_grade_is_valid(self, sample_health, tmp_path):
        generate_scores_json(sample_health, output_dir=str(tmp_path))
        data = json.loads((tmp_path / "scores.json").read_text())
        assert data["overall_grade"] in ("A", "B", "C", "D", "F")


class TestScoresJsonCategories:
    """Category section schema."""

    def test_each_category_has_required_fields(self, sample_health, tmp_path):
        generate_scores_json(sample_health, output_dir=str(tmp_path))
        data = json.loads((tmp_path / "scores.json").read_text())

        for cat_name, cat_data in data["categories"].items():
            assert "score" in cat_data, f"{cat_name} missing 'score'"
            assert "grade" in cat_data, f"{cat_name} missing 'grade'"
            assert "passed" in cat_data, f"{cat_name} missing 'passed'"
            assert "warnings" in cat_data, f"{cat_name} missing 'warnings'"
            assert "failed" in cat_data, f"{cat_name} missing 'failed'"

    def test_category_scores_bounded(self, sample_health, tmp_path):
        generate_scores_json(sample_health, output_dir=str(tmp_path))
        data = json.loads((tmp_path / "scores.json").read_text())

        for cat_name, cat_data in data["categories"].items():
            assert 0 <= cat_data["score"] <= 100, f"{cat_name} score out of range: {cat_data['score']}"

    def test_category_grades_valid(self, sample_health, tmp_path):
        generate_scores_json(sample_health, output_dir=str(tmp_path))
        data = json.loads((tmp_path / "scores.json").read_text())

        for cat_name, cat_data in data["categories"].items():
            assert cat_data["grade"] in ("A", "B", "C", "D", "F"), f"{cat_name} invalid grade"


class TestScoresJsonChecks:
    """Per-check schema -- this is what the LLM iterates to write findings."""

    def test_checks_is_list(self, sample_health, tmp_path):
        generate_scores_json(sample_health, output_dir=str(tmp_path))
        data = json.loads((tmp_path / "scores.json").read_text())
        assert isinstance(data["checks"], list)
        assert len(data["checks"]) > 0

    def test_each_check_has_required_fields(self, sample_health, tmp_path):
        generate_scores_json(sample_health, output_dir=str(tmp_path))
        data = json.loads((tmp_path / "scores.json").read_text())

        required = {"check_id", "category", "severity", "result", "message"}
        for check in data["checks"]:
            missing = required - set(check.keys())
            assert not missing, f"Check {check.get('check_id', '?')} missing: {missing}"

    def test_check_id_format(self, sample_health, tmp_path):
        generate_scores_json(sample_health, output_dir=str(tmp_path))
        data = json.loads((tmp_path / "scores.json").read_text())

        for check in data["checks"]:
            cid = check["check_id"]
            assert len(cid) >= 2, f"check_id too short: {cid}"
            # Should start with category prefix (R, CV, C, O, P, PR, SA)
            assert cid[0].isalpha(), f"check_id should start with letter: {cid}"

    def test_severity_values_valid(self, sample_health, tmp_path):
        generate_scores_json(sample_health, output_dir=str(tmp_path))
        data = json.loads((tmp_path / "scores.json").read_text())

        valid_severities = {"critical", "high", "medium", "low"}
        for check in data["checks"]:
            assert check["severity"] in valid_severities, f"{check['check_id']} invalid severity: {check['severity']}"

    def test_result_values_valid(self, sample_health, tmp_path):
        generate_scores_json(sample_health, output_dir=str(tmp_path))
        data = json.loads((tmp_path / "scores.json").read_text())

        valid_results = {"pass", "warning", "fail", "na"}
        for check in data["checks"]:
            assert check["result"] in valid_results, f"{check['check_id']} invalid result: {check['result']}"

    def test_message_is_nonempty_string(self, sample_health, tmp_path):
        generate_scores_json(sample_health, output_dir=str(tmp_path))
        data = json.loads((tmp_path / "scores.json").read_text())

        for check in data["checks"]:
            assert isinstance(check["message"], str), f"{check['check_id']} message not string"
            assert len(check["message"]) > 0, f"{check['check_id']} has empty message"

    def test_current_value_and_threshold_present(self, sample_health, tmp_path):
        generate_scores_json(sample_health, output_dir=str(tmp_path))
        data = json.loads((tmp_path / "scores.json").read_text())

        for check in data["checks"]:
            assert "current_value" in check, f"{check['check_id']} missing current_value"
            assert "threshold" in check, f"{check['check_id']} missing threshold"

    def test_na_checks_have_null_current_value(self, sample_health, tmp_path):
        generate_scores_json(sample_health, output_dir=str(tmp_path))
        data = json.loads((tmp_path / "scores.json").read_text())

        na_checks = [c for c in data["checks"] if c["result"] == "na"]
        for check in na_checks:
            assert check["current_value"] is None, f"NA check {check['check_id']} should have null current_value"


class TestScoresJsonRoundTrip:
    """Verify scores.json is valid JSON and re-parseable."""

    def test_valid_json(self, sample_health, tmp_path):
        path = generate_scores_json(sample_health, output_dir=str(tmp_path))
        content = open(path).read()
        # Should not raise
        data = json.loads(content)
        assert isinstance(data, dict)

    def test_no_nan_values(self, sample_health, tmp_path):
        generate_scores_json(sample_health, output_dir=str(tmp_path))
        content = (tmp_path / "scores.json").read_text()
        # NaN is not valid JSON -- would break LLM parsing
        assert "NaN" not in content, "scores.json contains NaN (invalid JSON)"
        assert "Infinity" not in content, "scores.json contains Infinity (invalid JSON)"
