"""Markdown report generation using Jinja2 templates."""

from __future__ import annotations

import json as json_mod
from datetime import datetime
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from .scoring import CheckResult, HealthScore, estimate_revenue_impact

TEMPLATE_DIR = Path(__file__).parent / "templates"

# Severity ordering for top-issue selection
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Benchmark definitions: check_id → (metric_label, median, top_quartile, format_fn)
_BENCHMARK_DEFS: dict[str, tuple[str, float, float, str]] = {
    "CV01": ("Conversion Rate", 0.025, 0.045, ".2%"),
    "CV05": ("Cart Abandonment", 0.70, 0.60, ".1%"),
    "CV06": ("Checkout Abandonment", 0.30, 0.20, ".1%"),
    "R05": ("Repeat Revenue Share", 0.30, 0.40, ".1%"),
    "R08": ("Avg Discount Rate", 0.12, 0.05, ".1%"),
    "R10": ("Return Rate", 0.08, 0.03, ".1%"),
    "R14": ("Gross Margin", 0.45, 0.65, ".1%"),
    "C01": ("F2 Conversion Rate", 0.27, 0.40, ".1%"),
}


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
            return "1.0.0"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        keep_trailing_newline=True,
    )


def _top_issue(check_results: list[CheckResult]) -> str:
    """Return the most severe non-pass issue, or 'All checks passed'."""
    non_pass = [c for c in check_results if c.result.lower() not in ("pass", "na")]
    if not non_pass:
        return "All checks passed"
    non_pass.sort(
        key=lambda c: (
            _SEVERITY_ORDER.get(c.severity.lower(), 9),
            c.result.lower() != "fail",
        )
    )
    return non_pass[0].message


# Finding cluster definitions: name → (check_ids, hypothesis_template, approach)
_FINDING_CLUSTERS = [
    {
        "name": "Purchase Funnel Issues",
        "checks": {"CV01", "CV03", "CV04", "CV05", "CV06", "CV10", "CV11"},
        "hypothesis": (
            "{n} funnel-related checks flagged warnings, suggesting structural "
            "UX issues in the browse-to-purchase path. {worst} is the most critical."
        ),
        "approach": ("Audit checkout UX end-to-end; prioritise reducing friction at the worst drop-off step."),
    },
    {
        "name": "Discount Dependency",
        "checks": {"R08", "PR01", "PR02", "PR03", "PR09"},
        "hypothesis": (
            "{n} discount/pricing checks show warnings, indicating the store "
            "may be conditioning customers to wait for sales. "
            "{worst} is the key concern."
        ),
        "approach": ("Shift from blanket discounts to value-added incentives; cap discount depth and frequency."),
    },
    {
        "name": "Retention & Loyalty Erosion",
        "checks": {"R05", "C01", "C05", "C08", "C09", "C10", "C11", "C12"},
        "hypothesis": (
            "{n} retention-related checks flagged issues — the 'leaky bucket' "
            "pattern where acquisition masks failing repeat purchase economics. "
            "{worst} is most severe."
        ),
        "approach": (
            "Implement post-purchase engagement flows; build tiered loyalty "
            "program; run win-back campaigns for At-Risk segment."
        ),
    },
    {
        "name": "Catalog & Inventory Health",
        "checks": {"P05", "P09", "P10", "O03", "O05", "O06", "O10"},
        "hypothesis": (
            "{n} product/inventory checks flagged, suggesting non-converting "
            "SKUs are tying up capital. {worst} needs immediate attention."
        ),
        "approach": (
            "Rationalise long-tail SKUs; implement markdown cadence for deadstock; improve demand forecasting."
        ),
    },
    {
        "name": "Revenue Concentration Risk",
        "checks": {"R07", "R13", "R14", "P01", "P19"},
        "hypothesis": (
            "{n} concentration-related checks show risk — over-reliance on "
            "few customers, products, or price tiers. "
            "{worst} is the primary concern."
        ),
        "approach": ("Diversify customer acquisition channels; expand product assortment into adjacent categories."),
    },
]


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
                "check_ids": ", ".join(c.check_id for c in matched),
                "hypothesis": cluster["hypothesis"].format(n=len(matched), worst=f"[{worst.check_id}] {worst.message}"),
                "approach": cluster["approach"],
            }
        )
    return clusters


