"""Health score calculation and grading.

Scoring system:
- 3 categories weighted to 100%: Revenue 40%, Customer 30%, Product 30%.
- Only categories present are included; weights are renormalised automatically.
- Severity multipliers: Critical 5.0, High 3.0, Medium 1.5, Low 0.5.
- Check results: PASS (1.0), WATCH (0.5), WARNING (0.5), FAIL (0.0).
- Health levels: strong (75-100), needs_attention (50-74), weak (<50).
"""

from __future__ import annotations

from dataclasses import dataclass, field

CATEGORY_WEIGHTS = {
    "revenue": 0.40,
    "customer": 0.30,
    "product": 0.30,
}

SEVERITY_MULTIPLIERS = {
    "critical": 5.0,
    "high": 3.0,
    "medium": 1.5,
    "low": 0.5,
}

RESULT_SCORES = {
    "pass": 1.0,
    "watch": 0.5,
    "warning": 0.5,
    "fail": 0.0,
    "na": None,
}

HEALTH_LEVELS = [
    (75, "strong"),
    (50, "needs_attention"),
    (0, "weak"),
]


@dataclass
class CheckResult:
    """A single check evaluation."""

    check_id: str
    category: str
    severity: str  # critical, high, medium, low
    result: str  # pass, watch, warning, fail, na
    message: str = ""
    current_value: float | str | None = None
    threshold: float | str | None = None
    recommended_action: str = ""


@dataclass
class CategoryScore:
    """Score for one category."""

    category: str
    score: float  # 0-100
    level: str  # strong, needs_attention, weak
    total_checks: int
    passed: int
    warnings: int
    failed: int
    na: int = 0
    critical_fails: list[str] = field(default_factory=list)


@dataclass
class HealthScore:
    """Overall health score."""

    overall_score: float
    category_scores: dict[str, CategoryScore]
    check_results: list[CheckResult]
    total_checks: int
    total_passed: int
    total_warnings: int
    total_failed: int
    total_na: int = 0


def assign_level(score: float) -> str:
    """Map a 0-100 score to a health level (strong/needs_attention/weak)."""
    for threshold, level in HEALTH_LEVELS:
        if score >= threshold:
            return level
    return "weak"


def score_category(checks: list[CheckResult]) -> CategoryScore:
    """Score a single category from its check results.

    Formula: score = Σ(result_score × severity_mult) / Σ(severity_mult) × 100
    """
    if not checks:
        return CategoryScore(
            category="",
            score=100.0,
            level="strong",
            total_checks=0,
            passed=0,
            warnings=0,
            failed=0,
        )

    category = checks[0].category
    weighted_sum = 0.0
    weight_total = 0.0
    passed = warnings = failed = na = 0
    critical_fails: list[str] = []

    for c in checks:
        if c.result.lower() == "na":
            na += 1
            continue
        mult = SEVERITY_MULTIPLIERS.get(c.severity.lower(), 1.0)
        pts = RESULT_SCORES.get(c.result.lower(), 0.0)
        weighted_sum += pts * mult
        weight_total += mult
        if c.result.lower() == "pass":
            passed += 1
        elif c.result.lower() in ("warning", "watch"):
            warnings += 1
        else:
            failed += 1
            if c.severity.lower() == "critical":
                critical_fails.append(c.check_id)

    score = (weighted_sum / weight_total * 100) if weight_total else 100.0

    return CategoryScore(
        category=category,
        score=round(score, 1),
        level=assign_level(score),
        total_checks=len(checks),
        passed=passed,
        warnings=warnings,
        failed=failed,
        na=na,
        critical_fails=critical_fails,
    )


