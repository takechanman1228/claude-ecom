"""Tests for claude_ecom.loader."""

import os

import pandas as pd

from claude_ecom.loader import (
    _auto_map_columns,
    _fuzzy_map_columns,
    _normalise_generic_orders,
    detect_format,
    load_orders,
    validate_schema,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
ORDERS_CSV = os.path.join(FIXTURES, "sample_orders.csv")
ONLINE_RETAIL_CSV = os.path.join(FIXTURES, "online_retail_sample.csv")


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


class TestOnlineRetailFormat:
    def test_load_returns_dataframe(self):
        df = load_orders(ONLINE_RETAIL_CSV)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5

    def test_required_columns_present(self):
        df = load_orders(ONLINE_RETAIL_CSV)
        for col in ("order_id", "order_date", "amount", "customer_id"):
            assert col in df.columns

    def test_optional_columns_mapped(self):
        df = load_orders(ONLINE_RETAIL_CSV)
        for col in ("sku", "product_name", "quantity"):
            assert col in df.columns

    def test_amount_derived(self):
        df = load_orders(ONLINE_RETAIL_CSV)
        # First row: 12 * 6.95 = 83.4
        assert abs(df["amount"].iloc[0] - 83.4) < 0.01

    def test_negative_quantity_amount(self):
        df = load_orders(ONLINE_RETAIL_CSV)
        # Row 4 (index 3): -2 * 4.95 = -9.9
        assert abs(df["amount"].iloc[3] - (-9.9)) < 0.01

    def test_order_date_is_datetime(self):
        df = load_orders(ONLINE_RETAIL_CSV)
        assert pd.api.types.is_datetime64_any_dtype(df["order_date"])

    def test_amount_not_overwritten(self):
        """When amount already present in CSV, derivation is skipped."""
        df = pd.DataFrame({
            "order_id": ["A1"],
            "order_date": ["2024-01-01"],
            "amount": [100.0],
            "customer_id": ["C1"],
            "quantity": [10],
            "item_price": [5.0],
        })
        df = _normalise_generic_orders(df)
        assert df["amount"].iloc[0] == 100.0

    def test_fuzzy_does_not_overwrite_tier1(self):
        """Tier 1 mapped columns should not be re-consumed by fuzzy mapper."""
        df = pd.DataFrame({
            "Invoice": ["A1"],
            "order_date": ["2024-01-01"],
            "amount": [50.0],
            "customer_id": ["C1"],
        })
        df, mapped = _auto_map_columns(df)
        assert mapped.get("Invoice") == "order_id"
        # Fuzzy should not remap order_id to something else
        df2, fuzzy_mapped = _fuzzy_map_columns(df, already_mapped=mapped)
        assert "order_id" in df2.columns
