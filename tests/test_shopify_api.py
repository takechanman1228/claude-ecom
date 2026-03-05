"""Tests for claude_ecom.shopify_api."""

import json
import os
import pytest

from claude_ecom.shopify_api import (
    parse_jsonl_stream,
    build_parent_child_map,
    build_orders_query,
    BulkRunner,
    ShopifyClient,
    ShopifyAPIError,
)
from claude_ecom.config import ShopifyConfig

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "shopify_api")


def _load_jsonl(name: str) -> list[dict]:
    path = os.path.join(FIXTURES, name)
    with open(path, "rb") as f:
        return list(parse_jsonl_stream(f.read()))


class TestParseJsonlStream:
    def test_parses_orders(self):
        rows = _load_jsonl("orders_bulk.jsonl")
        assert len(rows) > 0
        # First row should be an order (no __parentId)
        assert "__parentId" not in rows[0]
        assert "id" in rows[0]

    def test_parses_products(self):
        rows = _load_jsonl("products_bulk.jsonl")
        assert len(rows) > 0

    def test_parses_inventory(self):
        rows = _load_jsonl("inventory_bulk.jsonl")
        assert len(rows) > 0

    def test_empty_input(self):
        rows = list(parse_jsonl_stream(b""))
        assert rows == []

    def test_handles_blank_lines(self):
        raw = b'{"id":"1"}\n\n{"id":"2"}\n'
        rows = list(parse_jsonl_stream(raw))
        assert len(rows) == 2


class TestBuildParentChildMap:
    def test_orders_structure(self):
        rows = _load_jsonl("orders_bulk.jsonl")
        parents = build_parent_child_map(rows)

        # Should have 10 orders
        assert len(parents) == 10

        # Order 1001 should have 2 line items
        order_1001 = parents["gid://shopify/Order/1001"]
        assert order_1001["name"] == "#1001"
        assert len(order_1001["_children"]) == 2

        # Order 1003 should have 3 line items
        order_1003 = parents["gid://shopify/Order/1003"]
        assert len(order_1003["_children"]) == 3

    def test_products_structure(self):
        rows = _load_jsonl("products_bulk.jsonl")
        parents = build_parent_child_map(rows)

        assert len(parents) == 5
        # Classic T-Shirt has 2 variants
        tshirt = parents["gid://shopify/Product/4001"]
        assert tshirt["title"] == "Classic T-Shirt"
        assert len(tshirt["_children"]) == 2

    def test_inventory_structure(self):
        rows = _load_jsonl("inventory_bulk.jsonl")
        parents = build_parent_child_map(rows)

        assert len(parents) == 7
        # BAG-CNV-01 has 2 locations
        bag = parents["gid://shopify/InventoryItem/6003"]
        assert bag["sku"] == "BAG-CNV-01"
        assert len(bag["_children"]) == 2

    def test_guest_order_has_null_customer(self):
        rows = _load_jsonl("orders_bulk.jsonl")
        parents = build_parent_child_map(rows)
        order_1004 = parents["gid://shopify/Order/1004"]
        assert order_1004["customer"] is None


class TestBuildOrdersQuery:
    def test_no_filter(self):
        q = build_orders_query()
        assert "query:" not in q
        assert "orders" in q

    def test_with_since(self):
        q = build_orders_query(since="2024-01-01")
        assert "created_at:>='2024-01-01'" in q


class TestShopifyClient:
    def test_requires_httpx(self, monkeypatch):
        import claude_ecom.shopify_api as mod
        original = mod.httpx
        monkeypatch.setattr(mod, "httpx", None)
        try:
            cfg = ShopifyConfig(store_domain="test.myshopify.com", access_token="tok")
            with pytest.raises(ImportError, match="httpx"):
                ShopifyClient(cfg)
        finally:
            monkeypatch.setattr(mod, "httpx", original)


class TestBulkRunner:
    def test_state_file_round_trip(self, tmp_path):
        cfg = ShopifyConfig(store_domain="test.myshopify.com", access_token="tok")

        class FakeClient:
            pass

        runner = BulkRunner(FakeClient(), state_dir=tmp_path)
        assert runner._load_running_op() is None

        runner._save_running_op("gid://shopify/BulkOperation/123")
        assert runner._load_running_op() == "gid://shopify/BulkOperation/123"

        runner._clear_running_op()
        assert runner._load_running_op() is None