def _build_benchmarks(check_results: list[CheckResult]) -> list[dict]:
    """Build benchmark comparison rows from check results."""
    benchmarks = []
    checks_by_id = {c.check_id: c for c in check_results}
    # Checks where lower is better (invert comparison)
    lower_is_better = {"CV05", "CV06", "R08", "R10"}

    for check_id, (metric, median, top_q, fmt) in _BENCHMARK_DEFS.items():
        c = checks_by_id.get(check_id)
        if c is None or c.current_value is None or c.result.lower() == "na":
            continue
        try:
            val = float(c.current_value)
        except (ValueError, TypeError):
            continue

        actual_str = f"{val:{fmt}}"
        median_str = f"{median:{fmt}}"
        top_q_str = f"{top_q:{fmt}}"

        if check_id in lower_is_better:
            if val <= top_q:
                status = "Above Top Quartile"
            elif val <= median:
                status = "Above Median"
            else:
                status = "Below Median"
        else:
            if val >= top_q:
                status = "Above Top Quartile"
            elif val >= median:
                status = "Above Median"
            else:
                status = "Below Median"

        benchmarks.append(
            {
                "metric": metric,
                "actual": actual_str,
                "median": median_str,
                "top_q": top_q_str,
                "status": status,
            }
        )
    return benchmarks


def _build_actions(check_results: list[CheckResult], annual_revenue: float) -> dict[str, list]:
    """Build severity-grouped action items from check results."""
    impacts = estimate_revenue_impact(check_results, annual_revenue)
    actions: dict[str, list] = {"critical": [], "high": [], "medium": [], "low": []}
    for c in check_results:
        if c.result.lower() in ("pass", "na"):
            continue
        sev = c.severity.lower()
        imp = impacts.get(c.check_id, {})
        actions.setdefault(sev, []).append(
            {
                "check_id": c.check_id,
                "message": c.message,
                "result": c.result,
                "impact": imp.get("annual_revenue_impact", 0),
            }
        )
    return actions


def _build_quick_wins(check_results: list[CheckResult], annual_revenue: float) -> list[dict]:
    """Build quick win items (critical + high severity non-pass checks)."""
    impacts = estimate_revenue_impact(check_results, annual_revenue)
    wins = []
    for c in check_results:
        if c.result.lower() in ("pass", "na"):
            continue
        if c.severity.lower() not in ("critical", "high"):
            continue
        imp = impacts.get(c.check_id, {})
        wins.append(
            {
                "check_id": c.check_id,
                "severity": c.severity,
                "message": c.message,
                "impact": imp.get("annual_revenue_impact", 0),
            }
        )
    wins.sort(key=lambda w: w["impact"], reverse=True)
    return wins


def _build_data_coverage(health: HealthScore) -> dict:
    """Build data coverage summary from health score."""
    na_checks = [c for c in health.check_results if c.result.lower() == "na"]
    return {
        "total_checks": health.total_checks,
        "ran": health.total_checks - health.total_na,
        "na": health.total_na,
        "na_checks": [{"check_id": c.check_id, "message": c.message} for c in na_checks],
    }


def generate_audit_report(
    health: HealthScore,
    annual_revenue: float,
    data_start: str = "",
    data_end: str = "",
    output_dir: str = ".",
    business_model: str = "",
) -> str:
    """Render AUDIT-REPORT.md with action plan, quick wins, and optional site audit sections."""
    env = _env()
    tpl = env.get_template("audit_report.md.j2")
    impacts = estimate_revenue_impact(health.check_results, annual_revenue)
    total_impact = sum(v["annual_revenue_impact"] for v in impacts.values())

    top_issue = _top_issue(health.check_results)
    benchmarks = _build_benchmarks(health.check_results)
    clusters = _build_clusters(health.check_results)
    actions = _build_actions(health.check_results, annual_revenue)
    quick_wins = _build_quick_wins(health.check_results, annual_revenue)
    quick_wins_total_impact = f"{sum(w['impact'] for w in quick_wins):,.0f}"
    data_coverage = _build_data_coverage(health)

    # Category score bar chart (ASCII)
    cat_chart = ascii_bar_chart(
        {cat.capitalize(): cs.score for cat, cs in health.category_scores.items()},
        max_width=30,
    )

    content = tpl.render(
        date=datetime.now().strftime("%Y-%m-%d"),
        data_start=data_start,
        data_end=data_end,
        score=health.overall_score,
        grade=health.overall_grade,
        top_issue=top_issue,
        total_impact=f"{total_impact:,.0f}",
        category_scores=health.category_scores,
        check_results=health.check_results,
        version=_get_version(),
        business_model=business_model,
        benchmarks=benchmarks,
        clusters=clusters,
        cat_chart=cat_chart,
        actions=actions,
        quick_wins=quick_wins,
        quick_wins_total_impact=quick_wins_total_impact,
        data_coverage=data_coverage,
    )
    out = Path(output_dir) / "AUDIT-REPORT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return str(out)


