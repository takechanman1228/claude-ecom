"""CLI entry point for ecom-analytics."""

from __future__ import annotations

import json
import sys

import click

from ecom_analytics import __version__
from ecom_analytics.loader import (
    load_orders,
    load_products,
    load_inventory,
    load_shopify_analytics,
    detect_analytics_dir,
)
from ecom_analytics.metrics import (
    compute_revenue_kpis,
    compute_cohort_kpis,
    compute_inventory_kpis,
    compute_product_kpis,
    compute_revenue_kpis_from_analytics,
    compute_funnel_kpis_from_analytics,
    compute_product_kpis_from_analytics,
    compute_retention_kpis_from_analytics,
)
from ecom_analytics.decomposition import decompose_revenue
from ecom_analytics.cohort import build_cohort_matrix, compute_retention_curve, estimate_ltv, rfm_segmentation
from ecom_analytics.product import abc_analysis, cross_sell_matrix
from ecom_analytics.inventory import stockout_analysis, overstock_analysis
from ecom_analytics.pricing import discount_dependency, margin_analysis
from ecom_analytics.scoring import CheckResult, score_checks
from ecom_analytics.report import (
    generate_audit_report,
    generate_action_plan,
    generate_quick_wins,
    ascii_bar_chart,
)


@click.group()
@click.version_option(version=__version__)
def cli():
    """ecom-analytics: EC-specialized data analytics toolkit."""
    pass


@cli.command()
@click.argument("orders_path")
@click.option("--products", "products_path", default=None, help="Products CSV path")
@click.option("--inventory", "inventory_path", default=None, help="Inventory CSV path")
@click.option("--format", "fmt", default="auto", help="CSV format (shopify|generic|auto)")
@click.option("--output", default="./", help="Output directory for reports")
def audit(orders_path, products_path, inventory_path, fmt, output):
    """Run a full EC health audit and generate reports."""
    click.echo("Loading data...")
    orders = load_orders(orders_path, fmt=fmt)
    products = load_products(products_path) if products_path else None
    inventory = load_inventory(inventory_path) if inventory_path else None

    click.echo("Computing KPIs...")
    rev_kpis = compute_revenue_kpis(orders)
    cohort_kpis = compute_cohort_kpis(orders)

    # Build check results (simplified — in production each sub-module contributes)
    checks = _build_checks(rev_kpis, cohort_kpis, orders, products, inventory)

    click.echo("Scoring...")
    health = score_checks(checks)

    click.echo(f"\nOverall Score: {health.overall_score}/100 (Grade: {health.overall_grade})")
    for cat, cs in health.category_scores.items():
        click.echo(f"  {cat:>12}: {cs.score}/100 ({cs.grade})")

    click.echo(f"\nGenerating reports to {output} ...")
    annual_revenue = rev_kpis["total_revenue"]
    generate_audit_report(health, annual_revenue, output_dir=output)
    generate_action_plan(health, annual_revenue, output_dir=output)
    generate_quick_wins(health, annual_revenue, output_dir=output)
    click.echo("Done. Reports: AUDIT-REPORT.md, ACTION-PLAN.md, QUICK-WINS.md")


