"""Tests for ecom_analytics.loader."""

import os
import pytest
import pandas as pd

from ecom_analytics.loader import (
    load_orders,
    load_products,
    load_inventory,
    detect_format,
    validate_schema,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
ORDERS_CSV = os.path.join(FIXTURES, "sample_orders.csv")
PRODUCTS_CSV = os.path.join(FIXTURES, "sample_products.csv")
INVENTORY_CSV = os.path.join(FIXTURES, "sample_inventory.csv")


class TestDetectFormat:
    def test_generic_format(self):
        assert detect_format(ORDERS_CSV) == "generic"


class TestLoadOrders:
    def test_load_returns_dataframe(self):
        df = load_orders(ORDERS_CSV)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 500

    def test_required_columns_present(self):
        df = load_orders(ORDERS_CSV)
        for col in ("order_id", "order_date", "amount", "customer_id"):
            assert col in df.columns

    def test_order_date_is_datetime(self):
        df = load_orders(ORDERS_CSV)
        assert pd.api.types.is_datetime64_any_dtype(df["order_date"])

    def test_amount_is_numeric(self):
        df = load_orders(ORDERS_CSV)
        assert pd.api.types.is_numeric_dtype(df["amount"])


class TestLoadProducts:
    def test_load_returns_dataframe(self):
        df = load_products(PRODUCTS_CSV)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 50

    def test_required_columns(self):
        df = load_products(PRODUCTS_CSV)
        for col in ("product_id", "name", "price", "category"):
            assert col in df.columns


class TestLoadInventory:
    def test_load_returns_dataframe(self):
        df = load_inventory(INVENTORY_CSV)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 50

    def test_required_columns(self):
        df = load_inventory(INVENTORY_CSV)
        assert "sku" in df.columns
        assert "quantity_on_hand" in df.columns


class TestValidateSchema:
    def test_valid_orders(self):
        df = load_orders(ORDERS_CSV)
        result = validate_schema(df, "orders")
        assert result.valid is True
        assert result.missing_columns == []

    def test_missing_columns(self):
        df = pd.DataFrame({"foo": [1]})
        result = validate_schema(df, "orders")
        assert result.valid is False
        assert len(result.missing_columns) > 0
