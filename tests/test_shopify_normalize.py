"""Tests for Shopify data normalization in claude_ecom."""

import os

import pytest

from claude_ecom.shopify_api import parse_jsonl_stream
from claude_ecom.normalize import (
    normalize_orders,
    normalize_order_items,
    normalize_products,
    normalize_inventory,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
SHOPIFY_FIXTURES = os.path.join(FIXTURES, "shopify_api")


def _load_jsonl(name: str) -> list[dict]:
    with open(os.path.join(SHOPIFY_FIXTURES, name), "rb") as f:
        return list(parse_jsonl_stream(f.read()))


@pytest.mark.skipif(
    not os.path.isdir(os.path.join(FIXTURES, "shopify_api")),
    reason="Shopify fixtures not available",
)
class TestShopifyNormalize:
    """Verify normalization of Shopify JSONL data."""

    def test_normalize_orders(self):
        rows = _load_jsonl("orders_bulk.jsonl")
        df = normalize_orders(rows)
        assert "order_id" in df.columns
        assert "order_date" in df.columns
        assert len(df) > 0

    def test_normalize_order_items(self):
        rows = _load_jsonl("orders_bulk.jsonl")
        df = normalize_order_items(rows)
        assert "order_id" in df.columns
        assert len(df) > 0

    def test_normalize_products(self):
        rows = _load_jsonl("products_bulk.jsonl")
        df = normalize_products(rows)
        assert "product_id" in df.columns
        assert len(df) > 0

    def test_normalize_inventory(self):
        rows = _load_jsonl("inventory_bulk.jsonl")
        df = normalize_inventory(rows)
        assert len(df) > 0