@cli.command("audit-analytics")
@click.argument("data_dir")
@click.option("--output", default="./", help="Output directory for reports")
def audit_analytics(data_dir, output):
    """Run a full EC health audit from Shopify Analytics exports (aggregated data).

    DATA_DIR should be a directory containing Shopify Analytics CSV exports
    (e.g., 'Total sales over time', 'Conversion rate over time', etc.).
    """
    click.echo(f"Loading Shopify Analytics data from {data_dir}...")
    data = load_shopify_analytics(data_dir)
    click.echo(f"  Loaded {len(data.loaded_files)} files: {', '.join(data.loaded_files)}")
    if data.missing_files:
        click.echo(f"  Missing (optional): {', '.join(data.missing_files)}")

    click.echo("Computing KPIs...")
    rev_kpis = compute_revenue_kpis_from_analytics(data)
    funnel_kpis = compute_funnel_kpis_from_analytics(data)
    product_kpis = compute_product_kpis_from_analytics(data)
    retention_kpis = compute_retention_kpis_from_analytics(data)

    click.echo(f"\n=== Revenue Summary ===")
    click.echo(f"  Total Revenue:     ${rev_kpis.get('total_revenue', 0):>12,.2f}")
    click.echo(f"  Total Orders:      {rev_kpis.get('total_orders', 0):>12,}")
    click.echo(f"  AOV:               ${rev_kpis.get('aov', 0):>12,.2f}")
    click.echo(f"  MoM Growth:        {rev_kpis.get('mom_growth_latest', 0):>12.1%}")
    click.echo(f"  Discount Rate:     {rev_kpis.get('avg_discount_rate', 0):>12.1%}")
    click.echo(f"  Repeat Rev Share:  {rev_kpis.get('repeat_revenue_share', 0):>12.1%}")
    if "gross_margin" in rev_kpis:
        click.echo(f"  Gross Margin:      {rev_kpis['gross_margin']:>12.1%}")

    if funnel_kpis:
        click.echo(f"\n=== Conversion Funnel ===")
        click.echo(f"  Overall CVR:       {funnel_kpis.get('overall_cvr', 0):>12.2%}")
        click.echo(f"  Cart Add Rate:     {funnel_kpis.get('cart_addition_rate', 0):>12.2%}")
        click.echo(f"  Cart Abandon:      {funnel_kpis.get('cart_abandonment_rate', 0):>12.2%}")
        click.echo(f"  Checkout Abandon:  {funnel_kpis.get('checkout_abandonment_rate', 0):>12.2%}")

    if retention_kpis:
        click.echo(f"\n=== Customer Retention ===")
        click.echo(f"  Returning Ratio:   {retention_kpis.get('returning_customer_ratio', 0):>12.1%}")
        click.echo(f"  Avg Rev/Returning: ${retention_kpis.get('avg_rev_per_returning', 0):>12,.2f}")
        click.echo(f"  Avg Rev/New:       ${retention_kpis.get('avg_rev_per_new', 0):>12,.2f}")

    # Build checks from aggregated KPIs
    checks = _build_checks_from_analytics(rev_kpis, funnel_kpis, product_kpis, retention_kpis)

    click.echo("\nScoring...")
    health = score_checks(checks)

    click.echo(f"\nOverall Score: {health.overall_score}/100 (Grade: {health.overall_grade})")
    for cat, cs in health.category_scores.items():
        click.echo(f"  {cat:>12}: {cs.score}/100 ({cs.grade})")

    click.echo(f"\nGenerating reports to {output} ...")
    annual_revenue = rev_kpis.get("total_revenue", 0)
    # Calculate date range from data
    data_start = ""
    data_end = ""
    if data.sales is not None:
        data_start = data.sales["Month"].min().strftime("%Y-%m-%d")
        data_end = data.sales["Month"].max().strftime("%Y-%m-%d")

    generate_audit_report(health, annual_revenue, data_start=data_start, data_end=data_end, output_dir=output)
    generate_action_plan(health, annual_revenue, output_dir=output)
    generate_quick_wins(health, annual_revenue, output_dir=output)
    click.echo("Done. Reports: AUDIT-REPORT.md, ACTION-PLAN.md, QUICK-WINS.md")


@cli.command()
@click.argument("orders_path")
@click.option("--format", "fmt", default="auto")
def revenue(orders_path, fmt):
    """Analyse revenue decomposition."""
    orders = load_orders(orders_path, fmt=fmt)
    result = decompose_revenue(orders)
    click.echo(result.table.to_string())
    click.echo(f"\nSummary: {json.dumps(result.summary, indent=2)}")


@cli.command()
@click.argument("orders_path")
@click.option("--format", "fmt", default="auto")
@click.option("--horizon", default=12, help="LTV horizon in months")
def cohort(orders_path, fmt, horizon):
    """Run cohort, retention, and LTV analysis."""
    orders = load_orders(orders_path, fmt=fmt)
    matrix = build_cohort_matrix(orders)
    curve = compute_retention_curve(matrix)
    ltv = estimate_ltv(orders, horizon_months=horizon)
    rfm = rfm_segmentation(orders)

    click.echo("=== Retention Curve ===")
    click.echo(curve.to_string())
    click.echo(f"\n=== LTV ({horizon}m) ===")
    click.echo(f"Average: {ltv.avg_ltv:,.0f}  Median: {ltv.median_ltv:,.0f}")
    click.echo(f"\n=== RFM Segment Distribution ===")
    click.echo(rfm["segment"].value_counts().to_string())


@cli.command()
@click.argument("orders_path")
@click.option("--products", "products_path", default=None)
@click.option("--format", "fmt", default="auto")
def product(orders_path, products_path, fmt):
    """Run product analysis (ABC, cross-sell)."""
    orders = load_orders(orders_path, fmt=fmt)
    abc = abc_analysis(orders)
    click.echo("=== ABC Analysis ===")
    click.echo(abc.to_string(index=False))

    xs = cross_sell_matrix(orders)
    if len(xs):
        click.echo("\n=== Top Cross-Sell Pairs ===")
        click.echo(xs.head(10).to_string(index=False))


