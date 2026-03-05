"""Inventory and stockout analysis."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class StockoutResult:
    """Stockout analysis output."""

    stockout_skus: list[str]
    stockout_rate: float
    estimated_lost_revenue: float
    details: pd.DataFrame


@dataclass
class OverstockResult:
    """Overstock analysis output."""

    overstock_skus: list[str]
    overstock_value: float
    deadstock_skus: list[str]
    deadstock_value: float
    details: pd.DataFrame


def stockout_analysis(inventory: pd.DataFrame, orders: pd.DataFrame) -> StockoutResult:
    """Identify stockout SKUs and estimate lost revenue.

    Lost revenue is estimated as: daily_avg_revenue × days_out_of_stock.
    If ``days_out_of_stock`` is not available, uses 7-day estimate.
    """
    stockout = inventory[inventory["quantity_on_hand"] <= 0].copy()
    stockout_skus = stockout["sku"].tolist()

    # Daily average revenue per SKU
    if "sku" in orders.columns:
        days_span = (orders["order_date"].max() - orders["order_date"].min()).days or 1
        sku_rev = orders.groupby("sku")["amount"].sum()
        sku_daily = sku_rev / days_span
    else:
        sku_daily = pd.Series(dtype=float)

    estimated_loss = 0.0
    details_rows = []
    for sku in stockout_skus:
        daily = sku_daily.get(sku, 0)
        assumed_days = 7
        loss = daily * assumed_days
        estimated_loss += loss
        details_rows.append({"sku": sku, "daily_avg_revenue": float(daily), "est_lost_revenue": float(loss)})

    return StockoutResult(
        stockout_skus=stockout_skus,
        stockout_rate=len(stockout_skus) / len(inventory) if len(inventory) else 0,
        estimated_lost_revenue=float(estimated_loss),
        details=pd.DataFrame(details_rows),
    )


def overstock_analysis(inventory: pd.DataFrame, orders: pd.DataFrame) -> OverstockResult:
    """Identify overstock (>90 days) and deadstock (>180 days) SKUs."""
    inv = inventory.copy()

    # Calculate days of stock on hand
    if "sku" in orders.columns:
        days_span = max((orders["order_date"].max() - orders["order_date"].min()).days, 1)
        sku_qty = (
            orders.groupby("sku")["quantity"].sum() if "quantity" in orders.columns else orders.groupby("sku").size()
        )
        sku_daily_qty = sku_qty / days_span
        inv = inv.merge(sku_daily_qty.rename("daily_sales"), on="sku", how="left")
        inv["daily_sales"] = inv["daily_sales"].fillna(0)
        inv["days_on_hand"] = np.where(
            inv["daily_sales"] > 0,
            inv["quantity_on_hand"] / inv["daily_sales"],
            999,
        )
    elif "days_on_hand" not in inv.columns:
        inv["days_on_hand"] = 999

    overstock = inv[inv["days_on_hand"] > 90]
    deadstock = inv[inv["days_on_hand"] > 180]

    cost_col = "cost" if "cost" in inv.columns else None

    def _value(df: pd.DataFrame) -> float:
        if cost_col:
            return float((df["quantity_on_hand"] * df[cost_col]).sum())
        return 0.0

    return OverstockResult(
        overstock_skus=overstock["sku"].tolist(),
        overstock_value=_value(overstock),
        deadstock_skus=deadstock["sku"].tolist(),
        deadstock_value=_value(deadstock),
        details=inv[["sku", "quantity_on_hand", "days_on_hand"]],
    )


def inventory_turnover(inventory: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    """Calculate inventory turnover ratio per SKU.

    Turnover = annual_sales_qty / avg_inventory.
    """
    if "sku" not in orders.columns:
        return pd.DataFrame()

    days_span = max((orders["order_date"].max() - orders["order_date"].min()).days, 1)
    qty_col = "quantity" if "quantity" in orders.columns else None

    if qty_col:
        annual_sales = orders.groupby("sku")[qty_col].sum() * (365 / days_span)
    else:
        annual_sales = orders.groupby("sku").size() * (365 / days_span)

    avg_inv = inventory.set_index("sku")["quantity_on_hand"]

    result = pd.DataFrame({"annual_sales": annual_sales, "avg_inventory": avg_inv})
    result["turnover"] = result["annual_sales"] / result["avg_inventory"].clip(lower=1)
    return result.reset_index()
