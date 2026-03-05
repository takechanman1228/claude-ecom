"""CSV data loading and validation for ecommerce datasets."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Column mappings — Shopify export → internal canonical names
# ---------------------------------------------------------------------------

SHOPIFY_ORDER_COLUMNS = {
    "Name": "order_id",
    "Created at": "order_date",
    "Total": "amount",
    "Email": "customer_id",
    "Discount Amount": "discount",
    "Financial Status": "financial_status",
    "Shipping": "shipping",
    "Billing City": "city",
    "Lineitem name": "product_name",
    "Lineitem quantity": "quantity",
    "Lineitem price": "item_price",
    "Lineitem sku": "sku",
}

SHOPIFY_PRODUCT_COLUMNS = {
    "Handle": "product_id",
    "Title": "name",
    "Variant Price": "price",
    "Variant SKU": "sku",
    "Vendor": "vendor",
    "Type": "category",
    "Tags": "tags",
    "Variant Inventory Qty": "stock_quantity",
}

GENERIC_ORDER_REQUIRED = {"order_id", "order_date", "amount", "customer_id"}
GENERIC_PRODUCT_REQUIRED = {"product_id", "name", "price", "category"}
GENERIC_INVENTORY_REQUIRED = {"sku", "quantity_on_hand"}


@dataclass
class ValidationResult:
    """Result of schema validation."""

    valid: bool
    missing_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------


def detect_format(path: str) -> str:
    """Detect CSV format by inspecting column names.

    Returns ``"shopify"`` or ``"generic"``.
    """
    df_head = pd.read_csv(path, nrows=5)
    cols = set(df_head.columns)
    shopify_markers = {"Name", "Created at", "Financial Status"}
    if shopify_markers.issubset(cols):
        return "shopify"
    return "generic"


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def validate_schema(df: pd.DataFrame, schema: str) -> ValidationResult:
    """Validate that *df* contains the columns required by *schema*.

    Parameters
    ----------
    schema : str
        One of ``"orders"``, ``"products"``, ``"inventory"``.
    """
    required_map = {
        "orders": GENERIC_ORDER_REQUIRED,
        "products": GENERIC_PRODUCT_REQUIRED,
        "inventory": GENERIC_INVENTORY_REQUIRED,
    }
    required = required_map.get(schema, set())
    present = set(df.columns)
    missing = sorted(required - present)
    warnings: list[str] = []
    if schema == "orders" and "discount" not in present:
        warnings.append("'discount' column missing — discount analysis will be skipped")
    return ValidationResult(valid=len(missing) == 0, missing_columns=missing, warnings=warnings)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _normalise_shopify_orders(df: pd.DataFrame) -> pd.DataFrame:
    rename = {k: v for k, v in SHOPIFY_ORDER_COLUMNS.items() if k in df.columns}
    df = df.rename(columns=rename)
    if "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], utc=True)
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    if "discount" in df.columns:
        df["discount"] = pd.to_numeric(df["discount"], errors="coerce").fillna(0)
    return df


def _normalise_generic_orders(df: pd.DataFrame) -> pd.DataFrame:
    if "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"])
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    if "discount" in df.columns:
        df["discount"] = pd.to_numeric(df["discount"], errors="coerce").fillna(0)
    return df


def load_orders(path: str, fmt: str = "auto") -> pd.DataFrame:
    """Load and normalise an orders CSV.

    Parameters
    ----------
    fmt : str
        ``"shopify"``, ``"generic"``, or ``"auto"`` (detect automatically).
    """
    if fmt == "auto":
        fmt = detect_format(path)
    df = pd.read_csv(path)
    if fmt == "shopify":
        df = _normalise_shopify_orders(df)
    else:
        df = _normalise_generic_orders(df)
    validation = validate_schema(df, "orders")
    if not validation.valid:
        raise ValueError(
            f"Orders CSV missing required columns: {validation.missing_columns}"
        )
    return df


def load_products(path: str) -> pd.DataFrame:
    """Load and normalise a products CSV."""
    df = pd.read_csv(path)
    # Try Shopify mapping first
    shopify_markers = {"Handle", "Title", "Variant Price"}
    if shopify_markers.issubset(set(df.columns)):
        rename = {k: v for k, v in SHOPIFY_PRODUCT_COLUMNS.items() if k in df.columns}
        df = df.rename(columns=rename)
    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
    validation = validate_schema(df, "products")
    if not validation.valid:
        raise ValueError(
            f"Products CSV missing required columns: {validation.missing_columns}"
        )
    return df


def load_inventory(path: str) -> pd.DataFrame:
    """Load and normalise an inventory CSV."""
    df = pd.read_csv(path)
    if "quantity_on_hand" in df.columns:
        df["quantity_on_hand"] = pd.to_numeric(df["quantity_on_hand"], errors="coerce")
    validation = validate_schema(df, "inventory")
    if not validation.valid:
        raise ValueError(
            f"Inventory CSV missing required columns: {validation.missing_columns}"
        )
    return df


# ---------------------------------------------------------------------------
# Shopify Analytics (aggregated) loaders
# ---------------------------------------------------------------------------

# Filename patterns → internal keys (matched case-insensitively against start of filename)
_ANALYTICS_FILE_PATTERNS = {
    "total sales over time": "sales",
    "conversion rate over time": "conversion",
    "total sales by product variant": "products",
    "sessions over time": "sessions",
    "new vs returning customer sales": "customers",
    "gross profit breakdown": "profit",
    "net sales over time": "net_sales",
}


@dataclass
class AnalyticsData:
    """Container for Shopify Analytics aggregated exports."""

    sales: pd.DataFrame | None = None
    conversion: pd.DataFrame | None = None
    products: pd.DataFrame | None = None
    sessions: pd.DataFrame | None = None
    customers: pd.DataFrame | None = None
    profit: pd.DataFrame | None = None
    net_sales: pd.DataFrame | None = None
    loaded_files: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)


def detect_analytics_dir(directory: str) -> bool:
    """Return True if *directory* contains Shopify Analytics CSV exports."""
    p = Path(directory)
    if not p.is_dir():
        return False
    csv_names = {f.name.lower() for f in p.glob("*.csv")}
    # Need at least the sales-over-time file
    return any(
        any(name.startswith(pat) for pat in _ANALYTICS_FILE_PATTERNS)
        for name in csv_names
    )


def _match_analytics_file(filename: str) -> str | None:
    """Return the internal key for a Shopify Analytics filename, or None."""
    lower = filename.lower()
    for pattern, key in _ANALYTICS_FILE_PATTERNS.items():
        if lower.startswith(pattern):
            return key
    return None


def _drop_previous_period_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Drop the comparison / previous-period columns from Shopify Analytics exports."""
    keep = [c for c in df.columns if "previous_period" not in c.lower()]
    return df[keep].copy()


