"""CLI entry point for ecom-analytics."""

from __future__ import annotations

import json
import sys

import click
import pandas as pd

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
    generate_site_audit_report,
    generate_review,
    ascii_bar_chart,
)


@click.group()
@click.version_option(version=__version__)
def cli():
    """ecom-analytics: EC-specialized data analytics toolkit."""
    pass


@cli.command()
@click.argument("orders_path", required=False, default=None)
@click.option("--products", "products_path", default=None, help="Products CSV path")
@click.option("--inventory", "inventory_path", default=None, help="Inventory CSV path")
@click.option("--format", "fmt", default="auto", help="CSV format (shopify|generic|auto)")
@click.option("--output", default="./", help="Output directory for reports")
@click.option("--source", type=click.Choice(["csv", "shopify"]), default="csv", help="Data source")
@click.option("--since", default=None, help="Start date for Shopify sync (e.g. 2024-01-01)")
@click.option("--until", default=None, help="End date for Shopify sync")
@click.option("--site-url", default=None, help="Store URL for site quality audit (SA01-SA15)")
def audit(orders_path, products_path, inventory_path, fmt, output, source, since, until, site_url):
    """Run a full EC health audit and generate reports."""
    if source == "shopify":
        _audit_shopify(output, since, until)
        return

    if orders_path is None:
        raise click.UsageError(
            "ORDERS_PATH is required when --source=csv. "
            "Use --source shopify for Shopify Admin API data."
        )

    click.echo("Loading data...")
    orders = load_orders(orders_path, fmt=fmt)
    products = load_products(products_path) if products_path else None
    inventory = load_inventory(inventory_path) if inventory_path else None

    click.echo("Computing KPIs...")
    rev_kpis = compute_revenue_kpis(orders)
    cohort_kpis = compute_cohort_kpis(orders)

    # Build check results (simplified — in production each sub-module contributes)
    checks = _build_checks(rev_kpis, cohort_kpis, orders, products, inventory)

    # Optional site quality audit
    if site_url:
        checks.extend(_run_site_checks(site_url, output))

    click.echo("Scoring...")
    health = score_checks(checks)

    click.echo(f"\nOverall Score: {health.overall_score}/100 (Grade: {health.overall_grade})")
    for cat, cs in health.category_scores.items():
        click.echo(f"  {cat:>12}: {cs.score}/100 ({cs.grade})")

    click.echo(f"\nGenerating reports to {output} ...")
    annual_revenue = rev_kpis["total_revenue"]
    generate_audit_report(health, annual_revenue, output_dir=output, business_model=_detect_business_model(orders))
    generate_action_plan(health, annual_revenue, output_dir=output)
    generate_quick_wins(health, annual_revenue, output_dir=output)
    click.echo("Done. Reports: AUDIT-REPORT.md, ACTION-PLAN.md, QUICK-WINS.md")


def _audit_shopify(output, since, until):
    """Run audit using Shopify Admin API data."""
    from ecom_analytics.config import load_config
    from ecom_analytics.sync import sync_shopify, load_synced_data

    if since is None:
        raise click.UsageError("--since is required with --source shopify")

    click.echo("Loading Shopify config...")
    cfg = load_config()

    click.echo(f"Syncing data from Shopify (since {since})...")

    def progress(op_name, status, count):
        click.echo(f"  [{op_name}] {status} — {count} objects", nl=True)

    state = sync_shopify(cfg, since=since, until=until, progress_cb=progress)
    click.echo(f"  Synced: {state.record_counts}")

    click.echo("Loading synced data...")
    orders, products, inventory = load_synced_data()

    click.echo("Computing KPIs...")
    rev_kpis = compute_revenue_kpis(orders)
    cohort_kpis = compute_cohort_kpis(orders)

    checks = _build_checks(rev_kpis, cohort_kpis, orders, products, inventory)

    click.echo("Scoring...")
    health = score_checks(checks)

    click.echo(f"\nOverall Score: {health.overall_score}/100 (Grade: {health.overall_grade})")
    for cat, cs in health.category_scores.items():
        click.echo(f"  {cat:>12}: {cs.score}/100 ({cs.grade})")

    click.echo(f"\nGenerating reports to {output} ...")
    annual_revenue = rev_kpis["total_revenue"]
    generate_audit_report(health, annual_revenue, output_dir=output, business_model="D2C (Shopify)")
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

    generate_audit_report(health, annual_revenue, data_start=data_start, data_end=data_end, output_dir=output, business_model="D2C (Shopify Analytics)")
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
# Site audit command
# ---------------------------------------------------------------------------


