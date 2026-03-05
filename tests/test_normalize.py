"""Tests for ecom_analytics.normalize."""

import os
import pytest
import pandas as pd

from ecom_analytics.shopify_api import parse_jsonl_stream
from ecom_analytics.normalize import (
    normalize_orders,
    normalize_order_items,
    normalize_products,
    normalize_inventory,
    build_orders_compat,
    _hash_email,
    _guest_id,
)
from ecom_analytics.loader import validate_schema

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "shopify_api")


def _load_jsonl(name: str) -> list[dict]:
    with open(os.path.join(FIXTURES, name), "rb") as f:
        return list(parse_jsonl_stream(f.read()))


@pytest.fixture
def order_rows():
    return _load_jsonl("orders_bulk.jsonl")


@pytest.fixture
def product_rows():
    return _load_jsonl("products_bulk.jsonl")


@pytest.fixture
def inventory_rows():
    return _load_jsonl("inventory_bulk.jsonl")


class TestNormalizeOrders:
    def test_column_names(self, order_rows):
        df = normalize_orders(order_rows)
        expected = {
            "order_id", "order_date", "customer_id", "gross_revenue",
            "discount_amount", "shipping_amount", "tax_amount", "net_revenue",
            "currency", "financial_status", "fulfillment_status",
        }
        assert expected.issubset(set(df.columns))

    def test_row_count(self, order_rows):
        df = normalize_orders(order_rows)
        assert len(df) == 10

    def test_order_date_is_datetime(self, order_rows):
        df = normalize_orders(order_rows)
        assert pd.api.types.is_datetime64_any_dtype(df["order_date"])

    def test_revenue_is_numeric(self, order_rows):
        df = normalize_orders(order_rows)
        assert pd.api.types.is_numeric_dtype(df["gross_revenue"])
        assert (df["gross_revenue"] > 0).all()

    def test_pii_hashed_by_default(self, order_rows):
        df = normalize_orders(order_rows, allow_pii=False)
        # No raw email addresses should appear
        assert not df["customer_id"].str.contains("@").any()

    def test_allow_pii_keeps_email(self, order_rows):
        df = normalize_orders(order_rows, allow_pii=True)
        emails = df[df["customer_id"].str.contains("@", na=False)]
        assert len(emails) > 0

    def test_guest_order_gets_pseudo_id(self, order_rows):
        df = normalize_orders(order_rows)
        # Order 1004 has null customer
        order_1004 = df[df["order_id"] == "#1004"]
        assert len(order_1004) == 1
        assert order_1004.iloc[0]["customer_id"].startswith("guest_")

    def test_guest_id_is_deterministic(self, order_rows):
        df1 = normalize_orders(order_rows)
        df2 = normalize_orders(order_rows)
        guest1 = df1[df1["customer_id"].str.startswith("guest_")]["customer_id"].iloc[0]
        guest2 = df2[df2["customer_id"].str.startswith("guest_")]["customer_id"].iloc[0]
        assert guest1 == guest2

    def test_net_revenue_equals_gross_minus_discount(self, order_rows):
        df = normalize_orders(order_rows)
        expected = df["gross_revenue"] - df["discount_amount"]
        pd.testing.assert_series_equal(df["net_revenue"], expected, check_names=False)

    def test_empty_input(self):
        df = normalize_orders([])
        assert len(df) == 0
        assert "order_id" in df.columns


class TestNormalizeOrderItems:
    def test_column_names(self, order_rows):
        df = normalize_order_items(order_rows)
        expected = {
            "order_id", "product_id", "variant_id", "sku", "title",
            "quantity", "unit_price", "line_revenue", "line_discount",
        }
        assert expected.issubset(set(df.columns))

    def test_row_count(self, order_rows):
        df = normalize_order_items(order_rows)
        # 16 line items across 10 orders
        assert len(df) == 16

    def test_quantity_positive(self, order_rows):
        df = normalize_order_items(order_rows)
        assert (df["quantity"] > 0).all()

    def test_sku_present(self, order_rows):
        df = normalize_order_items(order_rows)
        assert (df["sku"].str.len() > 0).all()


class TestNormalizeProducts:
    def test_column_names(self, product_rows):
        df = normalize_products(product_rows)
        expected = {
            "product_id", "variant_id", "sku", "title", "category",
            "price", "compare_at", "cost",
        }
        assert expected.issubset(set(df.columns))

    def test_row_count(self, product_rows):
        df = normalize_products(product_rows)
        # 7 variants across 5 products
        assert len(df) == 7

    def test_price_positive(self, product_rows):
        df = normalize_products(product_rows)
        assert (df["price"] > 0).all()

    def test_cost_present(self, product_rows):
        df = normalize_products(product_rows)
        assert (df["cost"] > 0).all()


class TestNormalizeInventory:
    def test_column_names(self, inventory_rows):
        df = normalize_inventory(inventory_rows)
        expected = {"sku", "location_id", "on_hand"}
        assert expected.issubset(set(df.columns))

    def test_row_count(self, inventory_rows):
        df = normalize_inventory(inventory_rows)
        # 10 inventory levels across 7 items
        assert len(df) == 10

    def test_stockout_items(self, inventory_rows):
        df = normalize_inventory(inventory_rows)
        stockout = df[df["on_hand"] <= 0]
        # JKT-DNM-M and SCF-SLK-01 (2 locations) = 3 rows
        assert len(stockout) == 3


class TestBuildOrdersCompat:
    def test_schema_matches_loader_output(self, order_rows):
        orders = normalize_orders(order_rows)
        items = normalize_order_items(order_rows)
        compat = build_orders_compat(orders, items)

        # Must pass the existing orders schema validation
        result = validate_schema(compat, "orders")
        assert result.valid, f"Missing columns: {result.missing_columns}"

    def test_required_columns_present(self, order_rows):
        orders = normalize_orders(order_rows)
        items = normalize_order_items(order_rows)
        compat = build_orders_compat(orders, items)

        for col in ("order_id", "order_date", "amount", "customer_id"):
            assert col in compat.columns

    def test_optional_columns_present(self, order_rows):
        orders = normalize_orders(order_rows)
        items = normalize_order_items(order_rows)
        compat = build_orders_compat(orders, items)

        for col in ("discount", "sku", "product_name", "quantity", "item_price"):
            assert col in compat.columns

    def test_amount_is_numeric(self, order_rows):
        orders = normalize_orders(order_rows)
        items = normalize_order_items(order_rows)
        compat = build_orders_compat(orders, items)

        assert pd.api.types.is_numeric_dtype(compat["amount"])

    def test_order_date_is_datetime(self, order_rows):
        orders = normalize_orders(order_rows)
        items = normalize_order_items(order_rows)
        compat = build_orders_compat(orders, items)

        assert pd.api.types.is_datetime64_any_dtype(compat["order_date"])


class TestHelpers:
    def test_hash_email_consistent(self):
        h1 = _hash_email("Alice@Example.com")
        h2 = _hash_email("alice@example.com")
        assert h1 == h2

    def test_guest_id_deterministic(self):
        g1 = _guest_id("gid://shopify/Order/123")
        g2 = _guest_id("gid://shopify/Order/123")
        assert g1 == g2
        assert g1.startswith("guest_")

    def test_guest_id_unique_per_order(self):
        g1 = _guest_id("gid://shopify/Order/123")
        g2 = _guest_id("gid://shopify/Order/456")
        assert g1 != g2