def _normalise_sales_over_time(df: pd.DataFrame) -> pd.DataFrame:
    df = _drop_previous_period_cols(df)
    df["Month"] = pd.to_datetime(df["Month"])
    for col in ["Orders", "Gross sales", "Discounts", "Returns", "Net sales",
                 "Shipping charges", "Duties", "Additional fees", "Taxes", "Total sales"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    # Make Discounts positive for internal use (Shopify exports them as negative)
    if "Discounts" in df.columns:
        df["Discounts"] = df["Discounts"].abs()
    if "Returns" in df.columns:
        df["Returns"] = df["Returns"].abs()
    return df


def _normalise_conversion_over_time(df: pd.DataFrame) -> pd.DataFrame:
    df = _drop_previous_period_cols(df)
    df["Month"] = pd.to_datetime(df["Month"])
    for col in ["Sessions", "Sessions with cart additions",
                 "Sessions that reached checkout", "Sessions that completed checkout"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    if "Conversion rate" in df.columns:
        df["Conversion rate"] = pd.to_numeric(df["Conversion rate"], errors="coerce")
    return df


def _normalise_product_variants(df: pd.DataFrame) -> pd.DataFrame:
    # First row is often a summary row with no product title — drop it
    if len(df) > 1 and pd.isna(df.iloc[0]["Product title"]):
        df = df.iloc[1:].copy()
    for col in ["Net items sold", "Gross sales", "Discounts", "Returns",
                 "Net sales", "Taxes", "Total sales"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    if "Discounts" in df.columns:
        df["Discounts"] = df["Discounts"].abs()
    if "Returns" in df.columns:
        df["Returns"] = df["Returns"].abs()
    return df


def _normalise_sessions_over_time(df: pd.DataFrame) -> pd.DataFrame:
    df = _drop_previous_period_cols(df)
    df["Month"] = pd.to_datetime(df["Month"])
    for col in ["Online store visitors", "Sessions"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df


def _normalise_customer_segments(df: pd.DataFrame) -> pd.DataFrame:
    df = _drop_previous_period_cols(df)
    df["Month"] = pd.to_datetime(df["Month"])
    for col in ["Customers", "Orders", "Total sales"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def _normalise_gross_profit(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _normalise_net_sales(df: pd.DataFrame) -> pd.DataFrame:
    df = _drop_previous_period_cols(df)
    df["Month"] = pd.to_datetime(df["Month"])
    df["Net sales"] = pd.to_numeric(df["Net sales"], errors="coerce").fillna(0)
    return df


_NORMALISERS = {
    "sales": _normalise_sales_over_time,
    "conversion": _normalise_conversion_over_time,
    "products": _normalise_product_variants,
    "sessions": _normalise_sessions_over_time,
    "customers": _normalise_customer_segments,
    "profit": _normalise_gross_profit,
    "net_sales": _normalise_net_sales,
}


def load_shopify_analytics(directory: str) -> AnalyticsData:
    """Load all Shopify Analytics CSV exports from *directory*.

    Returns an ``AnalyticsData`` container with normalised DataFrames.
    Files are matched by filename prefix (case-insensitive).
    """
    p = Path(directory)
    if not p.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")

    result = AnalyticsData()
    matched_keys: set[str] = set()

    for csv_file in sorted(p.glob("*.csv")):
        key = _match_analytics_file(csv_file.name)
        if key is None:
            continue
        df = pd.read_csv(csv_file)
        normaliser = _NORMALISERS.get(key)
        if normaliser:
            df = normaliser(df)
        setattr(result, key, df)
        result.loaded_files.append(csv_file.name)
        matched_keys.add(key)

    # Track missing files
    for key in _ANALYTICS_FILE_PATTERNS.values():
        if key not in matched_keys:
            result.missing_files.append(key)

    if not result.loaded_files:
        raise ValueError(
            f"No Shopify Analytics CSV files found in {directory}. "
            "Expected filenames starting with: "
            + ", ".join(f'"{p}"' for p in _ANALYTICS_FILE_PATTERNS)
        )

    return result