def generate_executive_summary(
    health: HealthScore,
    annual_revenue: float,
    output_dir: str = ".",
    business_model: str = "",
) -> str:
    """Render executive-summary.md — a one-page stakeholder summary."""
    env = _env()
    tpl = env.get_template("executive_summary.md.j2")
    impacts = estimate_revenue_impact(health.check_results, annual_revenue)
    total_impact = sum(v["annual_revenue_impact"] for v in impacts.values())

    top_issue = _top_issue(health.check_results)
    clusters = _build_clusters(health.check_results)
    quick_wins = _build_quick_wins(health.check_results, annual_revenue)

    cat_chart = ascii_bar_chart(
        {cat.capitalize(): cs.score for cat, cs in health.category_scores.items()},
        max_width=30,
    )

    data_coverage = _build_data_coverage(health)

    content = tpl.render(
        date=datetime.now().strftime("%Y-%m-%d"),
        score=health.overall_score,
        grade=health.overall_grade,
        top_issue=top_issue,
        total_impact=f"{total_impact:,.0f}",
        category_scores=health.category_scores,
        version=_get_version(),
        business_model=business_model,
        clusters=clusters,
        quick_wins=quick_wins,
        cat_chart=cat_chart,
        data_coverage=data_coverage,
    )
    out = Path(output_dir) / "executive-summary.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return str(out)


def generate_scores_json(
    health: HealthScore,
    output_dir: str = ".",
    business_model: str = "",
) -> str:
    """Write machine-readable scores.json."""
    data = {
        "version": _get_version(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "business_model": business_model,
        "overall_score": health.overall_score,
        "overall_grade": health.overall_grade,
        "categories": {
            cat: {
                "score": cs.score,
                "grade": cs.grade,
                "passed": cs.passed,
                "warnings": cs.warnings,
                "failed": cs.failed,
                "na": cs.na,
            }
            for cat, cs in health.category_scores.items()
        },
        "checks": [
            {
                "check_id": c.check_id,
                "category": c.category,
                "severity": c.severity,
                "result": c.result,
                "message": c.message,
                "current_value": c.current_value,
                "threshold": c.threshold,
            }
            for c in health.check_results
        ],
    }
    out = Path(output_dir) / "scores.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json_mod.dumps(data, indent=2, default=str), encoding="utf-8")
    return str(out)


def ascii_bar_chart(data: dict, title: str = "", max_width: int = 40) -> str:
    """Render a simple ASCII horizontal bar chart."""
    if not data:
        return ""
    max_val = max(data.values())
    lines = [title] if title else []
    for label, value in data.items():
        bar_len = int(value / max_val * max_width) if max_val else 0
        bar = "\u2588" * bar_len
        lines.append(f"{str(label):>10} {bar} {value:,.0f}")
    return "\n".join(lines)


def generate_review(
    review_data: dict,
    cadence: str,
    output_dir: str | Path = ".",
) -> str:
    """Render a business review one-pager (MBR / QBR / ABR).

    Uses cadence-specific template. Writes BUSINESS-REVIEW-*.md to *output_dir*.
    Returns the output file path.
    """
    template_map = {"mbr": "mbr.md.j2", "qbr": "qbr.md.j2", "abr": "abr.md.j2"}
    filename_map = {
        "mbr": "BUSINESS-REVIEW-MBR.md",
        "qbr": "BUSINESS-REVIEW-QBR.md",
        "abr": "BUSINESS-REVIEW-ABR.md",
    }

    if cadence not in template_map:
        raise ValueError(f"Unknown cadence: {cadence}")

    env = _env()
    tpl = env.get_template(template_map[cadence])
    content = tpl.render(version=_get_version(), **review_data)
    out = Path(output_dir) / filename_map[cadence]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return str(out)


def generate_business_review(
    review_data: dict,
    output_dir: str | Path = ".",
) -> str:
    """Render the generic BUSINESS-REVIEW-REPORT.md.

    Uses the ``business_review.md.j2`` template with all sections enabled.
    Returns the output file path.
    """
    env = _env()
    tpl = env.get_template("business_review.md.j2")
    content = tpl.render(version=_get_version(), **review_data)
    out = Path(output_dir) / "BUSINESS-REVIEW-REPORT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return str(out)


def markdown_table(df: pd.DataFrame) -> str:
    """Convert a DataFrame to a Markdown table string."""
    if df.empty:
        return ""
    header = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "| " + " | ".join("---" for _ in df.columns) + " |"
    rows = []
    for _, row in df.iterrows():
        rows.append("| " + " | ".join(str(v) for v in row.values) + " |")
    return "\n".join([header, sep] + rows)