@cli.command()
@click.argument("inventory_path")
@click.option("--orders", "orders_path", required=True, help="Orders CSV for velocity calculation")
@click.option("--format", "fmt", default="auto")
def inventory(inventory_path, orders_path, fmt):
    """Run inventory and stockout analysis."""
    inv = load_inventory(inventory_path)
    orders = load_orders(orders_path, fmt=fmt)
    so = stockout_analysis(inv, orders)
    click.echo(f"Stockout SKUs: {len(so.stockout_skus)} ({so.stockout_rate:.1%})")
    click.echo(f"Estimated lost revenue (7-day): {so.estimated_lost_revenue:,.0f}")

    ov = overstock_analysis(inv, orders)
    click.echo(f"Overstock (>90d): {len(ov.overstock_skus)} SKUs, value: {ov.overstock_value:,.0f}")
    click.echo(f"Deadstock (>180d): {len(ov.deadstock_skus)} SKUs, value: {ov.deadstock_value:,.0f}")


@cli.command()
@click.argument("orders_path")
@click.option("--format", "fmt", default="auto")
@click.option("--output", default="./", help="Output directory")
def report(orders_path, fmt, output):
    """Generate all three Markdown reports."""
    orders = load_orders(orders_path, fmt=fmt)
    rev_kpis = compute_revenue_kpis(orders)
    cohort_kpis = compute_cohort_kpis(orders)
    checks = _build_checks(rev_kpis, cohort_kpis, orders, None, None)
    health = score_checks(checks)
    annual_revenue = rev_kpis["total_revenue"]
    generate_audit_report(health, annual_revenue, output_dir=output)
    generate_action_plan(health, annual_revenue, output_dir=output)
    generate_quick_wins(health, annual_revenue, output_dir=output)
    click.echo(f"Reports generated in {output}")


# ---------------------------------------------------------------------------
# Internal: build check results from KPIs
# ---------------------------------------------------------------------------


