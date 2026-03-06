"""End-to-end tests for the review CLI pipeline.

Verifies: CSV input -> KPI computation -> scoring -> review.json generation.
"""

import json
import os

import pytest
from click.testing import CliRunner

from claude_ecom.cli import cli

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
ORDERS_CSV = os.path.join(FIXTURES_DIR, "sample_orders.csv")


class TestReviewBasic:
    """Basic review with orders-only CSV."""

    def test_exit_code_zero(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["review", ORDERS_CSV, "--output", str(tmp_path)])
        assert result.exit_code == 0, f"Review failed:\n{result.output}"

    def test_generates_review_json(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, ["review", ORDERS_CSV, "--output", str(tmp_path)])
        assert (tmp_path / "review.json").exists(), "Missing review.json"

    def test_review_json_is_valid(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, ["review", ORDERS_CSV, "--output", str(tmp_path)])
        data = json.loads((tmp_path / "review.json").read_text())
        assert "health" in data
        assert "checks" in data["health"]
        assert isinstance(data["health"]["checks"], list)


class TestReviewNoData:
    """Edge case: missing required arg."""

    def test_no_orders_path_errors(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["review"])
        assert result.exit_code != 0


class TestReviewJsonNoNaN:
    """Ensure review.json never contains NaN -- breaks JSON parsing."""

    def test_no_nan_with_minimal_data(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, ["review", ORDERS_CSV, "--output", str(tmp_path)])
        content = (tmp_path / "review.json").read_text()
        assert "NaN" not in content
        assert "Infinity" not in content