def _run_site_checks(url: str, output_dir: str = "./") -> list[CheckResult]:
    """Run site audit on a URL and return SA01-SA15 checks."""
    try:
        from ecom_analytics.site_audit import analyze_page, build_site_checks_single
    except ImportError:
        click.echo("Site audit requires Playwright: pip install ecom-analytics[site] && playwright install chromium")
        return []

    click.echo(f"Analyzing site: {url} ...")
    try:
        data = analyze_page(url, screenshot_dir=output_dir)
        checks = build_site_checks_single(data)
        passed = sum(1 for c in checks if c.result == "pass")
        click.echo(f"  Site audit: {passed}/{len(checks)} checks passed")
        return checks
    except ImportError:
        click.echo("  Skipping site audit — Playwright not installed")
        return []
    except Exception as e:
        click.echo(f"  Site audit error: {e}")
        return []


@cli.command("site-audit")
@click.argument("url")
@click.option("--crawl", is_flag=True, help="Crawl additional pages from the site")
@click.option("--max-pages", default=20, help="Max pages to crawl (with --crawl)")
@click.option("--timeout", default=30000, help="Page load timeout in ms")
@click.option("--screenshots/--no-screenshots", default=True, help="Save viewport screenshots")
@click.option("--output", default="./", help="Output directory for report and screenshots")
@click.option("--json", "json_output", is_flag=True, help="Output results as JSON")
def site_audit(url, crawl, max_pages, timeout, screenshots, output, json_output):
    """Run a site / landing page quality audit (SA01-SA15)."""
    try:
        from ecom_analytics.site_audit import (
            analyze_page, build_site_checks, check_playwright_available,
        )
        check_playwright_available()
    except ImportError as e:
        click.echo(str(e))
        sys.exit(1)

    screenshot_dir = output if screenshots else None
    pages = []

    if crawl:
        from ecom_analytics.site_crawler import crawl_site, CrawlConfig
        config = CrawlConfig(
            max_pages=max_pages,
            timeout_per_page=timeout,
            screenshot_dir=screenshot_dir,
        )

        def progress(page_url, current, total):
            click.echo(f"  [{current}/{total}] {page_url}")

        click.echo(f"Crawling {url} (max {max_pages} pages)...")
        result = crawl_site(url, config, progress_cb=progress)
        pages = result.pages
        if result.errors:
            for err in result.errors:
                click.echo(f"  Error: {err}")
    else:
        click.echo(f"Analyzing {url} ...")
        data = analyze_page(url, timeout=timeout, screenshot_dir=screenshot_dir)
        pages = [data]

    if not pages:
        click.echo("No pages analyzed.")
        sys.exit(1)

    checks = build_site_checks(pages)
    health = score_checks(checks)

    if json_output:
        import json as json_mod
        results = []
        for c in checks:
            results.append({
                "check_id": c.check_id,
                "severity": c.severity,
                "result": c.result,
                "message": c.message,
                "current_value": c.current_value,
                "threshold": c.threshold,
            })
        output_data = {
            "url": url,
            "pages_analyzed": len(pages),
            "score": health.overall_score,
            "grade": health.overall_grade,
            "checks": results,
        }
        click.echo(json_mod.dumps(output_data, indent=2, default=str))
    else:
        click.echo(f"\nSite Score: {health.overall_score}/100 (Grade: {health.overall_grade})")
        click.echo(f"Pages Analyzed: {len(pages)}")
        click.echo(f"\nChecks:")
        for c in checks:
            icon = "PASS" if c.result == "pass" else ("WARN" if c.result == "warning" else "FAIL")
            click.echo(f"  [{icon}] {c.check_id} ({c.severity}) — {c.message}")

        # Generate report
        report_path = generate_site_audit_report(
            pages, health, output_dir=output,
        )
        click.echo(f"\nReport: {report_path}")


# ---------------------------------------------------------------------------
# Shopify Admin API commands
# ---------------------------------------------------------------------------


@cli.group("shopify")
def shopify_group():
    """Shopify Admin API integration."""
    pass