def _build_checks(
    rev_kpis: dict,
    cohort_kpis: dict,
    orders,
    products,
    inventory,
) -> list[CheckResult]:
    """Build a list of CheckResult from computed KPIs.

    This is a simplified implementation covering key checks.
    """
    checks: list[CheckResult] = []

    # --- Revenue checks ---
    mom = rev_kpis.get("mom_growth_latest", 0)
    checks.append(CheckResult(
        check_id="R01", category="revenue", severity="high",
        result="pass" if mom > 0 else ("warning" if mom > -0.05 else "fail"),
        message=f"MoM revenue growth: {mom:.1%}",
        current_value=mom, threshold=0.0,
    ))

    repeat_share = rev_kpis.get("repeat_revenue_share", 0)
    checks.append(CheckResult(
        check_id="R05", category="revenue", severity="critical",
        result="pass" if repeat_share >= 0.3 else ("warning" if repeat_share >= 0.2 else "fail"),
        message=f"Repeat customer revenue share: {repeat_share:.1%}",
        current_value=repeat_share, threshold=0.3,
    ))

    discount_rate = rev_kpis.get("avg_discount_rate", 0)
    checks.append(CheckResult(
        check_id="R08", category="revenue", severity="high",
        result="pass" if discount_rate < 0.15 else ("warning" if discount_rate < 0.25 else "fail"),
        message=f"Average discount rate: {discount_rate:.1%}",
        current_value=discount_rate, threshold=0.15,
    ))

    top10 = rev_kpis.get("top10_customer_share", 0)
    checks.append(CheckResult(
        check_id="R07", category="revenue", severity="medium",
        result="pass" if top10 < 0.6 else ("warning" if top10 < 0.8 else "fail"),
        message=f"Top 10% customer revenue share: {top10:.1%}",
        current_value=top10, threshold=0.6,
    ))

    daily_cv = rev_kpis.get("daily_revenue_cv", 0)
    checks.append(CheckResult(
        check_id="R13", category="revenue", severity="medium",
        result="pass" if daily_cv < 0.5 else ("warning" if daily_cv < 0.8 else "fail"),
        message=f"Daily revenue coefficient of variation: {daily_cv:.2f}",
        current_value=daily_cv, threshold=0.5,
    ))

    # --- Retention checks ---
    f2 = cohort_kpis.get("f2_rate", 0)
    checks.append(CheckResult(
        check_id="C01", category="retention", severity="critical",
        result="pass" if f2 >= 0.25 else ("warning" if f2 >= 0.15 else "fail"),
        message=f"F2 conversion rate: {f2:.1%}",
        current_value=f2, threshold=0.25,
    ))

    avg_interval = cohort_kpis.get("avg_purchase_interval_days", float("nan"))
    checks.append(CheckResult(
        check_id="C11", category="retention", severity="high",
        result="pass" if avg_interval < 60 else ("warning" if avg_interval < 90 else "fail"),
        message=f"Avg days to 2nd purchase: {avg_interval:.0f}" if avg_interval == avg_interval else "Insufficient data",
        current_value=avg_interval, threshold=60,
    ))

    # --- Inventory checks (if data available) ---
    if inventory is not None:
        from ecom_analytics.metrics import compute_inventory_kpis as inv_kpis_fn
        inv_kpis = inv_kpis_fn(inventory, orders)
        so_rate = inv_kpis.get("stockout_rate", 0)
        checks.append(CheckResult(
            check_id="O03", category="inventory", severity="critical",
            result="pass" if so_rate < 0.05 else ("warning" if so_rate < 0.1 else "fail"),
            message=f"Stockout SKU rate: {so_rate:.1%}",
            current_value=so_rate, threshold=0.05,
        ))

    # --- Pricing checks ---
    if "discount" in orders.columns:
        from ecom_analytics.pricing import discount_dependency as dd_fn
        dd = dd_fn(orders)
        checks.append(CheckResult(
            check_id="PR01", category="pricing", severity="high",
            result="pass" if dd.avg_discount_rate < 0.15 else ("warning" if dd.avg_discount_rate < 0.25 else "fail"),
            message=f"Average discount rate: {dd.avg_discount_rate:.1%}",
            current_value=dd.avg_discount_rate, threshold=0.15,
        ))
        checks.append(CheckResult(
            check_id="PR02", category="pricing", severity="high",
            result="pass" if dd.discounted_order_ratio < 0.4 else ("warning" if dd.discounted_order_ratio < 0.6 else "fail"),
            message=f"Discounted order ratio: {dd.discounted_order_ratio:.1%}",
            current_value=dd.discounted_order_ratio, threshold=0.4,
        ))

    return checks


