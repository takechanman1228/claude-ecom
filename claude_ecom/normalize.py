"""Normalize Shopify Bulk Operation JSONL data into DataFrames.

Transforms raw JSONL parent-child structures into flat DataFrames that
match the canonical schemas expected by metrics.py, cohort.py, etc.
"""

from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd

from claude_ecom.shopify_api import build_parent_child_map


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Extract a float from nested Shopify money fields or plain values."""
    if val is None:
        return default
    if isinstance(val, dict):
        # Handle shopMoney nesting: {"shopMoney": {"amount": "12.00"}}
        if "shopMoney" in val:
            return _safe_float(val["shopMoney"])
        if "amount" in val:
            try:
                return float(val["amount"])
            except (ValueError, TypeError):
                return default
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _hash_email(email: str) -> str:
    """SHA-256 hash an email for PII protection."""
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()[:16]


def _guest_id(order_gid: str) -> str:
    """Generate a deterministic pseudo customer ID for guest orders."""
    return "guest_" + hashlib.sha256(order_gid.encode()).hexdigest()[:12]


def normalize_orders(rows: list[dict], allow_pii: bool = False) -> pd.DataFrame:
    """Convert order JSONL rows into a normalized orders DataFrame.

    Parameters
    ----------
    rows : list[dict]
        Raw JSONL rows from the orders bulk operation.
    allow_pii : bool
        If True, keep raw email as customer_id. Otherwise SHA-256 hash.

    Returns
    -------
    pd.DataFrame
        Columns: order_id, order_date, customer_id, gross_revenue,
        discount_amount, shipping_amount, tax_amount, net_revenue,
        currency, financial_status, fulfillment_status
    """
    parents = build_parent_child_map(rows)

    records = []
    for gid, order in parents.items():
        if "Order" not in gid:
            continue

        customer = order.get("customer")
        if customer and customer.get("email"):
            cid = customer["email"] if allow_pii else _hash_email(customer["email"])
        else:
            cid = _guest_id(gid)

        gross = _safe_float(order.get("totalPriceSet"))
        discount = _safe_float(order.get("totalDiscountsSet"))
        shipping = _safe_float(order.get("totalShippingPriceSet"))
        tax = _safe_float(order.get("totalTaxSet"))

        price_set = order.get("totalPriceSet", {})
        shop_money = price_set.get("shopMoney", {}) if isinstance(price_set, dict) else {}
        currency = shop_money.get("currencyCode", "USD")

        records.append(
            {
                "order_id": order.get("name", gid),
                "order_date": pd.to_datetime(order["createdAt"], utc=True),
                "customer_id": cid,
                "gross_revenue": gross,
                "discount_amount": discount,
                "shipping_amount": shipping,
                "tax_amount": tax,
                "net_revenue": gross - discount,
                "currency": currency,
                "financial_status": (order.get("displayFinancialStatus") or "").lower(),
                "fulfillment_status": (order.get("displayFulfillmentStatus") or "").lower(),
            }
        )

    df = pd.DataFrame(records)
    if len(df) == 0:
        return pd.DataFrame(
            columns=[
                "order_id",
                "order_date",
                "customer_id",
                "gross_revenue",
                "discount_amount",
                "shipping_amount",
                "tax_amount",
                "net_revenue",
                "currency",
                "financial_status",
                "fulfillment_status",
            ]
        )
    return df


def normalize_order_items(rows: list[dict]) -> pd.DataFrame:
    """Convert order JSONL rows into a normalized line-items DataFrame.

    Returns
    -------
    pd.DataFrame
        Columns: order_id, product_id, variant_id, sku, title,
        quantity, unit_price, line_revenue, line_discount
    """
    parents = build_parent_child_map(rows)

    records = []
    for gid, order in parents.items():
        if "Order" not in gid:
            continue

        order_id = order.get("name", gid)
        for item in order.get("_children", []):
            variant = item.get("variant") or {}
            variant_id = variant.get("id", "")
            # Extract product GID from variant GID pattern
            product_id = ""
            if variant_id:
                product_id = variant_id  # Will be linked via products table

            records.append(
                {
                    "order_id": order_id,
                    "product_id": product_id,
                    "variant_id": variant_id,
                    "sku": variant.get("sku", ""),
                    "title": item.get("title", ""),
                    "quantity": item.get("quantity", 0),
                    "unit_price": _safe_float(variant.get("price")),
                    "line_revenue": _safe_float(item.get("originalTotalSet")),
                    "line_discount": _safe_float(item.get("totalDiscountSet")),
                }
            )

    df = pd.DataFrame(records)
    if len(df) == 0:
        return pd.DataFrame(
            columns=[
                "order_id",
                "product_id",
                "variant_id",
                "sku",
                "title",
                "quantity",
                "unit_price",
                "line_revenue",
                "line_discount",
            ]
        )
    return df


def normalize_products(rows: list[dict]) -> pd.DataFrame:
    """Convert product JSONL rows into a normalized products DataFrame.

    Returns
    -------
    pd.DataFrame
        Columns: product_id, variant_id, sku, title, category,
        price, compare_at, cost
    """
    parents = build_parent_child_map(rows)

    records = []
    for gid, product in parents.items():
        if "Product" not in gid:
            continue

        for variant in product.get("_children", []):
            inv_item = variant.get("inventoryItem") or {}
            unit_cost = inv_item.get("unitCost")

            records.append(
                {
                    "product_id": gid,
                    "variant_id": variant.get("id", ""),
                    "sku": variant.get("sku", ""),
                    "title": product.get("title", ""),
                    "category": product.get("productType", ""),
                    "price": _safe_float(variant.get("price")),
                    "compare_at": _safe_float(variant.get("compareAtPrice")),
                    "cost": _safe_float(unit_cost),
                    "vendor": product.get("vendor", ""),
                    "tags": (
                        ",".join(product.get("tags", []))
                        if isinstance(product.get("tags"), list)
                        else str(product.get("tags", ""))
                    ),
                }
            )

    df = pd.DataFrame(records)
    if len(df) == 0:
        return pd.DataFrame(
            columns=[
                "product_id",
                "variant_id",
                "sku",
                "title",
                "category",
                "price",
                "compare_at",
                "cost",
                "vendor",
                "tags",
            ]
        )
    return df


def normalize_inventory(rows: list[dict]) -> pd.DataFrame:
    """Convert inventory JSONL rows into a normalized inventory DataFrame.

    Returns
    -------
    pd.DataFrame
        Columns: sku, location_id, on_hand
    """
    parents = build_parent_child_map(rows)

    records = []
    for gid, item in parents.items():
        if "InventoryItem" not in gid:
            continue

        sku = item.get("sku", "")
        for level in item.get("_children", []):
            quantities = level.get("quantities", [])
            available = quantities[0].get("quantity", 0) if quantities else 0
            location = level.get("location", {})
            location_id = location.get("id", "")

            records.append(
                {
                    "sku": sku,
                    "location_id": location_id,
                    "on_hand": available,
                }
            )

    df = pd.DataFrame(records)
    if len(df) == 0:
        return pd.DataFrame(columns=["sku", "location_id", "on_hand"])
    return df


def build_orders_compat(
    orders_norm: pd.DataFrame,
    items_norm: pd.DataFrame,
) -> pd.DataFrame:
    """Build a flat DataFrame matching the existing loader.py output schema.

    This is the key integration point: downstream modules (metrics.py,
    cohort.py, product.py, etc.) receive identical schemas whether data
    came from CSV or API.

    Returns
    -------
    pd.DataFrame
        Columns: order_id, order_date, amount, customer_id, discount,
        shipping, sku, product_name, quantity, item_price
    """
    if items_norm.empty:
        # No line items — build from order-level data only
        return pd.DataFrame(
            {
                "order_id": orders_norm["order_id"],
                "order_date": orders_norm["order_date"],
                "amount": orders_norm["gross_revenue"],
                "customer_id": orders_norm["customer_id"],
                "discount": orders_norm["discount_amount"],
                "shipping": orders_norm["shipping_amount"],
                "sku": "",
                "product_name": "",
                "quantity": 1,
                "item_price": orders_norm["gross_revenue"],
            }
        )

    # Merge order-level fields with line items
    order_cols = orders_norm[["order_id", "order_date", "customer_id", "discount_amount", "shipping_amount"]].copy()

    merged = items_norm.merge(order_cols, on="order_id", how="left")

    return pd.DataFrame(
        {
            "order_id": merged["order_id"],
            "order_date": merged["order_date"],
            "amount": merged["line_revenue"],
            "customer_id": merged["customer_id"],
            "discount": merged["line_discount"],
            "shipping": merged["shipping_amount"],
            "sku": merged["sku"],
            "product_name": merged["title"],
            "quantity": merged["quantity"],
            "item_price": merged["unit_price"],
        }
    )