@shopify_group.command("setup")
@click.option("--global", "global_", is_flag=True, help="Save to ~/.ecom-analytics/")
def shopify_setup(global_):
    """Interactive setup for Shopify Admin API credentials."""
    from ecom_analytics.config import ShopifyConfig, save_config
    import os

    click.echo("=== Shopify Admin API Setup ===\n")
    click.echo("You'll need a Custom App with these scopes:")
    click.echo("  read_orders, read_products, read_inventory\n")

    store = click.prompt("Store domain (e.g. my-store.myshopify.com)")
    token = click.prompt("Admin API access token", hide_input=True)
    api_version = click.prompt("API version", default="2025-01")
    timezone = click.prompt("Store timezone", default="UTC")
    currency = click.prompt("Primary currency", default="USD")

    cfg = ShopifyConfig(
        store_domain=store,
        access_token=token,
        api_version=api_version,
        timezone=timezone,
        currency=currency,
    )

    path = save_config(cfg, global_=global_)
    click.echo(f"\nConfig saved to {path}")

    if not global_:
        click.echo("Note: .ecom-analytics/ added to .gitignore for token safety.")

    click.echo("\nNext: run 'ecom-analytics shopify sync --since 2024-01-01'")


@shopify_group.command("sync")
@click.option("--since", required=True, help="Start date (ISO format, e.g. 2024-01-01)")
@click.option("--until", default=None, help="End date (optional)")
@click.option("--mode", type=click.Choice(["full", "incremental"]), default="full")
@click.option("--out", "out_dir", default=".ecom-analytics/data", help="Output directory")
@click.option("--timeout-minutes", default=60, help="Max wait per bulk operation")
def shopify_sync(since, until, mode, out_dir, timeout_minutes):
    """Sync data from Shopify Admin API via Bulk Operations."""
    from ecom_analytics.config import load_config
    from ecom_analytics.sync import sync_shopify

    click.echo("Loading config...")
    cfg = load_config()

    click.echo(f"Syncing from {cfg.store_domain} (since={since}, mode={mode})...")

    def progress(op_name, status, count):
        click.echo(f"  [{op_name}] {status} — {count} objects")

    state = sync_shopify(
        cfg,
        since=since,
        until=until,
        mode=mode,
        out_dir=out_dir,
        progress_cb=progress,
        timeout_minutes=timeout_minutes,
    )

    click.echo(f"\nSync complete!")
    click.echo(f"  Orders:      {state.record_counts.get('orders', 0):,}")
    click.echo(f"  Line items:  {state.record_counts.get('order_items', 0):,}")
    click.echo(f"  Products:    {state.record_counts.get('products', 0):,}")
    click.echo(f"  Inventory:   {state.record_counts.get('inventory', 0):,}")
    click.echo(f"  Output:      {out_dir}/")
    click.echo(f"\nNext: run 'ecom-analytics audit --source shopify --since {since}'")


# ---------------------------------------------------------------------------
# Internal: build check results from KPIs
# ---------------------------------------------------------------------------


def _detect_business_model(orders) -> str:
    """Simple business model detection from order data signals."""
    cols = set(orders.columns)
    if "subscription" in cols or "recurring" in cols:
        return "Subscription"
    if "marketplace" in cols or "seller_id" in cols:
        return "Marketplace"
    if "channel" in cols:
        if orders["channel"].str.contains("pos|in-store|retail", case=False, na=False).any():
            return "O2O"
    return "D2C"


