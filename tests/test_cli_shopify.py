"""Tests for Shopify CLI commands in claude_ecom.cli."""

import os
import pytest
from click.testing import CliRunner

from claude_ecom.cli import cli
from claude_ecom.shopify_api import parse_jsonl_stream
from claude_ecom.normalize import (
    normalize_orders,
    normalize_order_items,
    normalize_products,
    normalize_inventory,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
ORDERS_CSV = os.path.join(FIXTURES, "sample_orders.csv")
SHOPIFY_FIXTURES = os.path.join(FIXTURES, "shopify_api")


def _load_jsonl(name: str) -> list[dict]:
    with open(os.path.join(SHOPIFY_FIXTURES, name), "rb") as f:
        return list(parse_jsonl_stream(f.read()))


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def synced_data_dir(tmp_path):
    """Create a directory with pre-synced data files for testing."""
    order_rows = _load_jsonl("orders_bulk.jsonl")
    product_rows = _load_jsonl("products_bulk.jsonl")
    inventory_rows = _load_jsonl("inventory_bulk.jsonl")

    orders = normalize_orders(order_rows)
    items = normalize_order_items(order_rows)
    products = normalize_products(product_rows)
    inv = normalize_inventory(inventory_rows)

    data_dir = tmp_path / ".claude-ecom" / "data"
    data_dir.mkdir(parents=True)

    orders.to_csv(data_dir / "orders.csv", index=False)
    items.to_csv(data_dir / "order_items.csv", index=False)
    products.to_csv(data_dir / "products.csv", index=False)
    inv.to_csv(data_dir / "inventory.csv", index=False)

    return tmp_path


class TestAuditCSVBackwardCompat:
    """Verify existing CSV audit still works unchanged."""

    def test_audit_csv_with_path(self, runner, tmp_path):
        result = runner.invoke(cli, [
            "audit", ORDERS_CSV, "--output", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "Overall Score" in result.output

    def test_audit_csv_no_path_errors(self, runner):
        result = runner.invoke(cli, ["audit"])
        assert result.exit_code != 0

    def test_audit_source_csv_no_path_errors(self, runner):
        result = runner.invoke(cli, ["audit", "--source", "csv"])
        # Should fail because no ORDERS_PATH given
        assert result.exit_code != 0


class TestShopifyGroup:
    def test_shopify_group_help(self, runner):
        result = runner.invoke(cli, ["shopify", "--help"])
        assert result.exit_code == 0
        assert "setup" in result.output
        assert "sync" in result.output

    def test_shopify_setup_help(self, runner):
        result = runner.invoke(cli, ["shopify", "setup", "--help"])
        assert result.exit_code == 0
        assert "global" in result.output.lower()

    def test_shopify_sync_help(self, runner):
        result = runner.invoke(cli, ["shopify", "sync", "--help"])
        assert result.exit_code == 0
        assert "--since" in result.output
        assert "--mode" in result.output


class TestAuditWithSyncedData:
    """Test audit --source shopify using pre-synced fixture data."""

    def test_audit_shopify_source_needs_since(self, runner):
        result = runner.invoke(cli, ["audit", "--source", "shopify"])
        assert result.exit_code != 0
        assert "since" in result.output.lower() or "since" in str(result.exception).lower()

    def test_audit_with_presynced_data(self, runner, synced_data_dir, monkeypatch):
        """Test audit pipeline with pre-synced data, bypassing live API."""
        from claude_ecom import cli as cli_module
        from claude_ecom.sync import load_synced_data

        # Monkeypatch _audit_shopify to skip the sync step and just load data
        data_dir = synced_data_dir / ".claude-ecom" / "data"

        def mock_audit_shopify(output, since, until, site_url=None):
            from claude_ecom.metrics import compute_revenue_kpis, compute_cohort_kpis
            from claude_ecom.scoring import score_checks

            orders, products, inventory = load_synced_data(str(data_dir))
            rev_kpis = compute_revenue_kpis(orders)
            cohort_kpis = compute_cohort_kpis(orders)
            checks = cli_module._build_checks(rev_kpis, cohort_kpis, orders, products, inventory)
            health = score_checks(checks)

            click_echo = __import__("click").echo
            click_echo(f"Overall Score: {health.overall_score}/100 (Grade: {health.overall_grade})")

        monkeypatch.setattr(cli_module, "_audit_shopify", mock_audit_shopify)

        result = runner.invoke(cli, [
            "audit", "--source", "shopify", "--since", "2024-01-01",
        ])
        assert result.exit_code == 0
        assert "Overall Score" in result.output
