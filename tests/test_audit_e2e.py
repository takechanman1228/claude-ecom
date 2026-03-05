"""End-to-end tests for the audit CLI pipeline.

Verifies: CSV input -> KPI computation -> scoring -> report generation.
"""

import json
import os

import pytest
from click.testing import CliRunner

from claude_ecom.cli import cli

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
ORDERS_CSV = os.path.join(FIXTURES_DIR, "sample_orders.csv")
PRODUCTS_CSV = os.path.join(FIXTURES_DIR, "sample_products.csv")
INVENTORY_CSV = os.path.join(FIXTURES_DIR, "sample_inventory.csv")


class TestAuditBasic:
    """Basic audit with orders-only CSV."""

    def test_exit_code_zero(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["audit", ORDERS_CSV, "--output", str(tmp_path)])
        assert result.exit_code == 0, f"Audit failed:\n{result.output}"

    def test_generates_all_output_files(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, ["audit", ORDERS_CSV, "--output", str(tmp_path)])
        assert (tmp_path / "scores.json").exists(), "Missing scores.json"
        assert (tmp_path / "AUDIT-REPORT.md").exists(), "Missing AUDIT-REPORT.md"
        assert (tmp_path / "executive-summary.md").exists(), "Missing executive-summary.md"

    def test_scores_json_is_valid(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, ["audit", ORDERS_CSV, "--output", str(tmp_path)])
        data = json.loads((tmp_path / "scores.json").read_text())
        assert "overall_score" in data
        assert "overall_grade" in data
        assert "checks" in data
        assert len(data["checks"]) > 0

    def test_overall_score_is_reasonable(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, ["audit", ORDERS_CSV, "--output", str(tmp_path)])
        data = json.loads((tmp_path / "scores.json").read_text())
        assert 0 <= data["overall_score"] <= 100

    def test_categories_present(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, ["audit", ORDERS_CSV, "--output", str(tmp_path)])
        data = json.loads((tmp_path / "scores.json").read_text())
        # Orders-only audit should have at least revenue and retention
        assert "revenue" in data["categories"]
        assert "retention" in data["categories"]


class TestAuditWithProducts:
    """Audit with orders + products CSV."""

    def test_product_category_present(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "audit", ORDERS_CSV,
            "--products", PRODUCTS_CSV,
            "--output", str(tmp_path),
        ])
        assert result.exit_code == 0, result.output
        data = json.loads((tmp_path / "scores.json").read_text())
        assert "product" in data["categories"]

    def test_product_checks_exist(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, [
            "audit", ORDERS_CSV,
            "--products", PRODUCTS_CSV,
            "--output", str(tmp_path),
        ])
        data = json.loads((tmp_path / "scores.json").read_text())
        product_checks = [c for c in data["checks"] if c["category"] == "product"]
        assert len(product_checks) > 0


class TestAuditWithInventory:
    """Audit with orders + products + inventory CSV."""

    def test_inventory_category_present(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "audit", ORDERS_CSV,
            "--products", PRODUCTS_CSV,
            "--inventory", INVENTORY_CSV,
            "--output", str(tmp_path),
        ])
        assert result.exit_code == 0, result.output
        data = json.loads((tmp_path / "scores.json").read_text())
        assert "inventory" in data["categories"]

    def test_inventory_checks_exist(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, [
            "audit", ORDERS_CSV,
            "--products", PRODUCTS_CSV,
            "--inventory", INVENTORY_CSV,
            "--output", str(tmp_path),
        ])
        data = json.loads((tmp_path / "scores.json").read_text())
        inv_checks = [c for c in data["checks"] if c["category"] == "inventory"]
        assert len(inv_checks) > 0


class TestAuditReportContent:
    """Verify AUDIT-REPORT.md has expected structure."""

    @pytest.fixture(autouse=True)
    def run_audit(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, [
            "audit", ORDERS_CSV,
            "--products", PRODUCTS_CSV,
            "--inventory", INVENTORY_CSV,
            "--output", str(tmp_path),
        ])
        self.report = (tmp_path / "AUDIT-REPORT.md").read_text()
        self.summary = (tmp_path / "executive-summary.md").read_text()

    def test_report_has_executive_summary(self):
        assert "Executive Summary" in self.report

    def test_report_has_score(self):
        assert "/100" in self.report
        assert "Grade:" in self.report or "grade" in self.report.lower()

    def test_report_has_category_breakdown(self):
        assert "Revenue" in self.report or "revenue" in self.report
        assert "Retention" in self.report or "retention" in self.report

    def test_report_has_detailed_findings(self):
        assert "Findings" in self.report or "Check" in self.report

    def test_executive_summary_has_score(self):
        assert "/100" in self.summary


class TestAuditNoData:
    """Edge case: missing required arg."""

    def test_no_orders_path_errors(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["audit"])
        assert result.exit_code != 0


class TestAuditScoresJsonNoNaN:
    """Ensure scores.json never contains NaN -- breaks JSON parsing."""

    def test_no_nan_with_minimal_data(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, ["audit", ORDERS_CSV, "--output", str(tmp_path)])
        content = (tmp_path / "scores.json").read_text()
        assert "NaN" not in content
        assert "Infinity" not in content

    def test_no_nan_with_full_data(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, [
            "audit", ORDERS_CSV,
            "--products", PRODUCTS_CSV,
            "--inventory", INVENTORY_CSV,
            "--output", str(tmp_path),
        ])
        content = (tmp_path / "scores.json").read_text()
        assert "NaN" not in content
        assert "Infinity" not in content