def _build_checks_from_analytics(
    rev_kpis: dict,
    funnel_kpis: dict,
    product_kpis: dict,
    retention_kpis: dict,
) -> list[CheckResult]:
    """Build check results from Shopify Analytics aggregated KPIs."""
    checks: list[CheckResult] = []

    # --- Revenue checks ---
    mom = rev_kpis.get("mom_growth_latest", 0)
    checks.append(CheckResult(
        check_id="R01", category="revenue", severity="high",
        result="pass" if mom > 0 else ("warning" if mom > -0.05 else "fail"),
        message=f"MoM revenue growth: {mom:.1%}",
        current_value=mom, threshold=0.0,
    ))

    repeat_share = rev_kpis.get("repeat_revenue_share", 0)
    checks.append(CheckResult(
        check_id="R05", category="revenue", severity="critical",
        result="pass" if repeat_share >= 0.3 else ("warning" if repeat_share >= 0.2 else "fail"),
        message=f"Repeat customer revenue share: {repeat_share:.1%}",
        current_value=repeat_share, threshold=0.3,
    ))

    discount_rate = rev_kpis.get("avg_discount_rate", 0)
    checks.append(CheckResult(
        check_id="R08", category="revenue", severity="high",
        result="pass" if discount_rate < 0.15 else ("warning" if discount_rate < 0.25 else "fail"),
        message=f"Average discount rate: {discount_rate:.1%}",
        current_value=discount_rate, threshold=0.15,
    ))

    return_rate = rev_kpis.get("return_rate", 0)
    checks.append(CheckResult(
        check_id="R10", category="revenue", severity="high",
        result="pass" if return_rate < 0.1 else ("warning" if return_rate < 0.2 else "fail"),
        message=f"Return rate: {return_rate:.1%}",
        current_value=return_rate, threshold=0.1,
    ))

    # Gross margin check
    gross_margin = rev_kpis.get("gross_margin", 0)
    if gross_margin > 0:
        checks.append(CheckResult(
            check_id="R14", category="revenue", severity="critical",
            result="pass" if gross_margin >= 0.5 else ("warning" if gross_margin >= 0.3 else "fail"),
            message=f"Gross margin: {gross_margin:.1%}",
            current_value=gross_margin, threshold=0.5,
        ))

    # --- Conversion checks ---
    if funnel_kpis:
        overall_cvr = funnel_kpis.get("overall_cvr", 0)
        checks.append(CheckResult(
            check_id="CV01", category="conversion", severity="critical",
            result="pass" if overall_cvr >= 0.02 else ("warning" if overall_cvr >= 0.01 else "fail"),
            message=f"Overall conversion rate: {overall_cvr:.2%}",
            current_value=overall_cvr, threshold=0.02,
        ))

        cart_rate = funnel_kpis.get("cart_addition_rate", 0)
        checks.append(CheckResult(
            check_id="CV03", category="conversion", severity="high",
            result="pass" if cart_rate >= 0.05 else ("warning" if cart_rate >= 0.03 else "fail"),
            message=f"Cart addition rate: {cart_rate:.2%}",
            current_value=cart_rate, threshold=0.05,
        ))

        cart_abandon = funnel_kpis.get("cart_abandonment_rate", 0)
        checks.append(CheckResult(
            check_id="CV05", category="conversion", severity="high",
            result="pass" if cart_abandon < 0.6 else ("warning" if cart_abandon < 0.75 else "fail"),
            message=f"Cart abandonment rate: {cart_abandon:.1%}",
            current_value=cart_abandon, threshold=0.6,
        ))

        checkout_abandon = funnel_kpis.get("checkout_abandonment_rate", 0)
        checks.append(CheckResult(
            check_id="CV06", category="conversion", severity="high",
            result="pass" if checkout_abandon < 0.3 else ("warning" if checkout_abandon < 0.5 else "fail"),
            message=f"Checkout abandonment rate: {checkout_abandon:.1%}",
            current_value=checkout_abandon, threshold=0.3,
        ))

    # --- Product checks ---
    if product_kpis:
        top20_share = product_kpis.get("top20_sku_revenue_share", 0)
        checks.append(CheckResult(
            check_id="P01", category="product", severity="medium",
            result="pass" if top20_share < 0.8 else ("warning" if top20_share < 0.9 else "fail"),
            message=f"Top 20% SKU revenue concentration: {top20_share:.1%}",
            current_value=top20_share, threshold=0.8,
        ))

        zero_skus = product_kpis.get("zero_sales_skus", 0)
        total_skus = product_kpis.get("total_skus", 1)
        zero_pct = zero_skus / total_skus if total_skus else 0
        checks.append(CheckResult(
            check_id="P10", category="product", severity="medium",
            result="pass" if zero_pct < 0.1 else ("warning" if zero_pct < 0.2 else "fail"),
            message=f"Zero/negative sales SKUs: {zero_skus} ({zero_pct:.1%} of {total_skus})",
            current_value=zero_pct, threshold=0.1,
        ))

    # --- Retention checks ---
    if retention_kpis:
        returning_ratio = retention_kpis.get("returning_customer_ratio", 0)
        checks.append(CheckResult(
            check_id="C01", category="retention", severity="critical",
            result="pass" if returning_ratio >= 0.25 else ("warning" if returning_ratio >= 0.15 else "fail"),
            message=f"Returning customer ratio: {returning_ratio:.1%}",
            current_value=returning_ratio, threshold=0.25,
        ))

        avg_rev_per_returning = retention_kpis.get("avg_rev_per_returning", 0)
        avg_rev_per_new = retention_kpis.get("avg_rev_per_new", 0)
        if avg_rev_per_new > 0:
            ltv_multiplier = avg_rev_per_returning / avg_rev_per_new
            checks.append(CheckResult(
                check_id="C05", category="retention", severity="high",
                result="pass" if ltv_multiplier >= 2.0 else ("warning" if ltv_multiplier >= 1.5 else "fail"),
                message=f"Returning/New customer value ratio: {ltv_multiplier:.1f}x",
                current_value=ltv_multiplier, threshold=2.0,
            ))

    # --- Pricing checks from revenue data ---
    discount_rate = rev_kpis.get("avg_discount_rate", 0)
    checks.append(CheckResult(
        check_id="PR01", category="pricing", severity="high",
        result="pass" if discount_rate < 0.15 else ("warning" if discount_rate < 0.25 else "fail"),
        message=f"Average discount rate: {discount_rate:.1%}",
        current_value=discount_rate, threshold=0.15,
    ))

    return checks


if __name__ == "__main__":
    cli()
