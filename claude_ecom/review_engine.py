"""Business review engine — orchestrates analysis modules into review data."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from .periods import (
    PeriodRange,
    auto_detect_cadence,
    last_complete_month,
    last_complete_quarter,
    last_complete_year,
    prior_period,
    prior_year_same_period,
    trailing_window,
)


def compute_period_summary(orders: pd.DataFrame, period: PeriodRange) -> dict:
    """Compute KPIs for a calendar period.

    Filters orders to [period.start, period.end] then computes core metrics.
    """
    mask = (orders["order_date"].dt.date >= period.start) & (orders["order_date"].dt.date <= period.end)
    filtered = orders[mask]

    if filtered.empty:
        return {
            "revenue": 0.0,
            "orders": 0,
            "aov": 0.0,
            "customers": 0,
            "new_customers": 0,
            "returning_customers": 0,
            "new_customer_revenue": 0.0,
            "returning_customer_revenue": 0.0,
            "avg_discount_rate": 0.0,
        }

    revenue = float(filtered["amount"].sum())
    n_orders = int(filtered["order_id"].nunique())
    aov = revenue / n_orders if n_orders else 0.0
    customers = int(filtered["customer_id"].nunique())

    # Determine new vs returning based on full order history
    first_order = orders.groupby("customer_id")["order_date"].min()
    period_customers = filtered["customer_id"].unique()
    new_custs = [
        c
        for c in period_customers
        if c in first_order.index and first_order[c].date() >= period.start and first_order[c].date() <= period.end
    ]
    new_customers = len(new_custs)
    returning_customers = customers - new_customers

    new_mask = filtered["customer_id"].isin(new_custs)
    new_customer_revenue = float(filtered.loc[new_mask, "amount"].sum())
    returning_customer_revenue = float(filtered.loc[~new_mask, "amount"].sum())

    avg_discount_rate = 0.0
    if "discount" in filtered.columns:
        gross = filtered["amount"] + filtered["discount"]
        gross_sum = gross.sum()
        avg_discount_rate = float(filtered["discount"].sum() / gross_sum) if gross_sum else 0.0

    return {
        "revenue": revenue,
        "orders": n_orders,
        "aov": aov,
        "customers": customers,
        "new_customers": new_customers,
        "returning_customers": returning_customers,
        "new_customer_revenue": new_customer_revenue,
        "returning_customer_revenue": returning_customer_revenue,
        "avg_discount_rate": avg_discount_rate,
    }


def compute_period_comparison(current: dict, previous: dict) -> dict:
    """Compute % change for each KPI between two periods."""
    result = {}
    for key in current:
        cur = current[key]
        prev = previous[key]
        if isinstance(cur, (int, float)) and isinstance(prev, (int, float)):
            if prev != 0:
                result[key] = (cur - prev) / abs(prev)
            else:
                result[key] = 0.0 if cur == 0 else float("inf")
        else:
            result[key] = 0.0
    return result


def build_review_data(
    orders: pd.DataFrame,
    cadence: str,
    products: pd.DataFrame | None = None,
    inventory: pd.DataFrame | None = None,
    ref_date: date | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
) -> dict:
    """Main entry point. Builds the full review data structure.

    Parameters
    ----------
    cadence : str
        One of ``"mbr"``, ``"qbr"``, ``"abr"``, ``"general"``.
    period_start, period_end : date, optional
        Explicit period boundaries. When provided, overrides ref_date-based detection.
    """
    from .cohort import rfm_segmentation
    from .decomposition import waterfall_analysis
    from .metrics import compute_cohort_kpis
    from .product import abc_analysis, category_performance, product_lifecycle

    # Resolve "general" cadence to a concrete cadence based on data span
    effective_cadence = cadence
    if cadence == "general":
        effective_cadence = auto_detect_cadence(orders)

    # 1. Determine target period + comparison periods
    if period_start and period_end:
        span_days = (period_end - period_start).days
        label = f"{period_start.isoformat()} to {period_end.isoformat()}"
        target = PeriodRange(label=label, start=period_start, end=period_end)
    elif effective_cadence == "mbr":
        target = last_complete_month(ref_date)
    elif effective_cadence == "qbr":
        target = last_complete_quarter(ref_date)
    elif effective_cadence == "abr":
        target = last_complete_year(ref_date)
    else:
        raise ValueError(f"Unknown cadence: {cadence}")

    prev = prior_period(target, effective_cadence)

    comparisons = [
        {"label": _comparison_label(effective_cadence, "pop"), "period": prev},
    ]
    if effective_cadence in ("mbr", "qbr"):
        yoy_period = prior_year_same_period(target, effective_cadence)
        comparisons.append({"label": _comparison_label(effective_cadence, "yoy"), "period": yoy_period})

    # 2. Compute period summaries
    target_summary = compute_period_summary(orders, target)
    comparison_summaries = []
    for comp in comparisons:
        summary = compute_period_summary(orders, comp["period"])
        delta = compute_period_comparison(target_summary, summary)
        comparison_summaries.append(
            {
                "label": comp["label"],
                "period": comp["period"],
                "summary": summary,
                "delta": delta,
            }
        )

    # 3. Revenue decomposition: waterfall bridge (target vs prior period)
    target_month_str = target.start.strftime("%Y-%m")
    prev_month_str = prev.start.strftime("%Y-%m")
    waterfall = None
    try:
        waterfall = waterfall_analysis(orders, prev_month_str, target_month_str)
        waterfall_dict = {
            "period1": waterfall.period1,
            "period2": waterfall.period2,
            "total_change": waterfall.total_change,
            "aov_effect": waterfall.components.get("aov_effect", 0),
            "order_count_effect": waterfall.components.get("order_count_effect", 0),
        }
    except Exception:
        waterfall_dict = None

    # 4. New vs Returning split
    returning_share = (
        target_summary["returning_customer_revenue"] / target_summary["revenue"] if target_summary["revenue"] else 0
    )

    # 5. Customer analysis: RFM + F2
    rfm = rfm_segmentation(orders)
    segment_counts = rfm["segment"].value_counts().to_dict()
    cohort_kpis = compute_cohort_kpis(orders)

    # 6. Product analysis
    abc = abc_analysis(orders)
    abc_summary = abc["abc_rank"].value_counts().to_dict()
    top_products = abc.head(10).to_dict("records")

    lifecycle = product_lifecycle(orders, products)
    lifecycle_dist = lifecycle["lifecycle_stage"].value_counts().to_dict()

    category_perf = category_performance(orders)
    category_data = category_perf.head(10).to_dict("records") if not category_perf.empty else []

    # 7. Trailing temperature check
    ref = ref_date or date.today()
    trail_30 = trailing_window(ref, 30)
    trail_90 = trailing_window(ref, 90)
    trail_30_summary = compute_period_summary(orders, trail_30)
    trail_90_summary = compute_period_summary(orders, trail_90)

    # 8. Build review data dict
    review_data = {
        "cadence": cadence,
        "effective_cadence": effective_cadence,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "period": {
            "label": target.label,
            "start": target.start.isoformat(),
            "end": target.end.isoformat(),
        },
        "target_summary": target_summary,
        "comparisons": comparison_summaries,
        "waterfall": waterfall_dict,
        "new_vs_returning": {
            "new_revenue": target_summary["new_customer_revenue"],
            "returning_revenue": target_summary["returning_customer_revenue"],
            "returning_share": returning_share,
        },
        "customer_analysis": {
            "rfm_segments": segment_counts,
            "f2_rate": cohort_kpis["f2_rate"],
            "avg_purchase_interval_days": cohort_kpis["avg_purchase_interval_days"],
            "total_customers": cohort_kpis["total_customers"],
        },
        "product_analysis": {
            "abc_summary": abc_summary,
            "top_products": top_products,
            "lifecycle_distribution": lifecycle_dist,
            "category_performance": category_data,
        },
        "trailing": {
            "30d": trail_30_summary,
            "90d": trail_90_summary,
        },
        "findings": [],
    }

    # Generate hypotheses (cadence-specific cap)
    review_data["findings"] = _generate_hypotheses(review_data, effective_cadence)

    # Risk assessment
    review_data["risks"] = _assess_risks(review_data, effective_cadence)

    # Recommendations
    review_data["recommendations"] = _generate_recommendations(review_data, effective_cadence)

    # ABR-specific: monthly trend + growth drivers
    if effective_cadence == "abr":
        review_data["monthly_trend"] = _compute_monthly_trend(orders, target.start.year)
        if comparison_summaries:
            prev_summary = comparison_summaries[0]["summary"]
            review_data["growth_drivers"] = _compute_growth_drivers(target_summary, prev_summary)
        else:
            review_data["growth_drivers"] = {}

    return review_data


def _generate_hypotheses(review_data: dict, cadence: str) -> list[dict]:
    """Cross-reference metric movements to generate 'why' hypotheses.

    Returns list of dicts with keys: title, situation, complication, decision.
    Max 3 findings.
    """
    findings = []
    target = review_data["target_summary"]
    comparisons = review_data["comparisons"]

    if not comparisons:
        return findings

    # Use the first comparison (period-over-period) for primary analysis
    pop_delta = comparisons[0]["delta"]

    # Revenue direction
    rev_delta = pop_delta.get("revenue", 0)
    orders_delta = pop_delta.get("orders", 0)
    aov_delta = pop_delta.get("aov", 0)
    new_cust_delta = pop_delta.get("new_customers", 0)
    returning_rev_delta = pop_delta.get("returning_customer_revenue", 0)
    discount_delta = pop_delta.get("avg_discount_rate", 0)

    if cadence == "mbr":
        findings = _mbr_hypotheses(
            rev_delta,
            orders_delta,
            aov_delta,
            new_cust_delta,
            returning_rev_delta,
            discount_delta,
            target,
        )
    elif cadence == "qbr":
        findings = _qbr_hypotheses(
            rev_delta,
            orders_delta,
            aov_delta,
            new_cust_delta,
            returning_rev_delta,
            discount_delta,
            target,
            review_data,
        )
    elif cadence == "abr":
        findings = _abr_hypotheses(
            rev_delta,
            orders_delta,
            aov_delta,
            target,
            review_data,
        )

    caps = {"mbr": 3, "qbr": 4, "abr": 5, "general": 5}
    return findings[:caps.get(cadence, 5)]


def _mbr_hypotheses(
    rev_delta,
    orders_delta,
    aov_delta,
    new_cust_delta,
    returning_rev_delta,
    discount_delta,
    target,
) -> list[dict]:
    """MBR: short-term focus hypotheses."""
    findings = []

    if rev_delta < -0.05 and orders_delta < -0.05 and abs(aov_delta) < 0.05:
        findings.append(
            {
                "title": "Traffic or Acquisition Drop",
                "situation": (
                    f"Revenue declined {rev_delta:.1%} with orders down {orders_delta:.1%}, while AOV remained stable."
                ),
                "complication": (
                    "Fewer customers are entering the funnel. This could indicate "
                    "paid channel underperformance, seasonal dip, or organic traffic loss."
                ),
                "decision": (
                    "Audit acquisition channels (paid search, social) for spend or "
                    "efficiency changes. Check Google Analytics for traffic source shifts."
                ),
            }
        )

    if rev_delta < -0.05 and aov_delta < -0.05 and abs(orders_delta) < 0.05:
        findings.append(
            {
                "title": "Mix Shift or Heavier Discounting",
                "situation": (
                    f"Revenue declined {rev_delta:.1%} driven by AOV dropping "
                    f"{aov_delta:.1%}, while order volume held steady."
                ),
                "complication": (
                    "Customers are spending less per order. This may reflect heavier "
                    "promotions, a shift toward lower-price items, or smaller basket sizes."
                ),
                "decision": (
                    "Review promotional calendar for discount depth changes. "
                    "Analyze category mix shift and bundle/upsell performance."
                ),
            }
        )

    if discount_delta > 0.02:
        findings.append(
            {
                "title": "Increasing Promo Dependency",
                "situation": f"Average discount rate increased by {discount_delta:.1%} vs prior month.",
                "complication": (
                    "Rising discount rates erode margin and can condition customers "
                    "to wait for sales, creating a vicious cycle."
                ),
                "decision": (
                    "Cap discount depth at current levels. Shift from blanket discounts "
                    "to targeted, value-added incentives "
                    "(free shipping thresholds, gift-with-purchase)."
                ),
            }
        )

    if new_cust_delta < -0.10:
        findings.append(
            {
                "title": "New Customer Acquisition Decline",
                "situation": f"New customer count dropped {new_cust_delta:.1%} vs prior month.",
                "complication": (
                    "Sustained acquisition declines lead to revenue contraction "
                    "within 2-3 months as the customer base shrinks."
                ),
                "decision": (
                    "Review paid channel CPAs and budget allocation. Check for ad fatigue or landing page issues."
                ),
            }
        )

    if returning_rev_delta < -0.10:
        findings.append(
            {
                "title": "Returning Customer Revenue Drop",
                "situation": f"Revenue from returning customers declined {returning_rev_delta:.1%}.",
                "complication": (
                    "Returning customers are the most profitable segment. "
                    "Declining repeat revenue signals retention or engagement issues."
                ),
                "decision": (
                    "Launch win-back campaigns for lapsed customers. Review "
                    "post-purchase email flows and loyalty program engagement."
                ),
            }
        )

    # If revenue is up, add a positive finding
    if rev_delta > 0.05:
        findings.append(
            {
                "title": "Revenue Growth Momentum",
                "situation": f"Revenue grew {rev_delta:.1%} vs prior month.",
                "complication": (
                    "Sustained growth requires monitoring whether it's driven by "
                    "acquisition (scalable) or one-time factors (promotions, seasonal)."
                ),
                "decision": (
                    "Identify the primary growth driver (new customers, AOV, or "
                    "repeat) and double down on sustainable channels."
                ),
            }
        )

    return findings


def _qbr_hypotheses(
    rev_delta,
    orders_delta,
    aov_delta,
    new_cust_delta,
    returning_rev_delta,
    discount_delta,
    target,
    review_data,
) -> list[dict]:
    """QBR: structural focus hypotheses."""
    findings = []

    f2_rate = review_data["customer_analysis"]["f2_rate"]
    if f2_rate < 0.20:
        findings.append(
            {
                "title": "Low F2 Conversion Rate",
                "situation": f"Only {f2_rate:.1%} of customers make a second purchase.",
                "complication": (
                    "A low F2 rate means the business must continuously acquire new "
                    "customers to maintain revenue — an expensive and unsustainable model."
                ),
                "decision": (
                    "Implement post-purchase engagement series. Test first-purchase "
                    "incentives for second order "
                    "(e.g., 'Thank you' discount within 30 days)."
                ),
            }
        )

    returning_share = review_data["new_vs_returning"]["returning_share"]
    if returning_share < 0.30:
        findings.append(
            {
                "title": "Weak Retention Structure",
                "situation": f"Returning customers contribute only {returning_share:.1%} of revenue.",
                "complication": (
                    "Healthy e-commerce businesses derive 40-60% of revenue from "
                    "repeat customers. Low repeat share indicates acquisition dependency."
                ),
                "decision": (
                    "Build tiered loyalty program. Implement automated win-back "
                    "flows for 60/90/120-day lapsed customers."
                ),
            }
        )

    abc_summary = review_data["product_analysis"]["abc_summary"]
    a_count = abc_summary.get("A", 0)
    total_products = sum(abc_summary.values())
    if total_products > 0 and a_count / total_products < 0.15:
        findings.append(
            {
                "title": "Revenue Concentration in Few Products",
                "situation": (
                    f"Only {a_count} products ({a_count / total_products:.1%} of catalog) drive 80% of revenue."
                ),
                "complication": (
                    "Heavy dependence on a small number of products creates risk if "
                    "those products face supply issues, competition, or demand shifts."
                ),
                "decision": (
                    "Develop growth strategies for B-tier products. Test cross-sell "
                    "and bundle offers to broaden the revenue base."
                ),
            }
        )

    if rev_delta < -0.05:
        findings.append(
            {
                "title": "Quarterly Revenue Decline",
                "situation": f"Revenue declined {rev_delta:.1%} quarter-over-quarter.",
                "complication": (
                    "Quarterly declines are harder to attribute to short-term "
                    "fluctuations and may indicate structural issues in "
                    "demand, pricing, or competition."
                ),
                "decision": (
                    "Conduct deep-dive into category-level performance. Compare "
                    "customer acquisition cost trends and channel mix shifts."
                ),
            }
        )

    if rev_delta > 0.05:
        findings.append(
            {
                "title": "Quarterly Growth Sustained",
                "situation": f"Revenue grew {rev_delta:.1%} quarter-over-quarter.",
                "complication": (
                    "Ensure growth is balanced between new acquisition and repeat, "
                    "and not solely driven by unsustainable promotions."
                ),
                "decision": (
                    "Decompose growth by customer type (new vs returning) and "
                    "channel. Validate unit economics remain healthy."
                ),
            }
        )

    return findings


def _abr_hypotheses(
    rev_delta,
    orders_delta,
    aov_delta,
    target,
    review_data,
) -> list[dict]:
    """ABR: strategic focus hypotheses."""
    findings = []

    returning_share = review_data["new_vs_returning"]["returning_share"]

    if returning_share < 0.35:
        findings.append(
            {
                "title": "Acquisition-Heavy Growth Model",
                "situation": f"Returning customers contribute only {returning_share:.1%} of annual revenue.",
                "complication": (
                    "An acquisition-heavy model is unsustainable as customer "
                    "acquisition costs rise. LTV must exceed CAC for "
                    "long-term viability."
                ),
                "decision": (
                    "Shift 20-30% of acquisition budget to retention programs. "
                    "Build subscription or replenishment models for "
                    "consumable categories."
                ),
            }
        )

    abc_summary = review_data["product_analysis"]["abc_summary"]
    a_count = abc_summary.get("A", 0)
    total_products = sum(abc_summary.values())
    if total_products > 0 and a_count <= 5:
        findings.append(
            {
                "title": "SKU Dependency Risk",
                "situation": f"Only {a_count} SKUs drive 80% of annual revenue.",
                "complication": (
                    "Extreme product concentration creates existential risk. "
                    "A single supply disruption or competitive entry could "
                    "devastate revenue."
                ),
                "decision": (
                    "Invest in new product development pipeline. Expand into "
                    "adjacent categories with proven demand signals."
                ),
            }
        )

    if rev_delta < -0.03:
        findings.append(
            {
                "title": "Year-over-Year Revenue Decline",
                "situation": f"Annual revenue declined {rev_delta:.1%} year-over-year.",
                "complication": (
                    "Annual declines signal fundamental issues in market position, "
                    "product-market fit, or competitive dynamics."
                ),
                "decision": (
                    "Commission market analysis to understand share shifts. "
                    "Review pricing strategy and product portfolio fit."
                ),
            }
        )

    if rev_delta > 0.10:
        findings.append(
            {
                "title": "Strong Annual Growth",
                "situation": f"Annual revenue grew {rev_delta:.1%} year-over-year.",
                "complication": (
                    "Rapid growth must be validated for quality — ensure margins "
                    "are maintained and customer quality isn't declining."
                ),
                "decision": (
                    "Verify unit economics at scale. Monitor CAC:LTV ratio trends and gross margin trajectory."
                ),
            }
        )

    category_data = review_data["product_analysis"]["category_performance"]
    if len(category_data) >= 2:
        top_share = category_data[0].get("revenue_share", 0) if category_data else 0
        if top_share > 0.50:
            findings.append(
                {
                    "title": "Category Concentration",
                    "situation": f"Top category accounts for {top_share:.1%} of annual revenue.",
                    "complication": (
                        "Over-reliance on a single category limits growth potential "
                        "and increases vulnerability to "
                        "category-specific disruptions."
                    ),
                    "decision": (
                        "Develop second and third category pillars. Allocate "
                        "marketing budget proportionally to growth potential, "
                        "not current size."
                    ),
                }
            )

    return findings


def _assess_risks(review_data: dict, cadence: str) -> list[dict]:
    """Assess business risks based on review data.

    Returns list of dicts with keys: title, severity (High/Medium/Low), description.
    """
    risks = []
    product = review_data.get("product_analysis", {})
    customer = review_data.get("customer_analysis", {})
    target = review_data.get("target_summary", {})
    comparisons = review_data.get("comparisons", [])

    # Revenue concentration risk: top product share > 50%
    top_products = product.get("top_products", [])
    if top_products:
        top_share = top_products[0].get("revenue_share", 0)
        if top_share > 0.50:
            risks.append({
                "title": "Revenue Concentration",
                "severity": "High",
                "description": (
                    f"Top product accounts for {top_share:.1%} of revenue. "
                    "Supply disruption or demand shift in this product would severely impact the business."
                ),
            })
        elif top_share > 0.30:
            risks.append({
                "title": "Revenue Concentration",
                "severity": "Medium",
                "description": (
                    f"Top product accounts for {top_share:.1%} of revenue. "
                    "Consider diversifying revenue sources."
                ),
            })

    # Customer acquisition dependency risk
    returning_share = review_data.get("new_vs_returning", {}).get("returning_share", 0.5)
    if returning_share < 0.30:
        risks.append({
            "title": "Customer Acquisition Dependency",
            "severity": "High",
            "description": (
                f"Returning customers contribute only {returning_share:.1%} of revenue. "
                "The business is heavily dependent on new customer acquisition, "
                "which is typically more expensive and less sustainable."
            ),
        })

    # Discount dependency risk
    pop_delta = comparisons[0]["delta"] if comparisons else {}
    discount_delta = pop_delta.get("avg_discount_rate", 0)
    current_discount = target.get("avg_discount_rate", 0)
    if discount_delta > 0.02 or current_discount > 0.20:
        risks.append({
            "title": "Discount Dependency",
            "severity": "High" if current_discount > 0.25 else "Medium",
            "description": (
                f"Average discount rate is {current_discount:.1%}"
                + (f" (up {discount_delta:.1%} vs prior period)" if discount_delta > 0 else "")
                + ". Rising discount rates erode margins and condition customers to wait for sales."
            ),
        })

    # Product lifecycle risk
    lifecycle = product.get("lifecycle_distribution", {})
    total_lc = sum(lifecycle.values()) if lifecycle else 0
    decline_count = lifecycle.get("Decline", 0)
    if total_lc > 0 and decline_count / total_lc > 0.30:
        risks.append({
            "title": "Product Lifecycle Risk",
            "severity": "High" if decline_count / total_lc > 0.50 else "Medium",
            "description": (
                f"{decline_count}/{total_lc} products ({decline_count / total_lc:.1%}) "
                "are in decline stage. The catalog needs renewal to sustain growth."
            ),
        })

    # Growth sustainability risk
    rev_delta = pop_delta.get("revenue", 0)
    new_cust_delta = pop_delta.get("new_customers", 0)
    if rev_delta < -0.05 and new_cust_delta < -0.05:
        risks.append({
            "title": "Growth Sustainability",
            "severity": "High",
            "description": (
                f"Revenue declining ({rev_delta:.1%}) alongside new customer decline ({new_cust_delta:.1%}). "
                "Both demand and acquisition are contracting, signaling a structural growth problem."
            ),
        })

    # Sort by severity
    severity_order = {"High": 0, "Medium": 1, "Low": 2}
    risks.sort(key=lambda r: severity_order.get(r["severity"], 9))
    return risks[:3]


def _generate_recommendations(review_data: dict, cadence: str) -> list[dict]:
    """Generate forward-looking action recommendations.

    Returns list of dicts with keys: title, description, expected_impact, timeline.
    """
    recommendations = []
    findings = review_data.get("findings", [])
    risks = review_data.get("risks", [])

    timeline_map = {
        "mbr": ("Next 30 days", "short-term"),
        "qbr": ("Next 90 days", "medium-term"),
        "abr": ("Next 12 months", "strategic"),
    }
    default_timeline = timeline_map.get(cadence, ("Next 90 days", "medium-term"))

    # Generate from risks
    for risk in risks:
        if risk["title"] == "Revenue Concentration":
            recommendations.append({
                "title": "Diversify Revenue Sources",
                "description": (
                    "Develop growth strategies for B-tier products. "
                    "Test cross-sell bundles and category expansion to reduce top-product dependency."
                ),
                "expected_impact": "Reduce top-product revenue share by 10-15pp",
                "timeline": default_timeline[0],
            })
        elif risk["title"] == "Customer Acquisition Dependency":
            recommendations.append({
                "title": "Strengthen Retention Programs",
                "description": (
                    "Implement post-purchase engagement series and loyalty program. "
                    "Target F2 conversion with 30-day incentive offers."
                ),
                "expected_impact": "Increase returning customer revenue share by 5-10pp",
                "timeline": default_timeline[0],
            })
        elif risk["title"] == "Discount Dependency":
            recommendations.append({
                "title": "Optimize Promotion Strategy",
                "description": (
                    "Cap discount depth at current levels. Shift from blanket discounts "
                    "to targeted, value-added incentives (free shipping thresholds, gift-with-purchase)."
                ),
                "expected_impact": "Reduce average discount rate by 2-5pp while maintaining volume",
                "timeline": default_timeline[0],
            })
        elif risk["title"] == "Product Lifecycle Risk":
            recommendations.append({
                "title": "Accelerate Catalog Renewal",
                "description": (
                    "Identify decline-stage products for markdown/exit. "
                    "Invest in new product development pipeline for emerging categories."
                ),
                "expected_impact": "Reduce decline-stage product share below 30%",
                "timeline": default_timeline[0],
            })
        elif risk["title"] == "Growth Sustainability":
            recommendations.append({
                "title": "Revitalize Growth Engine",
                "description": (
                    "Audit acquisition channels for efficiency. "
                    "Test new traffic sources and reactivate lapsed customer segments."
                ),
                "expected_impact": "Reverse revenue decline trend within 1-2 periods",
                "timeline": default_timeline[0],
            })

    # Add finding-based recommendations if under cap
    for finding in findings:
        if len(recommendations) >= 5:
            break
        if finding["title"] == "Low F2 Conversion Rate":
            recommendations.append({
                "title": "Improve First-to-Second Purchase Conversion",
                "description": finding.get("decision", "Implement post-purchase engagement series."),
                "expected_impact": "Increase F2 rate by 3-5pp",
                "timeline": default_timeline[0],
            })

    # Deduplicate by title
    seen = set()
    unique = []
    for r in recommendations:
        if r["title"] not in seen:
            seen.add(r["title"])
            unique.append(r)
    return unique[:5]


def _compute_monthly_trend(orders: pd.DataFrame, year: int) -> list[dict]:
    """Compute 12-month KPI series for a given year (ABR use).

    Returns list of dicts with keys: month, revenue, orders, aov, customers.
    """
    import calendar

    trend = []
    for month in range(1, 13):
        last_day = calendar.monthrange(year, month)[1]
        period = PeriodRange(
            label=f"{year}-{month:02d}",
            start=date(year, month, 1),
            end=date(year, month, last_day),
        )
        summary = compute_period_summary(orders, period)
        trend.append({
            "month": f"{year}-{month:02d}",
            "revenue": summary["revenue"],
            "orders": summary["orders"],
            "aov": summary["aov"],
            "customers": summary["customers"],
        })
    return trend


def _compute_growth_drivers(target_summary: dict, prev_summary: dict) -> dict:
    """Decompose YoY growth into acquisition, retention, and AOV effects.

    Returns dict with keys: acquisition_effect, retention_effect, aov_effect, total_change.
    """
    prev_rev = prev_summary.get("revenue", 0)
    if prev_rev == 0:
        return {
            "acquisition_effect": 0.0,
            "retention_effect": 0.0,
            "aov_effect": 0.0,
            "total_change": 0.0,
        }

    total_change = target_summary["revenue"] - prev_rev

    # Acquisition effect: change in new customer revenue
    acq_effect = target_summary.get("new_customer_revenue", 0) - prev_summary.get("new_customer_revenue", 0)

    # Retention effect: change in returning customer revenue
    ret_effect = target_summary.get("returning_customer_revenue", 0) - prev_summary.get(
        "returning_customer_revenue", 0
    )

    # AOV effect: residual (total - acquisition - retention)
    aov_effect = total_change - acq_effect - ret_effect

    return {
        "acquisition_effect": acq_effect,
        "retention_effect": ret_effect,
        "aov_effect": aov_effect,
        "total_change": total_change,
    }


def _comparison_label(cadence: str, comparison_type: str) -> str:
    """Return a human-readable label for a comparison axis."""
    labels = {
        ("mbr", "pop"): "vs Prior Month",
        ("mbr", "yoy"): "vs Same Month Last Year",
        ("qbr", "pop"): "vs Prior Quarter",
        ("qbr", "yoy"): "vs Same Quarter Last Year",
        ("abr", "pop"): "vs Prior Year",
    }
    return labels.get((cadence, comparison_type), "")
