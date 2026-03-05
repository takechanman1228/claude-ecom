"""Business review engine — orchestrates analysis modules into review data."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from .periods import (
    PeriodRange,
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
    mask = (orders["order_date"].dt.date >= period.start) & (
        orders["order_date"].dt.date <= period.end
    )
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
        if c in first_order.index
        and first_order[c].date() >= period.start
        and first_order[c].date() <= period.end
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
) -> dict:
    """Main entry point. Builds the full review data structure.

    Parameters
    ----------
    cadence : str
        One of ``"mbr"``, ``"qbr"``, ``"abr"``.
    """
    from .cohort import rfm_segmentation
    from .decomposition import waterfall_analysis
    from .metrics import compute_cohort_kpis
    from .product import abc_analysis, category_performance, product_lifecycle

    # 1. Determine target period + comparison periods
    if cadence == "mbr":
        target = last_complete_month(ref_date)
    elif cadence == "qbr":
        target = last_complete_quarter(ref_date)
    elif cadence == "abr":
        target = last_complete_year(ref_date)
    else:
        raise ValueError(f"Unknown cadence: {cadence}")

    prev = prior_period(target, cadence)

    comparisons = [
        {"label": _comparison_label(cadence, "pop"), "period": prev},
    ]
    if cadence in ("mbr", "qbr"):
        yoy_period = prior_year_same_period(target, cadence)
        comparisons.append(
            {"label": _comparison_label(cadence, "yoy"), "period": yoy_period}
        )

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
        target_summary["returning_customer_revenue"] / target_summary["revenue"]
        if target_summary["revenue"]
        else 0
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

    # Generate hypotheses
    review_data["findings"] = _generate_hypotheses(review_data, cadence)

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
    pop_prev = comparisons[0]["summary"]

    # Revenue direction
    rev_delta = pop_delta.get("revenue", 0)
    orders_delta = pop_delta.get("orders", 0)
    aov_delta = pop_delta.get("aov", 0)
    new_cust_delta = pop_delta.get("new_customers", 0)
    returning_rev_delta = pop_delta.get("returning_customer_revenue", 0)
    discount_delta = pop_delta.get("avg_discount_rate", 0)

    if cadence == "mbr":
        findings = _mbr_hypotheses(
            rev_delta, orders_delta, aov_delta, new_cust_delta,
            returning_rev_delta, discount_delta, target,
        )
    elif cadence == "qbr":
        findings = _qbr_hypotheses(
            rev_delta, orders_delta, aov_delta, new_cust_delta,
            returning_rev_delta, discount_delta, target, review_data,
        )
    elif cadence == "abr":
        findings = _abr_hypotheses(
            rev_delta, orders_delta, aov_delta, target, review_data,
        )

    return findings[:3]


def _mbr_hypotheses(
    rev_delta, orders_delta, aov_delta, new_cust_delta,
    returning_rev_delta, discount_delta, target,
) -> list[dict]:
    """MBR: short-term focus hypotheses."""
    findings = []

    if rev_delta < -0.05 and orders_delta < -0.05 and abs(aov_delta) < 0.05:
        findings.append({
            "title": "Traffic or Acquisition Drop",
            "situation": f"Revenue declined {rev_delta:.1%} with orders down {orders_delta:.1%}, while AOV remained stable.",
            "complication": "Fewer customers are entering the funnel. This could indicate paid channel underperformance, seasonal dip, or organic traffic loss.",
            "decision": "Audit acquisition channels (paid search, social) for spend or efficiency changes. Check Google Analytics for traffic source shifts.",
        })

    if rev_delta < -0.05 and aov_delta < -0.05 and abs(orders_delta) < 0.05:
        findings.append({
            "title": "Mix Shift or Heavier Discounting",
            "situation": f"Revenue declined {rev_delta:.1%} driven by AOV dropping {aov_delta:.1%}, while order volume held steady.",
            "complication": "Customers are spending less per order. This may reflect heavier promotions, a shift toward lower-price items, or smaller basket sizes.",
            "decision": "Review promotional calendar for discount depth changes. Analyze category mix shift and bundle/upsell performance.",
        })

    if discount_delta > 0.02:
        findings.append({
            "title": "Increasing Promo Dependency",
            "situation": f"Average discount rate increased by {discount_delta:.1%} vs prior month.",
            "complication": "Rising discount rates erode margin and can condition customers to wait for sales, creating a vicious cycle.",
            "decision": "Cap discount depth at current levels. Shift from blanket discounts to targeted, value-added incentives (free shipping thresholds, gift-with-purchase).",
        })

    if new_cust_delta < -0.10:
        findings.append({
            "title": "New Customer Acquisition Decline",
            "situation": f"New customer count dropped {new_cust_delta:.1%} vs prior month.",
            "complication": "Sustained acquisition declines lead to revenue contraction within 2-3 months as the customer base shrinks.",
            "decision": "Review paid channel CPAs and budget allocation. Check for ad fatigue or landing page issues.",
        })

    if returning_rev_delta < -0.10:
        findings.append({
            "title": "Returning Customer Revenue Drop",
            "situation": f"Revenue from returning customers declined {returning_rev_delta:.1%}.",
            "complication": "Returning customers are the most profitable segment. Declining repeat revenue signals retention or engagement issues.",
            "decision": "Launch win-back campaigns for lapsed customers. Review post-purchase email flows and loyalty program engagement.",
        })

    # If revenue is up, add a positive finding
    if rev_delta > 0.05:
        findings.append({
            "title": "Revenue Growth Momentum",
            "situation": f"Revenue grew {rev_delta:.1%} vs prior month.",
            "complication": "Sustained growth requires monitoring whether it's driven by acquisition (scalable) or one-time factors (promotions, seasonal).",
            "decision": "Identify the primary growth driver (new customers, AOV, or repeat) and double down on sustainable channels.",
        })

    return findings


def _qbr_hypotheses(
    rev_delta, orders_delta, aov_delta, new_cust_delta,
    returning_rev_delta, discount_delta, target, review_data,
) -> list[dict]:
    """QBR: structural focus hypotheses."""
    findings = []

    f2_rate = review_data["customer_analysis"]["f2_rate"]
    if f2_rate < 0.20:
        findings.append({
            "title": "Low F2 Conversion Rate",
            "situation": f"Only {f2_rate:.1%} of customers make a second purchase.",
            "complication": "A low F2 rate means the business must continuously acquire new customers to maintain revenue — an expensive and unsustainable model.",
            "decision": "Implement post-purchase engagement series. Test first-purchase incentives for second order (e.g., 'Thank you' discount within 30 days).",
        })

    returning_share = review_data["new_vs_returning"]["returning_share"]
    if returning_share < 0.30:
        findings.append({
            "title": "Weak Retention Structure",
            "situation": f"Returning customers contribute only {returning_share:.1%} of revenue.",
            "complication": "Healthy e-commerce businesses derive 40-60% of revenue from repeat customers. Low repeat share indicates acquisition dependency.",
            "decision": "Build tiered loyalty program. Implement automated win-back flows for 60/90/120-day lapsed customers.",
        })

    abc_summary = review_data["product_analysis"]["abc_summary"]
    a_count = abc_summary.get("A", 0)
    total_products = sum(abc_summary.values())
    if total_products > 0 and a_count / total_products < 0.15:
        findings.append({
            "title": "Revenue Concentration in Few Products",
            "situation": f"Only {a_count} products ({a_count/total_products:.1%} of catalog) drive 80% of revenue.",
            "complication": "Heavy dependence on a small number of products creates risk if those products face supply issues, competition, or demand shifts.",
            "decision": "Develop growth strategies for B-tier products. Test cross-sell and bundle offers to broaden the revenue base.",
        })

    if rev_delta < -0.05:
        findings.append({
            "title": "Quarterly Revenue Decline",
            "situation": f"Revenue declined {rev_delta:.1%} quarter-over-quarter.",
            "complication": "Quarterly declines are harder to attribute to short-term fluctuations and may indicate structural issues in demand, pricing, or competition.",
            "decision": "Conduct deep-dive into category-level performance. Compare customer acquisition cost trends and channel mix shifts.",
        })

    if rev_delta > 0.05:
        findings.append({
            "title": "Quarterly Growth Sustained",
            "situation": f"Revenue grew {rev_delta:.1%} quarter-over-quarter.",
            "complication": "Ensure growth is balanced between new acquisition and repeat, and not solely driven by unsustainable promotions.",
            "decision": "Decompose growth by customer type (new vs returning) and channel. Validate unit economics remain healthy.",
        })

    return findings


def _abr_hypotheses(
    rev_delta, orders_delta, aov_delta, target, review_data,
) -> list[dict]:
    """ABR: strategic focus hypotheses."""
    findings = []

    f2_rate = review_data["customer_analysis"]["f2_rate"]
    returning_share = review_data["new_vs_returning"]["returning_share"]

    if returning_share < 0.35:
        findings.append({
            "title": "Acquisition-Heavy Growth Model",
            "situation": f"Returning customers contribute only {returning_share:.1%} of annual revenue.",
            "complication": "An acquisition-heavy model is unsustainable as customer acquisition costs rise. LTV must exceed CAC for long-term viability.",
            "decision": "Shift 20-30% of acquisition budget to retention programs. Build subscription or replenishment models for consumable categories.",
        })

    abc_summary = review_data["product_analysis"]["abc_summary"]
    a_count = abc_summary.get("A", 0)
    total_products = sum(abc_summary.values())
    if total_products > 0 and a_count <= 5:
        findings.append({
            "title": "SKU Dependency Risk",
            "situation": f"Only {a_count} SKUs drive 80% of annual revenue.",
            "complication": "Extreme product concentration creates existential risk. A single supply disruption or competitive entry could devastate revenue.",
            "decision": "Invest in new product development pipeline. Expand into adjacent categories with proven demand signals.",
        })

    if rev_delta < -0.03:
        findings.append({
            "title": "Year-over-Year Revenue Decline",
            "situation": f"Annual revenue declined {rev_delta:.1%} year-over-year.",
            "complication": "Annual declines signal fundamental issues in market position, product-market fit, or competitive dynamics.",
            "decision": "Commission market analysis to understand share shifts. Review pricing strategy and product portfolio fit.",
        })

    if rev_delta > 0.10:
        findings.append({
            "title": "Strong Annual Growth",
            "situation": f"Annual revenue grew {rev_delta:.1%} year-over-year.",
            "complication": "Rapid growth must be validated for quality — ensure margins are maintained and customer quality isn't declining.",
            "decision": "Verify unit economics at scale. Monitor CAC:LTV ratio trends and gross margin trajectory.",
        })

    category_data = review_data["product_analysis"]["category_performance"]
    if len(category_data) >= 2:
        top_share = category_data[0].get("revenue_share", 0) if category_data else 0
        if top_share > 0.50:
            findings.append({
                "title": "Category Concentration",
                "situation": f"Top category accounts for {top_share:.1%} of annual revenue.",
                "complication": "Over-reliance on a single category limits growth potential and increases vulnerability to category-specific disruptions.",
                "decision": "Develop second and third category pillars. Allocate marketing budget proportionally to growth potential, not current size.",
            })

    return findings


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
