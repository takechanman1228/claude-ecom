"""Check result types, impact estimation, and action builders."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CheckResult:
    """A single check evaluation."""

    check_id: str
    category: str
    severity: str  # critical, high, medium, low
    result: str  # pass, watch, fail, na
    message: str = ""
    current_value: float | str | None = None
    threshold: float | str | None = None
    recommended_action: str = ""


def _check_specific_impact(c: CheckResult, annual_revenue: float) -> float | None:
    """Compute check-specific revenue impact when current_value is available.

    Returns None if no formula exists for this check or data is missing.
    """
    if c.current_value is None:
        return None
    try:
        val = float(c.current_value)
    except (ValueError, TypeError):
        return None

    formulas: dict[str, tuple[float, object]] = {
        # Discount rate: margin recovery from reducing discounts
        "avg_discount_rate_trend": (0.12, lambda v, rev: rev * max(0, v - 0.12) * 0.5),
    }

    entry = formulas.get(c.check_id)
    if entry is None:
        return None
    _, fn = entry
    result = fn(val, annual_revenue)
    if result is None or result < 0:
        return None
    return result


def estimate_revenue_impact(check_results: list[CheckResult], annual_revenue: float) -> dict:
    """Estimate revenue impact of fixing FAIL/WARNING checks.

    Uses check-specific formulas when available, falling back to
    severity-based heuristics.
    """
    if annual_revenue <= 0:
        return {}

    severity_pct = {
        "critical": 0.03,
        "high": 0.015,
        "medium": 0.005,
        "low": 0.001,
    }

    impacts: dict[str, dict] = {}
    for c in check_results:
        if c.result.lower() in ("pass", "na"):
            continue

        # Try check-specific formula first
        specific = _check_specific_impact(c, annual_revenue)
        if specific is not None:
            est = specific
            confidence = "high"
        else:
            # Fallback: severity-based estimate
            pct = severity_pct.get(c.severity.lower(), 0.005)
            if c.result.lower() == "warning":
                pct *= 0.5
            est = annual_revenue * pct
            confidence = (
                "high" if c.severity.lower() == "critical" else ("medium" if c.severity.lower() == "high" else "low")
            )

        impacts[c.check_id] = {
            "annual_revenue_impact": round(est, 0),
            "confidence": confidence,
            "severity": c.severity,
            "result": c.result,
        }

    return impacts


# ---------------------------------------------------------------------------
# Builders for unified review model
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def build_top_issues(checks: list[CheckResult], annual_revenue: float, max_issues: int = 10) -> list[dict]:
    """Build pre-sorted top issues from non-pass checks.

    Sorted by severity * impact. Each entry contains id, category, severity,
    result, message, and estimated_annual_impact.
    """
    impacts = estimate_revenue_impact(checks, annual_revenue)
    issues = []
    for c in checks:
        if c.result.lower() in ("pass", "na"):
            continue
        imp = impacts.get(c.check_id, {})
        issues.append(
            {
                "id": c.check_id,
                "category": c.category,
                "severity": c.severity,
                "result": c.result,
                "message": c.message,
                "estimated_annual_impact": imp.get("annual_revenue_impact", 0),
            }
        )
    issues.sort(
        key=lambda x: (
            _SEVERITY_ORDER.get(x["severity"].lower(), 9),
            x["result"].lower() != "fail",
            -x["estimated_annual_impact"],
        )
    )
    return issues[:max_issues]


_SEVERITY_TIMELINE = {
    "critical": "this_week",
    "high": "this_month",
    "medium": "this_quarter",
    "low": "this_quarter",
}

# Action suggestion templates keyed by check_id
_ACTION_TEMPLATES: dict[str, str] = {
    "monthly_revenue_trend": "Audit acquisition channels for spend or efficiency changes",
    "aov_trend": "Analyze category mix shift and review promotional calendar",
    "order_count_trend": "Review traffic sources and conversion funnel for volume drops",
    "repeat_customer_revenue_share": "Launch tiered loyalty program and post-purchase email automation",
    "revenue_concentration_top10": "Diversify customer acquisition channels to reduce concentration",
    "avg_discount_rate_trend": "Cap discount depth and shift to value-added incentives",
    "daily_revenue_volatility": "Shift promotional budget from flash sales to always-on acquisition",
    "large_order_dependency": "Analyze large-order dependency and diversify revenue sources",
    "discounted_order_ratio": "Restrict promo code distribution to targeted segments",
    "discount_depth_trend": "Freeze discount escalation and introduce non-discount incentives",
    "category_margin_variance": "Review pricing for negative-margin categories",
    "free_shipping_threshold_effectiveness": "Adjust free-shipping threshold to 1.2x median AOV",
    "repeat_purchase_rate": "Deploy post-purchase engagement sequence to improve repeat purchase conversion",
    "champions_loyal_share": "Build VIP program for top customers to grow Champions segment",
    "at_risk_segment_share": "Launch win-back campaigns for At-Risk customer segment",
    "lost_segment_share": "Implement automated reactivation flows for Lost customers",
    "days_to_second_purchase": "Shorten second-purchase window with replenishment reminders",
    "top20_revenue_concentration": "Create discovery merchandising for mid-tier products",
    "converting_sku_rate": "Conduct SKU rationalization for non-converting products",
    "multi_item_order_rate": "Introduce product bundles to increase multi-item orders",
    "cross_sell_pair_lift": "Build cross-sell recommendations from high-lift product pairs",
    "lifecycle_stage_distribution": "Accelerate new product launches to replace declining SKUs",
    "price_tier_distribution": "Expand price tier coverage with entry-level or premium options",
}


def build_action_candidates(top_issues: list[dict], max_actions: int = 10) -> list[dict]:
    """Build action candidates from top issues with severity-based timelines.

    Each entry contains action, source_check, severity, estimated_annual_impact,
    and timeline.
    """
    actions = []
    seen_checks: set[str] = set()
    for issue in top_issues:
        if len(actions) >= max_actions:
            break
        cid = issue["id"]
        if cid in seen_checks:
            continue
        seen_checks.add(cid)
        action_text = _ACTION_TEMPLATES.get(cid, f"Address {issue['message']}")
        actions.append(
            {
                "action": action_text,
                "source_check": cid,
                "severity": issue["severity"],
                "estimated_annual_impact": issue["estimated_annual_impact"],
                "timeline": _SEVERITY_TIMELINE.get(issue["severity"].lower(), "this_quarter"),
            }
        )
    return actions
