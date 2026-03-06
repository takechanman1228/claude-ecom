"""ETL orchestration for Shopify Admin API data sync."""
# NOTE: Not used by the current review flow. Kept for future integration.

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from claude_ecom.config import ShopifyConfig
from claude_ecom.normalize import (
    build_orders_compat,
    normalize_inventory,
    normalize_order_items,
    normalize_orders,
    normalize_products,
)
from claude_ecom.shopify_api import (
    INVENTORY_QUERY,
    PRODUCTS_QUERY,
    BulkRunner,
    ShopifyClient,
    build_orders_query,
)

logger = logging.getLogger(__name__)

_STATE_FILE = "sync_state.json"


@dataclass
class SyncState:
    """Persisted sync state."""

    last_synced_at: str = ""
    since: str = ""
    until: str = ""
    mode: str = "full"
    record_counts: dict[str, int] = field(default_factory=dict)


def write_state(state: SyncState, out_dir: str | Path) -> None:
    """Save sync state to JSON."""
    p = Path(out_dir) / _STATE_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(state), indent=2))


def read_state(out_dir: str | Path) -> SyncState | None:
    """Load sync state from JSON, or None if not found."""
    p = Path(out_dir) / _STATE_FILE
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    return SyncState(**data)


def _write_dataframe(df: pd.DataFrame, out_dir: Path, name: str) -> str:
    """Write a DataFrame as parquet (preferred) or CSV (fallback)."""
    try:
        import pyarrow  # noqa: F401

        path = out_dir / f"{name}.parquet"
        df.to_parquet(path, index=False)
        return str(path)
    except ImportError:
        path = out_dir / f"{name}.csv"
        df.to_csv(path, index=False)
        return str(path)


def _read_dataframe(out_dir: Path, name: str) -> pd.DataFrame | None:
    """Read a DataFrame from parquet or CSV."""
    parquet_path = out_dir / f"{name}.parquet"
    csv_path = out_dir / f"{name}.csv"

    if parquet_path.exists():
        try:
            return pd.read_parquet(parquet_path)
        except ImportError:
            pass

    if csv_path.exists():
        return pd.read_csv(csv_path)

    return None


def sync_shopify(
    cfg: ShopifyConfig,
    since: str,
    until: str | None = None,
    mode: str = "full",
    out_dir: str | Path = ".claude-ecom/data",
    progress_cb: Callable[[str, str, int], None] | None = None,
    timeout_minutes: int = 60,
) -> SyncState:
    """Run a full Shopify data sync via Bulk Operations.

    Parameters
    ----------
    cfg : ShopifyConfig
        Shopify API configuration.
    since : str
        Start date (ISO format, e.g. "2024-01-01").
    until : str | None
        End date (optional).
    mode : str
        "full" to fetch all data, "incremental" to merge with existing.
    out_dir : str | Path
        Directory for output files.
    progress_cb : callable | None
        Callback: ``progress_cb(operation_name, status, object_count)``.
    timeout_minutes : int
        Max time to wait for each bulk operation.

    Returns
    -------
    SyncState
        State with record counts and timestamps.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    client = ShopifyClient(cfg, timeout=30.0)
    runner = BulkRunner(client, state_dir=out_path, timeout_minutes=timeout_minutes)

    record_counts: dict[str, int] = {}

    def _progress(op_name: str):
        def cb(status: str, count: int):
            if progress_cb:
                progress_cb(op_name, status, count)

        return cb

    # --- 1. Orders + LineItems ---
    logger.info("Syncing orders (since=%s)...", since)
    orders_query = build_orders_query(since=since)
    order_rows = runner.run(orders_query, progress_cb=_progress("orders"))

    orders_norm = normalize_orders(order_rows, allow_pii=cfg.allow_pii)
    items_norm = normalize_order_items(order_rows)

    if mode == "incremental":
        existing_orders = _read_dataframe(out_path, "orders")
        if existing_orders is not None:
            orders_norm = pd.concat([existing_orders, orders_norm]).drop_duplicates(subset=["order_id"], keep="last")
        existing_items = _read_dataframe(out_path, "order_items")
        if existing_items is not None:
            items_norm = pd.concat([existing_items, items_norm]).drop_duplicates(
                subset=["order_id", "sku", "quantity"], keep="last"
            )

    _write_dataframe(orders_norm, out_path, "orders")
    _write_dataframe(items_norm, out_path, "order_items")
    record_counts["orders"] = len(orders_norm)
    record_counts["order_items"] = len(items_norm)

    # --- 2. Products + Variants ---
    logger.info("Syncing products...")
    product_rows = runner.run(PRODUCTS_QUERY, progress_cb=_progress("products"))
    products_norm = normalize_products(product_rows)
    _write_dataframe(products_norm, out_path, "products")
    record_counts["products"] = len(products_norm)

    # --- 3. Inventory ---
    logger.info("Syncing inventory...")
    inv_rows = runner.run(INVENTORY_QUERY, progress_cb=_progress("inventory"))
    inv_norm = normalize_inventory(inv_rows)
    _write_dataframe(inv_norm, out_path, "inventory")
    record_counts["inventory"] = len(inv_norm)

    # --- Save state ---
    state = SyncState(
        last_synced_at=datetime.now(timezone.utc).isoformat(),
        since=since,
        until=until or "",
        mode=mode,
        record_counts=record_counts,
    )
    write_state(state, out_path)

    client.close()
    return state


def load_synced_data(
    out_dir: str | Path = ".claude-ecom/data",
) -> tuple[pd.DataFrame, pd.DataFrame | None, pd.DataFrame | None]:
    """Load previously synced data and return compat DataFrames.

    Returns
    -------
    tuple
        (orders_compat, products, inventory) — orders_compat matches the
        existing loader.py output schema. products and inventory may be None.
    """
    out_path = Path(out_dir)

    orders = _read_dataframe(out_path, "orders")
    items = _read_dataframe(out_path, "order_items")

    if orders is None:
        raise FileNotFoundError(f"No synced order data found in {out_path}. Run 'ecom shopify sync' first.")
    if items is None:
        items = pd.DataFrame(
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

    # Parse dates if loaded from CSV
    if not pd.api.types.is_datetime64_any_dtype(orders["order_date"]):
        orders["order_date"] = pd.to_datetime(orders["order_date"], utc=True)

    orders_compat = build_orders_compat(orders, items)

    products = _read_dataframe(out_path, "products")
    inventory = _read_dataframe(out_path, "inventory")

    # Convert inventory to loader-compatible format
    if inventory is not None and "on_hand" in inventory.columns:
        # Aggregate across locations for compat
        inv_agg = inventory.groupby("sku", as_index=False)["on_hand"].sum()
        inv_agg = inv_agg.rename(columns={"on_hand": "quantity_on_hand"})
        inventory = inv_agg

    # Convert products to loader-compatible format
    if products is not None:
        products_compat = products.rename(
            columns={
                "title": "name",
            }
        )
        if "category" not in products_compat.columns and "productType" in products_compat.columns:
            products_compat = products_compat.rename(columns={"productType": "category"})
        products = products_compat

    return orders_compat, products, inventory
