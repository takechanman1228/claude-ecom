"""Tests for claude_ecom.metrics."""

import os
import pytest

from claude_ecom.loader import load_orders, load_products, load_inventory
from claude_ecom.metrics import (
    compute_revenue_kpis,
    compute_cohort_kpis,
    compute_product_kpis,
    compute_inventory_kpis,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
ORDERS_CSV = os.path.join(FIXTURES, "sample_orders.csv")
PRODUCTS_CSV = os.path.join(FIXTURES, "sample_products.csv")
INVENTORY_CSV = os.path.join(FIXTURES, "sample_inventory.csv")


@pytest.fixture
def orders():
    return load_orders(ORDERS_CSV)


@pytest.fixture
def products():
    return load_products(PRODUCTS_CSV)


@pytest.fixture
def inventory():
    return load_inventory(INVENTORY_CSV)


class TestRevenueKPIs:
    def test_returns_dict(self, orders):
        kpis = compute_revenue_kpis(orders)
        assert isinstance(kpis, dict)

    def test_total_revenue_positive(self, orders):
        kpis = compute_revenue_kpis(orders)
        assert kpis["total_revenue"] > 0

    def test_aov_positive(self, orders):
        kpis = compute_revenue_kpis(orders)
        assert kpis["aov"] > 0

    def test_repeat_revenue_share_bounded(self, orders):
        kpis = compute_revenue_kpis(orders)
        assert 0 <= kpis["repeat_revenue_share"] <= 1

    def test_discount_rate_bounded(self, orders):
        kpis = compute_revenue_kpis(orders)
        assert 0 <= kpis["avg_discount_rate"] <= 1


class TestCohortKPIs:
    def test_returns_dict(self, orders):
        kpis = compute_cohort_kpis(orders)
        assert isinstance(kpis, dict)

    def test_f2_rate_bounded(self, orders):
        kpis = compute_cohort_kpis(orders)
        assert 0 <= kpis["f2_rate"] <= 1

    def test_total_customers_positive(self, orders):
        kpis = compute_cohort_kpis(orders)
        assert kpis["total_customers"] > 0


class TestProductKPIs:
    def test_returns_dict(self, orders, products):
        kpis = compute_product_kpis(orders, products)
        assert isinstance(kpis, dict)

    def test_top20_share_bounded(self, orders, products):
        kpis = compute_product_kpis(orders, products)
        assert 0 <= kpis["top20_revenue_share"] <= 1


class TestInventoryKPIs:
    def test_returns_dict(self, inventory, orders):
        kpis = compute_inventory_kpis(inventory, orders)
        assert isinstance(kpis, dict)

    def test_stockout_rate_bounded(self, inventory, orders):
        kpis = compute_inventory_kpis(inventory, orders)
        assert 0 <= kpis["stockout_rate"] <= 1
