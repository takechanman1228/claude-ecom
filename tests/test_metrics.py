"""Tests for claude_ecom.metrics."""

import os

import pandas as pd
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

    def test_repeat_purchase_rate_bounded(self, orders):
        kpis = compute_cohort_kpis(orders)
        assert 0 <= kpis["repeat_purchase_rate"] <= 1

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


class TestPartialMonthMetrics:
    """Tests for partial last month detection in compute_revenue_kpis."""

    def _make_full_month_orders(self, year, month, days_count, daily_amount=1000.0):
        rows = []
        for i in range(days_count):
            d = pd.Timestamp(year, month, 1) + pd.Timedelta(days=i)
            rows.append({
                "order_id": f"O-{year}{month:02d}-{i}",
                "order_date": d,
                "customer_id": f"C-{i}",
                "amount": daily_amount,
            })
        return rows

    def test_detects_partial_last_month(self):
        """3 days in January should be flagged as partial."""
        rows = self._make_full_month_orders(2025, 11, 30)
        rows += self._make_full_month_orders(2025, 12, 31)
        # Only 3 days in Jan
        for i in range(3):
            d = pd.Timestamp("2026-01-01") + pd.Timedelta(days=i)
            rows.append({
                "order_id": f"O-jan-{i}", "order_date": d,
                "customer_id": f"C-jan-{i}", "amount": 100.0,
            })
        df = pd.DataFrame(rows)
        df["order_date"] = pd.to_datetime(df["order_date"])
        kpis = compute_revenue_kpis(df)
        assert kpis["partial_last_month"] is True
        assert kpis["partial_last_month_days"] == 3
        assert kpis["partial_last_month_label"] == "2026-01"

    def test_full_month_not_partial(self):
        """A full month should not be flagged as partial."""
        rows = self._make_full_month_orders(2025, 11, 30)
        rows += self._make_full_month_orders(2025, 12, 31)
        df = pd.DataFrame(rows)
        df["order_date"] = pd.to_datetime(df["order_date"])
        kpis = compute_revenue_kpis(df)
        assert kpis["partial_last_month"] is False

    def test_mom_uses_complete_months(self):
        """MoM should be computed from complete months when last is partial."""
        rows = self._make_full_month_orders(2025, 11, 30, daily_amount=1000.0)
        rows += self._make_full_month_orders(2025, 12, 31, daily_amount=1100.0)
        # 3 days in Jan (partial)
        for i in range(3):
            d = pd.Timestamp("2026-01-01") + pd.Timedelta(days=i)
            rows.append({
                "order_id": f"O-jan-{i}", "order_date": d,
                "customer_id": f"C-jan-{i}", "amount": 50.0,
            })
        df = pd.DataFrame(rows)
        df["order_date"] = pd.to_datetime(df["order_date"])
        kpis = compute_revenue_kpis(df)
        # MoM should be Dec vs Nov (~10% growth), not Jan(150) vs Dec(34100)
        mom = kpis["mom_growth_latest"]
        assert mom > 0, "MoM should be positive (Dec > Nov)"
        assert mom < 0.5, f"MoM {mom:.1%} is too high, likely comparing wrong months"
