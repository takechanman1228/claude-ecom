"""CSV data loading and validation for ecommerce datasets."""

from __future__ import annotations

from dataclasses import dataclass, field

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

# ---------------------------------------------------------------------------
# Column alias auto-mapping for arbitrary CSV formats
# ---------------------------------------------------------------------------

_ORDER_COLUMN_ALIASES: dict[str, list[str]] = {
    "order_id": [
        "order_id",
        "order id",
        "order_number",
        "order number",
        "invoice",
        "invoice number",
        "invoice/item number",
        "transaction_id",
        "transaction id",
    ],
    "order_date": [
        "order_date",
        "order date",
        "date",
        "created_at",
        "created at",
        "purchase_date",
        "purchase date",
        "transaction_date",
        "transaction date",
        "day",
    ],
    "amount": [
        "amount",
        "total",
        "sale (dollars)",
        "sale_amount",
        "sale amount",
        "total_amount",
        "total amount",
        "revenue",
        "grand_total",
        "grand total",
        "total sales",
        "net sales",
    ],
    "customer_id": [
        "customer_id",
        "customer id",
        "email",
        "customer_email",
        "buyer_id",
        "store number",
        "store_number",
        "store name",
        "user_id",
        "client_id",
    ],
}

_ORDER_COLUMN_OPTIONAL_ALIASES: dict[str, list[str]] = {
    "product_name": [
        "product_name",
        "product name",
        "item description",
        "item_description",
        "product",
        "item",
        "lineitem name",
        "product title",
    ],
    "quantity": [
        "quantity",
        "bottles sold",
        "qty",
        "units",
        "items",
        "lineitem quantity",
    ],
    "sku": [
        "sku",
        "item number",
        "item_number",
        "variant_id",
        "lineitem sku",
    ],
    "discount": [
        "discount",
        "discount_amount",
        "discount amount",
        "discounts",
    ],
    "category": [
        "category",
        "category name",
        "category_name",
        "product_type",
        "product type",
    ],
    "city": [
        "city",
        "billing city",
        "shipping city",
    ],
}


def _auto_map_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    """Try to auto-map columns to canonical names using aliases.

    Returns the renamed DataFrame and a dict of applied mappings.
    """
    col_lower_map = {c.lower().strip(): c for c in df.columns}
    rename_map: dict[str, str] = {}

    for canonical, aliases in {**_ORDER_COLUMN_ALIASES, **_ORDER_COLUMN_OPTIONAL_ALIASES}.items():
        if canonical in df.columns:
            continue  # already present
        for alias in aliases:
            if alias in col_lower_map:
                rename_map[col_lower_map[alias]] = canonical
                break

    if rename_map:
        df = df.rename(columns=rename_map)
    return df, rename_map


def _token_similarity(a: str, b: str) -> float:
    """Jaccard similarity on word tokens of two strings."""
    tokens_a = set(a.lower().replace("_", " ").split())
    tokens_b = set(b.lower().replace("_", " ").split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def _infer_column_type(series: pd.Series) -> str:
    """Detect column type from sample values: date, currency, id, or unknown."""
    sample = series.dropna().head(20)
    if sample.empty:
        return "unknown"
    # Date-like
    try:
        pd.to_datetime(sample)
        return "date"
    except (ValueError, TypeError):
        pass
    # Currency-like (numeric with possible $ , .)
    str_vals = sample.astype(str)
    numeric_count = (
        str_vals.str.replace(r"[$,\s]", "", regex=True)
        .apply(lambda v: v.replace(".", "", 1).replace("-", "", 1).isdigit())
        .sum()
    )
    if numeric_count / len(sample) > 0.8:
        return "currency"
    # ID-like (mostly unique values)
    if series.nunique() / max(len(series), 1) > 0.8:
        return "id"
    return "unknown"


def _fuzzy_map_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    """Tier 2: Token + value-type inference for unmapped required columns.

    Only maps columns that are still missing after exact alias matching.
    """
    all_aliases = {**_ORDER_COLUMN_ALIASES, **_ORDER_COLUMN_OPTIONAL_ALIASES}
    rename_map: dict[str, str] = {}
    used_cols: set[str] = set()

    # Type hints for canonical columns
    expected_types = {
        "order_id": "id",
        "order_date": "date",
        "amount": "currency",
        "customer_id": "id",
        "discount": "currency",
        "quantity": "currency",
    }

    for canonical, aliases in all_aliases.items():
        if canonical in df.columns:
            continue
        best_score = 0.0
        best_col = None
        # All alias tokens for similarity
        alias_tokens = " ".join(aliases)
        for col in df.columns:
            if col in used_cols or col in rename_map:
                continue
            sim = max(_token_similarity(col, alias_tokens), _token_similarity(col, canonical))
            # Boost if value type matches
            if canonical in expected_types:
                col_type = _infer_column_type(df[col])
                if col_type == expected_types[canonical]:
                    sim += 0.2
            if sim > best_score:
                best_score = sim
                best_col = col
        if best_col and best_score >= 0.5:
            rename_map[best_col] = canonical
            used_cols.add(best_col)

    if rename_map:
        df = df.rename(columns=rename_map)
    return df, rename_map


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
    # Tier 1: Auto-map column names from common aliases
    df, mapped = _auto_map_columns(df)
    if mapped:
        import logging

        logging.getLogger(__name__).info("Auto-mapped columns: %s", mapped)
    # Tier 2: Fuzzy matching for still-missing required columns
    missing = GENERIC_ORDER_REQUIRED - set(df.columns)
    if missing:
        df, fuzzy_mapped = _fuzzy_map_columns(df)
        if fuzzy_mapped:
            import logging

            logging.getLogger(__name__).info("Fuzzy-mapped columns: %s", fuzzy_mapped)
            mapped.update(fuzzy_mapped)
    if "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"])
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    if "discount" in df.columns:
        df["discount"] = pd.to_numeric(df["discount"], errors="coerce").fillna(0)
    return df


def load_orders(path: str, fmt: str = "auto", nrows: int | None = None) -> pd.DataFrame:
    """Load and normalise an orders CSV.

    Parameters
    ----------
    fmt : str
        ``"shopify"``, ``"generic"``, or ``"auto"`` (detect automatically).
    nrows : int | None
        If set, only read this many rows (useful for large files).
    """
    if fmt == "auto":
        fmt = detect_format(path)
    df = pd.read_csv(path, nrows=nrows, low_memory=False)
    if fmt == "shopify":
        df = _normalise_shopify_orders(df)
    else:
        df = _normalise_generic_orders(df)
    validation = validate_schema(df, "orders")
    if not validation.valid:
        raise ValueError(f"Orders CSV missing required columns: {validation.missing_columns}")
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
        raise ValueError(f"Products CSV missing required columns: {validation.missing_columns}")
    return df


def load_inventory(path: str) -> pd.DataFrame:
    """Load and normalise an inventory CSV."""
    df = pd.read_csv(path)
    if "quantity_on_hand" in df.columns:
        df["quantity_on_hand"] = pd.to_numeric(df["quantity_on_hand"], errors="coerce")
    validation = validate_schema(df, "inventory")
    if not validation.valid:
        raise ValueError(f"Inventory CSV missing required columns: {validation.missing_columns}")
    return df
