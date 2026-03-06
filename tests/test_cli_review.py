"""Tests for the unified review CLI command."""

import json
import os

from click.testing import CliRunner

from claude_ecom.cli import cli

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
ORDERS_CSV = os.path.join(FIXTURES_DIR, "sample_orders.csv")


class TestReviewCommand:
    def test_produces_review_json(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["review", ORDERS_CSV, "--output", str(tmp_path)])
        assert result.exit_code == 0, result.output
        review_path = tmp_path / "review.json"
        assert review_path.exists()

    def test_review_json_valid(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["review", ORDERS_CSV, "--output", str(tmp_path)])
        assert result.exit_code == 0
        with open(tmp_path / "review.json") as f:
            data = json.load(f)
        assert "version" in data
        assert "metadata" in data
        assert "health" in data

    def test_period_filter(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["review", ORDERS_CSV, "--period", "30d", "--output", str(tmp_path)])
        assert result.exit_code == 0

    def test_nrows_option(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["review", ORDERS_CSV, "--nrows", "50", "--output", str(tmp_path)])
        assert result.exit_code == 0

    def test_shows_coverage(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["review", ORDERS_CSV, "--output", str(tmp_path)])
        assert result.exit_code == 0
        assert "Data coverage" in result.output
