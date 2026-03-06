"""Report generation (review.json) and finding clusters."""

from __future__ import annotations

import json as json_mod
from pathlib import Path

from .checks import CheckResult

# Severity ordering for cluster sorting
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Finding cluster definitions: name → (check_ids, hypothesis_template, approach)
# 4 clusters: B (Discount), C (Assortment), F (Customer), G (Concentration)
_FINDING_CLUSTERS = [
    {
        "name": "Discount Dependency",
        "checks": {"avg_discount_rate_trend", "discounted_order_ratio", "discount_depth_trend", "free_shipping_threshold_effectiveness", "monthly_revenue_trend"},
        "hypothesis": (
            "{n} discount/pricing checks flagged, indicating the store "
            "may be conditioning customers to wait for sales. "
            "{worst} is the key concern."
        ),
        "approach": ("Shift from blanket discounts to value-added incentives; cap discount depth and frequency."),
    },
    {
        "name": "Assortment & Merchandising Misfit",
        "checks": {"top20_revenue_concentration", "converting_sku_rate", "multi_item_order_rate", "cross_sell_pair_lift", "lifecycle_stage_distribution", "price_tier_distribution", "category_margin_variance"},
        "hypothesis": (
            "{n} assortment/merchandising checks flagged, suggesting the catalog "
            "is misaligned to demand and value positioning. "
            "{worst} is most critical."
        ),
        "approach": (
            "Do SKU rationalization with clear roles (hero/core/seasonal); "
            "improve merchandising and align price ladders."
        ),
    },
    {
        "name": "Customer & LTV Engine Weakness",
        "checks": {"repeat_purchase_rate", "champions_loyal_share", "at_risk_segment_share", "lost_segment_share", "days_to_second_purchase", "repeat_customer_revenue_share", "large_order_dependency"},
        "hypothesis": (
            "{n} customer and value checks flagged — the store is failing to "
            "convert first-time buyers into repeat buyers at profitable frequency. "
            "{worst} is most severe."
        ),
        "approach": (
            "Build a retention engine: post-purchase onboarding, replenishment triggers, "
            "lifecycle marketing, and loyalty economics."
        ),
    },
    {
        "name": "Revenue Concentration Risk",
        "checks": {"order_count_trend", "revenue_concentration_top10", "top20_revenue_concentration"},
        "hypothesis": (
            "{n} concentration-related checks show risk — revenue depends on "
            "a narrow set of customers or SKUs. "
            "{worst} is the primary concern."
        ),
        "approach": ("Diversify customer acquisition channels; expand product assortment into adjacent categories."),
    },
]


def _get_version() -> str:
    """Get package version, with fallback to pyproject.toml."""
    try:
        from importlib.metadata import version

        return version("claude-ecom")
    except Exception:
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib  # type: ignore[no-redef]
        try:
            pyproject = Path(__file__).parent.parent / "pyproject.toml"
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            return data["project"]["version"]
        except Exception:
            return "0.1.0"


def _build_clusters(check_results: list[CheckResult]) -> list[dict]:
    """Build activated finding clusters from check results."""
    non_pass = {c.check_id: c for c in check_results if c.result.lower() not in ("pass", "na")}
    clusters = []
    for cluster in _FINDING_CLUSTERS:
        matched = [non_pass[cid] for cid in cluster["checks"] if cid in non_pass]
        if len(matched) < 2:
            continue
        matched.sort(
            key=lambda c: (
                _SEVERITY_ORDER.get(c.severity.lower(), 9),
                c.result.lower() != "fail",
            )
        )
        worst = matched[0]
        clusters.append(
            {
                "name": cluster["name"],
                "count": len(matched),
                "related_issues": ", ".join(c.message for c in matched),
                "hypothesis": cluster["hypothesis"].format(n=len(matched), worst=worst.message),
                "approach": cluster["approach"],
            }
        )
    return clusters


def _sanitize_for_json(obj):
    """Replace NaN/Infinity with None for JSON serialization."""
    import math

    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


def generate_review_json(
    review_data: dict,
    output_dir: str = ".",
) -> str:
    """Write review.json from review engine output.

    Returns the output file path.
    """
    sanitized = _sanitize_for_json(review_data)
    out = Path(output_dir) / "review.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json_mod.dumps(sanitized, indent=2, default=str), encoding="utf-8")
    return str(out)