def score_checks(check_results: list[CheckResult]) -> HealthScore:
    """Compute the overall health score from all check results.

    Aggregates by category, applies category weights, and produces an
    overall 0-100 score.
    """
    # Group by category
    by_category: dict[str, list[CheckResult]] = {}
    for c in check_results:
        by_category.setdefault(c.category, []).append(c)

    category_scores: dict[str, CategoryScore] = {}
    for cat, checks in by_category.items():
        category_scores[cat] = score_category(checks)

    # Weighted aggregate
    overall = aggregate_score(
        {cat: cs.score for cat, cs in category_scores.items()},
        CATEGORY_WEIGHTS,
    )

    total_passed = sum(cs.passed for cs in category_scores.values())
    total_warnings = sum(cs.warnings for cs in category_scores.values())
    total_failed = sum(cs.failed for cs in category_scores.values())
    total_na = sum(cs.na for cs in category_scores.values())

    return HealthScore(
        overall_score=round(overall, 1),
        category_scores=category_scores,
        check_results=check_results,
        total_checks=len(check_results),
        total_passed=total_passed,
        total_warnings=total_warnings,
        total_failed=total_failed,
        total_na=total_na,
    )


def aggregate_score(category_scores: dict[str, float], weights: dict[str, float]) -> float:
    """Compute weighted average of category scores.

    Only categories present in both dicts are included; weights are renormalised.
    """
    total_weight = 0.0
    weighted_sum = 0.0
    for cat, score in category_scores.items():
        w = weights.get(cat, 0)
        weighted_sum += score * w
        total_weight += w
    return weighted_sum / total_weight if total_weight else 0.0


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
        "R08": (0.12, lambda v, rev: rev * max(0, v - 0.12) * 0.5),
        # Gross margin gap
        "R14": (0.45, lambda v, rev: rev * max(0, 0.45 - v) if v < 0.45 else None),
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


def build_top_issues(
    checks: list[CheckResult], annual_revenue: float, max_issues: int = 10
) -> list[dict]:
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
        issues.append({
            "id": c.check_id,
            "category": c.category,
            "severity": c.severity,
            "result": c.result,
            "message": c.message,
            "estimated_annual_impact": imp.get("annual_revenue_impact", 0),
        })
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
    "R01": "Audit acquisition channels for spend or efficiency changes",
    "R03": "Analyze category mix shift and review promotional calendar",
    "R04": "Review traffic sources and conversion funnel for volume drops",
    "R05": "Launch tiered loyalty program and post-purchase email automation",
    "R07": "Diversify customer acquisition channels to reduce concentration",
    "R08": "Cap discount depth and shift to value-added incentives",
    "R13": "Shift promotional budget from flash sales to always-on acquisition",
    "R14": "Analyze large-order dependency and diversify revenue sources",
    "PR02": "Restrict promo code distribution to targeted segments",
    "PR03": "Freeze discount escalation and introduce non-discount incentives",
    "PR07": "Review pricing for negative-margin categories",
    "PR08": "Adjust free-shipping threshold to 1.2x median AOV",
    "C01": "Deploy post-purchase engagement sequence to improve F2 conversion",
    "C08": "Build VIP program for top customers to grow Champions segment",
    "C09": "Launch win-back campaigns for At-Risk customer segment",
    "C10": "Implement automated reactivation flows for Lost customers",
    "C11": "Shorten second-purchase window with replenishment reminders",
    "P01": "Create discovery merchandising for mid-tier products",
    "P05": "Conduct SKU rationalization for non-converting products",
    "P06": "Introduce product bundles to increase multi-item orders",
    "P07": "Build cross-sell recommendations from high-lift product pairs",
    "P10": "Accelerate new product launches to replace declining SKUs",
    "P19": "Expand price tier coverage with entry-level or premium options",
}


def build_action_candidates(
    top_issues: list[dict], max_actions: int = 10
) -> list[dict]:
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
        actions.append({
            "action": action_text,
            "source_check": cid,
            "severity": issue["severity"],
            "estimated_annual_impact": issue["estimated_annual_impact"],
            "timeline": _SEVERITY_TIMELINE.get(issue["severity"].lower(), "this_quarter"),
        })
    return actions
