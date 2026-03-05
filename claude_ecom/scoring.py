"""Health score calculation and grading.

Scoring system:
- 7 categories weighted to 100%: Revenue 25%, Conversion 20%, Product 20%,
  Inventory 10%, Retention 15%, Pricing 10%, Site 10%.
- Only categories present are included; weights are renormalised automatically.
- Severity multipliers: Critical 5.0, High 3.0, Medium 1.5, Low 0.5.
- Check results: PASS (1.0), WARNING (0.5), FAIL (0.0).
- Grades: A (90-100), B (75-89), C (60-74), D (40-59), F (<40).
"""

from __future__ import annotations

from dataclasses import dataclass, field

CATEGORY_WEIGHTS = {
    "revenue": 0.25,
    "conversion": 0.20,
    "product": 0.20,
    "inventory": 0.10,
    "retention": 0.15,
    "pricing": 0.10,
    "site": 0.10,
}

SEVERITY_MULTIPLIERS = {
    "critical": 5.0,
    "high": 3.0,
    "medium": 1.5,
    "low": 0.5,
}

RESULT_SCORES = {
    "pass": 1.0,
    "warning": 0.5,
    "fail": 0.0,
    "na": None,
}

GRADE_THRESHOLDS = [
    (90, "A"),
    (75, "B"),
    (60, "C"),
    (40, "D"),
    (0, "F"),
]


@dataclass
class CheckResult:
    """A single check evaluation."""

    check_id: str
    category: str
    severity: str  # critical, high, medium, low
    result: str  # pass, warning, fail
    message: str = ""
    current_value: float | str | None = None
    threshold: float | str | None = None
    recommended_action: str = ""


@dataclass
class CategoryScore:
    """Score for one category."""

    category: str
    score: float  # 0-100
    grade: str
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
    overall_grade: str
    category_scores: dict[str, CategoryScore]
    check_results: list[CheckResult]
    total_checks: int
    total_passed: int
    total_warnings: int
    total_failed: int
    total_na: int = 0


def assign_grade(score: float) -> str:
    """Map a 0-100 score to a letter grade."""
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def score_category(checks: list[CheckResult]) -> CategoryScore:
    """Score a single category from its check results.

    Formula: score = Σ(result_score × severity_mult) / Σ(severity_mult) × 100
    """
    if not checks:
        return CategoryScore(
            category="",
            score=100.0,
            grade="A",
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
        elif c.result.lower() == "warning":
            warnings += 1
        else:
            failed += 1
            if c.severity.lower() == "critical":
                critical_fails.append(c.check_id)

    score = (weighted_sum / weight_total * 100) if weight_total else 100.0

    return CategoryScore(
        category=category,
        score=round(score, 1),
        grade=assign_grade(score),
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
    overall 0-100 score with grade.
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
        overall_grade=assign_grade(overall),
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
        # CVR gap vs median 2.5%: lost revenue from lower conversion
        "CV01": (0.025, lambda v, rev: rev * (0.025 - v) / v if v > 0 else None),
        # Cart abandonment: each 1% improvement ≈ proportional revenue gain
        "CV05": (0.60, lambda v, rev: rev * 0.01 * max(0, v - 0.60) / 0.60),
        # Checkout abandonment: similar
        "CV06": (0.30, lambda v, rev: rev * 0.01 * max(0, v - 0.30) / 0.30),
        # Return rate: cost savings from reducing returns
        "R10": (0.08, lambda v, rev: rev * max(0, v - 0.08)),
        # Discount rate: margin recovery from reducing discounts
        "R08": (0.12, lambda v, rev: rev * max(0, v - 0.12) * 0.5),
        "PR01": (0.12, lambda v, rev: rev * max(0, v - 0.12) * 0.5),
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