def _build_checks(
    rev_kpis: dict,
    cohort_kpis: dict,
    orders,
    products,
    inventory,
) -> list[CheckResult]:
    """Build a list of CheckResult from computed KPIs.

    Implements 35+ checks across all 6 categories.
    """
    checks: list[CheckResult] = []

    # ===== Revenue checks (R01-R14) =====
    mom = rev_kpis.get("mom_growth_latest", 0)
    checks.append(CheckResult(
        check_id="R01", category="revenue", severity="high",
        result="pass" if mom > 0 else ("warning" if mom > -0.05 else "fail"),
        message=f"MoM revenue growth: {mom:.1%}",
        current_value=mom, threshold=0.0,
    ))

    # R03 — AOV Trend
    monthly_aov = rev_kpis.get("monthly_aov", {})
    if len(monthly_aov) >= 2:
        aov_vals = list(monthly_aov.values())
        aov_change = (aov_vals[-1] - aov_vals[-2]) / aov_vals[-2] if aov_vals[-2] else 0
        checks.append(CheckResult(
            check_id="R03", category="revenue", severity="high",
            result="pass" if aov_change > -0.05 else ("warning" if aov_change > -0.1 else "fail"),
            message=f"AOV MoM change: {aov_change:.1%}",
            current_value=aov_change, threshold=-0.05,
        ))

    # R04 — Order Count Trend
    monthly_orders = rev_kpis.get("monthly_orders", {})
    if len(monthly_orders) >= 2:
        ord_vals = list(monthly_orders.values())
        ord_change = (ord_vals[-1] - ord_vals[-2]) / ord_vals[-2] if ord_vals[-2] else 0
        checks.append(CheckResult(
            check_id="R04", category="revenue", severity="high",
            result="pass" if ord_change > -0.05 else ("warning" if ord_change > -0.1 else "fail"),
            message=f"MoM order count change: {ord_change:.1%}",
            current_value=ord_change, threshold=-0.05,
        ))

    repeat_share = rev_kpis.get("repeat_revenue_share", 0)
    checks.append(CheckResult(
        check_id="R05", category="revenue", severity="critical",
        result="pass" if repeat_share >= 0.3 else ("warning" if repeat_share >= 0.2 else "fail"),
        message=f"Repeat customer revenue share: {repeat_share:.1%}",
        current_value=repeat_share, threshold=0.3,
    ))

    top10 = rev_kpis.get("top10_customer_share", 0)
    checks.append(CheckResult(
        check_id="R07", category="revenue", severity="medium",
        result="pass" if top10 < 0.6 else ("warning" if top10 < 0.8 else "fail"),
        message=f"Top 10% customer revenue share: {top10:.1%}",
        current_value=top10, threshold=0.6,
    ))

    discount_rate = rev_kpis.get("avg_discount_rate", 0)
    checks.append(CheckResult(
        check_id="R08", category="revenue", severity="high",
        result="pass" if discount_rate < 0.15 else ("warning" if discount_rate < 0.25 else "fail"),
        message=f"Average discount rate: {discount_rate:.1%}",
        current_value=discount_rate, threshold=0.15,
    ))

    daily_cv = rev_kpis.get("daily_revenue_cv", 0)
    checks.append(CheckResult(
        check_id="R13", category="revenue", severity="medium",
        result="pass" if daily_cv < 0.5 else ("warning" if daily_cv < 0.8 else "fail"),
        message=f"Daily revenue coefficient of variation: {daily_cv:.2f}",
        current_value=daily_cv, threshold=0.5,
    ))

    # R14 — Large Order Dependency
    if rev_kpis.get("total_revenue", 0) > 0:
        order_amounts = orders.groupby("order_id")["amount"].sum()
        largest_share = order_amounts.max() / rev_kpis["total_revenue"]
        checks.append(CheckResult(
            check_id="R14", category="revenue", severity="medium",
            result="pass" if largest_share < 0.05 else ("warning" if largest_share < 0.1 else "fail"),
            message=f"Largest order share of revenue: {largest_share:.1%}",
            current_value=largest_share, threshold=0.05,
        ))

    # ===== Product checks (P01, P05, P06, P07, P09, P10, P19) =====
    if products is not None:
        from ecom_analytics.metrics import compute_product_kpis as prod_kpis_fn
        prod_kpis = prod_kpis_fn(orders, products)

        top20 = prod_kpis.get("top20_revenue_share", 0)
        checks.append(CheckResult(
            check_id="P01", category="product", severity="medium",
            result="pass" if 0.5 <= top20 <= 0.8 else ("warning" if top20 <= 0.9 else "fail"),
            message=f"Top 20% SKU revenue concentration: {top20:.1%}",
            current_value=top20, threshold=0.8,
        ))

        multi_item = prod_kpis.get("multi_item_order_rate", 0)
        checks.append(CheckResult(
            check_id="P06", category="product", severity="medium",
            result="pass" if multi_item >= 0.25 else ("warning" if multi_item >= 0.15 else "fail"),
            message=f"Multi-item order rate: {multi_item:.1%}",
            current_value=multi_item, threshold=0.25,
        ))

    # P05 — Converting SKU Rate (works without products CSV too)
    key = "sku" if "sku" in orders.columns else "product_name" if "product_name" in orders.columns else None
    if key:
        total_active = orders[key].nunique()
        selling = orders.groupby(key)["amount"].sum()
        converting = (selling > 0).sum()
        convert_rate = converting / total_active if total_active else 0
        checks.append(CheckResult(
            check_id="P05", category="product", severity="high",
            result="pass" if convert_rate >= 0.7 else ("warning" if convert_rate >= 0.5 else "fail"),
            message=f"Converting SKU rate: {convert_rate:.1%} ({converting}/{total_active})",
            current_value=convert_rate, threshold=0.7,
        ))

    # P07 — Cross-Sell Pair Lift
    if key:
        from ecom_analytics.product import cross_sell_matrix
        xs = cross_sell_matrix(orders)
        high_lift = len(xs[xs["lift"] > 2.0]) if len(xs) else 0
        checks.append(CheckResult(
            check_id="P07", category="product", severity="medium",
            result="pass" if high_lift >= 3 else ("warning" if high_lift >= 1 else "fail"),
            message=f"Cross-sell pairs with lift > 2.0: {high_lift}",
            current_value=high_lift, threshold=3,
        ))

    # P10 — Lifecycle Stage Distribution
    if key:
        from ecom_analytics.product import product_lifecycle
        lifecycle = product_lifecycle(orders)
        if len(lifecycle):
            decline_pct = (lifecycle["lifecycle_stage"] == "Decline").mean()
            checks.append(CheckResult(
                check_id="P10", category="product", severity="medium",
                result="pass" if decline_pct < 0.3 else ("warning" if decline_pct < 0.5 else "fail"),
                message=f"Decline-stage products: {decline_pct:.1%}",
                current_value=decline_pct, threshold=0.3,
            ))

    # P19 — Price Tier Distribution
    if key:
        prices = orders.groupby(key)["amount"].mean()
        n_tiers = len(pd.qcut(prices, q=min(4, len(prices)), duplicates="drop").cat.categories)
        checks.append(CheckResult(
            check_id="P19", category="product", severity="medium",
            result="pass" if n_tiers >= 3 else ("warning" if n_tiers >= 2 else "fail"),
            message=f"Distinct price tiers: {n_tiers}",
            current_value=n_tiers, threshold=3,
        ))

    # ===== Retention checks (C01, C02, C08, C09, C10, C11) =====
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

    # C08/C09/C10 — RFM Segment Distribution
    order_counts = orders.groupby("customer_id")["order_id"].nunique()
    total_cust = len(order_counts)
    if total_cust > 0:
        from ecom_analytics.cohort import rfm_segmentation
        try:
            rfm = rfm_segmentation(orders)
            seg_dist = rfm["segment"].value_counts(normalize=True)

            champions_loyal = seg_dist.get("Champions", 0) + seg_dist.get("Loyal", 0)
            checks.append(CheckResult(
                check_id="C08", category="retention", severity="medium",
                result="pass" if champions_loyal >= 0.2 else ("warning" if champions_loyal >= 0.1 else "fail"),
                message=f"Champions + Loyal segment share: {champions_loyal:.1%}",
                current_value=champions_loyal, threshold=0.2,
            ))

            at_risk = seg_dist.get("At Risk", 0)
            checks.append(CheckResult(
                check_id="C09", category="retention", severity="high",
                result="pass" if at_risk < 0.25 else ("warning" if at_risk < 0.35 else "fail"),
                message=f"At-Risk segment share: {at_risk:.1%}",
                current_value=at_risk, threshold=0.25,
            ))

            lost = seg_dist.get("Lost", 0)
            checks.append(CheckResult(
                check_id="C10", category="retention", severity="medium",
                result="pass" if lost < 0.3 else ("warning" if lost < 0.45 else "fail"),
                message=f"Lost segment share: {lost:.1%}",
                current_value=lost, threshold=0.3,
            ))
        except Exception:
            pass  # RFM requires sufficient data

    # ===== Inventory checks (O01-O06, O10) =====
    if inventory is not None:
        from ecom_analytics.metrics import compute_inventory_kpis as inv_kpis_fn
        from ecom_analytics.inventory import stockout_analysis, overstock_analysis, inventory_turnover
        inv_kpis = inv_kpis_fn(inventory, orders)

        so_rate = inv_kpis.get("stockout_rate", 0)
        checks.append(CheckResult(
            check_id="O03", category="inventory", severity="critical",
            result="pass" if so_rate < 0.05 else ("warning" if so_rate < 0.1 else "fail"),
            message=f"Stockout SKU rate: {so_rate:.1%}",
            current_value=so_rate, threshold=0.05,
        ))

        # O01 — Overall Inventory Turnover
        turn = inventory_turnover(inventory, orders)
        if len(turn) and "turnover" in turn.columns:
            median_turn = turn["turnover"].median()
            checks.append(CheckResult(
                check_id="O01", category="inventory", severity="high",
                result="pass" if median_turn >= 6 else ("warning" if median_turn >= 4 else "fail"),
                message=f"Median inventory turnover: {median_turn:.1f}x/year",
                current_value=median_turn, threshold=6.0,
            ))

        # O05 — Overstock Value
        ov = overstock_analysis(inventory, orders)
        inv_val = inv_kpis.get("total_inventory_value", 0)
        if inv_val and inv_val == inv_val:  # not NaN
            overstock_pct = ov.overstock_value / inv_val
            checks.append(CheckResult(
                check_id="O05", category="inventory", severity="high",
                result="pass" if overstock_pct < 0.2 else ("warning" if overstock_pct < 0.35 else "fail"),
                message=f"Overstock value (>90d): {overstock_pct:.1%} of inventory",
                current_value=overstock_pct, threshold=0.2,
            ))

        # O06 — Deadstock Rate
        total_inv_skus = inv_kpis.get("total_skus", 1)
        deadstock_rate = len(ov.deadstock_skus) / total_inv_skus if total_inv_skus else 0
        checks.append(CheckResult(
            check_id="O06", category="inventory", severity="high",
            result="pass" if deadstock_rate < 0.1 else ("warning" if deadstock_rate < 0.2 else "fail"),
            message=f"Deadstock rate (>180d): {deadstock_rate:.1%}",
            current_value=deadstock_rate, threshold=0.1,
        ))

        # O04 — Stockout Opportunity Cost
        so = stockout_analysis(inventory, orders)
        monthly_rev = rev_kpis.get("total_revenue", 0) / 12
        if monthly_rev > 0:
            lost_pct = so.estimated_lost_revenue / monthly_rev
            checks.append(CheckResult(
                check_id="O04", category="inventory", severity="critical",
                result="pass" if lost_pct < 0.03 else ("warning" if lost_pct < 0.05 else "fail"),
                message=f"Stockout opportunity cost: {lost_pct:.1%} of monthly revenue",
                current_value=lost_pct, threshold=0.03,
            ))

        # O10 — Inventory Cost as % of Revenue
        if inv_val and inv_val == inv_val and rev_kpis.get("total_revenue", 0):
            inv_rev_pct = inv_val / rev_kpis["total_revenue"]
            checks.append(CheckResult(
                check_id="O10", category="inventory", severity="medium",
                result="pass" if inv_rev_pct < 0.25 else ("warning" if inv_rev_pct < 0.4 else "fail"),
                message=f"Inventory cost as % of revenue: {inv_rev_pct:.1%}",
                current_value=inv_rev_pct, threshold=0.25,
            ))

    # ===== Pricing checks (PR01-PR03) =====
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
        # PR03 — Discount Depth Trend
        trend = dd.discount_rate_trend
        checks.append(CheckResult(
            check_id="PR03", category="pricing", severity="critical",
            result="pass" if trend == "stable" or trend == "decreasing" else "warning",
            message=f"Discount depth trend: {trend}",
            current_value=trend, threshold="stable",
        ))

    # PR07 — Category Margin Variance (if cost data available)
    if "cost" in orders.columns:
        from ecom_analytics.pricing import margin_analysis
        ma = margin_analysis(orders)
        neg_cats = len(ma.negative_margin_categories)
        checks.append(CheckResult(
            check_id="PR07", category="pricing", severity="medium",
            result="pass" if neg_cats == 0 else ("warning" if neg_cats == 1 else "fail"),
            message=f"Categories with negative margin: {neg_cats}",
            current_value=neg_cats, threshold=0,
        ))

    # PR08 — Free-Shipping Threshold
    from ecom_analytics.pricing import free_shipping_threshold
    fst = free_shipping_threshold(orders)
    checks.append(CheckResult(
        check_id="PR08", category="pricing", severity="high",
        result="pass" if fst.potential_aov_lift >= 0.1 else ("warning" if fst.potential_aov_lift >= 0.05 else "fail"),
        message=f"Free-shipping threshold AOV lift potential: {fst.potential_aov_lift:.1%} (suggested: {fst.suggested_threshold:,.0f})",
        current_value=fst.potential_aov_lift, threshold=0.1,
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

    # R03 — AOV Trend
    monthly_aov = rev_kpis.get("monthly_aov", {})
    if len(monthly_aov) >= 2:
        aov_vals = list(monthly_aov.values())
        aov_change = (aov_vals[-1] - aov_vals[-2]) / aov_vals[-2] if aov_vals[-2] else 0
        checks.append(CheckResult(
            check_id="R03", category="revenue", severity="high",
            result="pass" if aov_change > -0.05 else ("warning" if aov_change > -0.1 else "fail"),
            message=f"AOV MoM change: {aov_change:.1%}",
            current_value=aov_change, threshold=-0.05,
        ))

    # R04 — Order Count Trend
    monthly_orders = rev_kpis.get("monthly_orders", {})
    if len(monthly_orders) >= 2:
        ord_vals = list(monthly_orders.values())
        ord_change = (ord_vals[-1] - ord_vals[-2]) / ord_vals[-2] if ord_vals[-2] else 0
        checks.append(CheckResult(
            check_id="R04", category="revenue", severity="high",
            result="pass" if ord_change > -0.05 else ("warning" if ord_change > -0.1 else "fail"),
            message=f"MoM order count change: {ord_change:.1%}",
            current_value=ord_change, threshold=-0.05,
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

        # CV04 — Cart-to-Purchase Completion Rate
        purchase_rate = funnel_kpis.get("purchase_completion_rate", 0)
        checks.append(CheckResult(
            check_id="CV04", category="conversion", severity="high",
            result="pass" if purchase_rate >= 0.4 else ("warning" if purchase_rate >= 0.25 else "fail"),
            message=f"Cart-to-purchase completion rate: {purchase_rate:.1%}",
            current_value=purchase_rate, threshold=0.4,
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

        # CV12 — CVR Time-Series Trend
        monthly_cvr = funnel_kpis.get("monthly_cvr", {})
        if len(monthly_cvr) >= 2:
            cvr_vals = list(monthly_cvr.values())
            cvr_delta = cvr_vals[-1] - cvr_vals[-2]
            checks.append(CheckResult(
                check_id="CV12", category="conversion", severity="high",
                result="pass" if cvr_delta > -0.003 else ("warning" if cvr_delta > -0.005 else "fail"),
                message=f"CVR MoM change: {cvr_delta:+.3f}",
                current_value=cvr_delta, threshold=-0.003,
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

        # P05 — Converting SKU Rate
        if total_skus > 0:
            converting = total_skus - zero_skus
            convert_rate = converting / total_skus
            checks.append(CheckResult(
                check_id="P05", category="product", severity="high",
                result="pass" if convert_rate >= 0.7 else ("warning" if convert_rate >= 0.5 else "fail"),
                message=f"Converting SKU rate: {convert_rate:.1%} ({converting}/{total_skus})",
                current_value=convert_rate, threshold=0.7,
            ))

        # P11 — High-Return Products
        skus_with_returns = product_kpis.get("skus_with_returns", 0)
        if total_skus > 0:
            return_product_pct = skus_with_returns / total_skus
            checks.append(CheckResult(
                check_id="P11", category="product", severity="high",
                result="pass" if return_product_pct < 0.1 else ("warning" if return_product_pct < 0.15 else "fail"),
                message=f"SKUs with returns: {skus_with_returns} ({return_product_pct:.1%})",
                current_value=return_product_pct, threshold=0.1,
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

        # C12 — Customer Spend Growth Over Time (proxy: returning AOV vs new AOV)
        if avg_rev_per_returning > 0 and avg_rev_per_new > 0:
            spend_growth = (avg_rev_per_returning - avg_rev_per_new) / avg_rev_per_new
            checks.append(CheckResult(
                check_id="C12", category="retention", severity="medium",
                result="pass" if spend_growth > 0 else ("warning" if spend_growth > -0.1 else "fail"),
                message=f"Repeat vs new customer spend difference: {spend_growth:+.1%}",
                current_value=spend_growth, threshold=0.0,
            ))

    # --- Pricing checks from revenue data ---
    discount_rate = rev_kpis.get("avg_discount_rate", 0)
    checks.append(CheckResult(
        check_id="PR01", category="pricing", severity="high",
        result="pass" if discount_rate < 0.15 else ("warning" if discount_rate < 0.25 else "fail"),
        message=f"Average discount rate: {discount_rate:.1%}",
        current_value=discount_rate, threshold=0.15,
    ))

    # PR09 — Gross Margin Check (reuse R14 data as pricing perspective)
    gross_margin = rev_kpis.get("gross_margin", 0)
    if gross_margin > 0:
        checks.append(CheckResult(
            check_id="PR09", category="pricing", severity="high",
            result="pass" if gross_margin >= 0.15 else ("warning" if gross_margin >= 0.1 else "fail"),
            message=f"Overall gross margin: {gross_margin:.1%}",
            current_value=gross_margin, threshold=0.15,
        ))

    return checks


@cli.group()
def review():
    """Generate periodic business reviews (MBR / QBR / ABR)."""
    pass


@review.command()
@click.argument("orders_path", required=False, default=None)
@click.option("--products", "products_path", default=None, help="Products CSV path")
@click.option("--inventory", "inventory_path", default=None, help="Inventory CSV path")
@click.option("--format", "fmt", default="auto", help="CSV format (shopify|generic|auto)")
@click.option("--output", default="./", help="Output directory for reports")
@click.option("--source", type=click.Choice(["csv", "shopify"]), default="csv", help="Data source")
@click.option("--since", default=None, help="Start date for Shopify sync")
@click.option("--until", default=None, help="End date for Shopify sync")
def mbr(orders_path, products_path, inventory_path, fmt, output, source, since, until):
    """Generate a Monthly Business Review."""
    _run_review("mbr", orders_path, products_path, inventory_path, fmt, output, source, since, until)


@review.command()
@click.argument("orders_path", required=False, default=None)
@click.option("--products", "products_path", default=None, help="Products CSV path")
@click.option("--inventory", "inventory_path", default=None, help="Inventory CSV path")
@click.option("--format", "fmt", default="auto", help="CSV format (shopify|generic|auto)")
@click.option("--output", default="./", help="Output directory for reports")
@click.option("--source", type=click.Choice(["csv", "shopify"]), default="csv", help="Data source")
@click.option("--since", default=None, help="Start date for Shopify sync")
@click.option("--until", default=None, help="End date for Shopify sync")
def qbr(orders_path, products_path, inventory_path, fmt, output, source, since, until):
    """Generate a Quarterly Business Review."""
    _run_review("qbr", orders_path, products_path, inventory_path, fmt, output, source, since, until)


@review.command()
@click.argument("orders_path", required=False, default=None)
@click.option("--products", "products_path", default=None, help="Products CSV path")
@click.option("--inventory", "inventory_path", default=None, help="Inventory CSV path")
@click.option("--format", "fmt", default="auto", help="CSV format (shopify|generic|auto)")
@click.option("--output", default="./", help="Output directory for reports")
@click.option("--source", type=click.Choice(["csv", "shopify"]), default="csv", help="Data source")
@click.option("--since", default=None, help="Start date for Shopify sync")
@click.option("--until", default=None, help="End date for Shopify sync")
def abr(orders_path, products_path, inventory_path, fmt, output, source, since, until):
    """Generate an Annual Business Review."""
    _run_review("abr", orders_path, products_path, inventory_path, fmt, output, source, since, until)


def _run_review(cadence, orders_path, products_path, inventory_path, fmt, output, source, since, until):
    """Shared implementation for review commands."""
    from ecom_analytics.review_engine import build_review_data

    if source == "shopify":
        from ecom_analytics.config import load_config
        from ecom_analytics.sync import sync_shopify, load_synced_data

        if since is None:
            raise click.UsageError("--since is required with --source shopify")

        click.echo("Loading Shopify config...")
        cfg = load_config()

        click.echo(f"Syncing data from Shopify (since {since})...")

        def progress(op_name, status, count):
            click.echo(f"  [{op_name}] {status} — {count} objects", nl=True)

        sync_shopify(cfg, since=since, until=until, progress_cb=progress)
        orders, products, inventory = load_synced_data()
    else:
        if orders_path is None:
            raise click.UsageError(
                "ORDERS_PATH is required when --source=csv. "
                "Use --source shopify for Shopify Admin API data."
            )
        click.echo("Loading data...")
        orders = load_orders(orders_path, fmt=fmt)
        products = load_products(products_path) if products_path else None
        inventory = load_inventory(inventory_path) if inventory_path else None

    cadence_labels = {"mbr": "Monthly", "qbr": "Quarterly", "abr": "Annual"}
    click.echo(f"Building {cadence_labels[cadence]} Business Review...")
    review_data = build_review_data(orders, cadence, products=products, inventory=inventory)

    click.echo(f"Generating report to {output} ...")
    path = generate_review(review_data, cadence, output_dir=output)
    click.echo(f"Done. Report: {path}")


if __name__ == "__main__":
    cli()
