"""Tests for ecom_analytics.sync."""

import os
import pytest
import pandas as pd

from ecom_analytics.sync import (
    SyncState,
    write_state,
    read_state,
    load_synced_data,
    _write_dataframe,
    _read_dataframe,
)
from ecom_analytics.shopify_api import parse_jsonl_stream
from ecom_analytics.normalize import (
    normalize_orders,
    normalize_order_items,
    normalize_products,
    normalize_inventory,
)
from ecom_analytics.loader import validate_schema

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "shopify_api")


def _load_jsonl(name: str) -> list[dict]:
    with open(os.path.join(FIXTURES, name), "rb") as f:
        return list(parse_jsonl_stream(f.read()))


@pytest.fixture
def synced_dir(tmp_path):
    """Create a directory with synced data files."""
    order_rows = _load_jsonl("orders_bulk.jsonl")
    product_rows = _load_jsonl("products_bulk.jsonl")
    inventory_rows = _load_jsonl("inventory_bulk.jsonl")

    orders = normalize_orders(order_rows)
    items = normalize_order_items(order_rows)
    products = normalize_products(product_rows)
    inv = normalize_inventory(inventory_rows)

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Write as CSV (no pyarrow dependency required for tests)
    orders.to_csv(data_dir / "orders.csv", index=False)
    items.to_csv(data_dir / "order_items.csv", index=False)
    products.to_csv(data_dir / "products.csv", index=False)
    inv.to_csv(data_dir / "inventory.csv", index=False)

    return data_dir


class TestSyncState:
    def test_round_trip(self, tmp_path):
        state = SyncState(
            last_synced_at="2024-03-15T10:00:00Z",
            since="2024-01-01",
            until="2024-03-31",
            mode="full",
            record_counts={"orders": 100, "products": 50},
        )
        write_state(state, tmp_path)
        loaded = read_state(tmp_path)

        assert loaded is not None
        assert loaded.last_synced_at == state.last_synced_at
        assert loaded.since == state.since
        assert loaded.until == state.until
        assert loaded.mode == state.mode
        assert loaded.record_counts == state.record_counts

    def test_read_missing_returns_none(self, tmp_path):
        assert read_state(tmp_path) is None

    def test_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "deep" / "nested"
        state = SyncState(since="2024-01-01")
        write_state(state, nested)
        assert (nested / "sync_state.json").exists()


class TestWriteReadDataframe:
    def test_csv_fallback(self, tmp_path):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        _write_dataframe(df, tmp_path, "test")

        # Should have written either parquet or csv
        has_parquet = (tmp_path / "test.parquet").exists()
        has_csv = (tmp_path / "test.csv").exists()
        assert has_parquet or has_csv

        loaded = _read_dataframe(tmp_path, "test")
        assert loaded is not None
        assert len(loaded) == 3

    def test_read_missing_returns_none(self, tmp_path):
        assert _read_dataframe(tmp_path, "nonexistent") is None


class TestLoadSyncedData:
    def test_returns_three_dataframes(self, synced_dir):
        orders_compat, products, inventory = load_synced_data(synced_dir)

        assert isinstance(orders_compat, pd.DataFrame)
        assert len(orders_compat) > 0
        assert products is not None
        assert inventory is not None

    def test_orders_compat_passes_schema(self, synced_dir):
        orders_compat, _, _ = load_synced_data(synced_dir)
        result = validate_schema(orders_compat, "orders")
        assert result.valid, f"Missing columns: {result.missing_columns}"

    def test_orders_compat_has_datetime(self, synced_dir):
        orders_compat, _, _ = load_synced_data(synced_dir)
        assert pd.api.types.is_datetime64_any_dtype(orders_compat["order_date"])

    def test_inventory_has_quantity_on_hand(self, synced_dir):
        _, _, inventory = load_synced_data(synced_dir)
        assert inventory is not None
        assert "quantity_on_hand" in inventory.columns
        assert "sku" in inventory.columns

    def test_products_has_required_columns(self, synced_dir):
        _, products, _ = load_synced_data(synced_dir)
        assert products is not None
        assert "name" in products.columns
        assert "price" in products.columns

    def test_missing_data_raises(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="No synced order data"):
            load_synced_data(empty_dir)
