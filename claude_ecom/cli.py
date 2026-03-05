"""CLI entry point for claude-ecom."""

from __future__ import annotations

import math

import click
import pandas as pd

from claude_ecom import __version__
from claude_ecom.loader import (
    GENERIC_ORDER_REQUIRED,
    _auto_map_columns,
    _fuzzy_map_columns,
    load_inventory,
    load_orders,
    load_products,
)
from claude_ecom.metrics import (
    compute_cohort_kpis,
    compute_revenue_kpis,
)
from claude_ecom.report import (
    generate_audit_report,
    generate_business_review,
    generate_executive_summary,
    generate_review,
    generate_scores_json,
)
from claude_ecom.scoring import CheckResult, score_checks


@click.group()
@click.version_option(version=__version__)
def cli():
    """claude-ecom: EC-specialized data analytics toolkit."""
    pass


# ---------------------------------------------------------------------------
# audit command
# ---------------------------------------------------------------------------


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
@click.option("--nrows", default=None, type=int, help="Limit rows to read (for large files)")
def audit(orders_path, products_path, inventory_path, fmt, output, source, since, until, site_url, nrows):
    """Run a full EC health audit and generate reports."""
    if source == "shopify":
        _audit_shopify(output, since, until, site_url)
        return

    if orders_path is None:
        raise click.UsageError(
            "ORDERS_PATH is required when --source=csv. Use --source shopify for Shopify Admin API data."
        )

    click.echo("Loading data...")
    orders = load_orders(orders_path, fmt=fmt, nrows=nrows)
    if nrows:
        click.echo(f"  (limited to {nrows:,} rows)")
    products = load_products(products_path) if products_path else None
    inventory = load_inventory(inventory_path) if inventory_path else None

    click.echo("Computing KPIs...")
    rev_kpis = compute_revenue_kpis(orders)
    cohort_kpis = compute_cohort_kpis(orders)

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
    # Annualize revenue based on data span
    total_revenue = rev_kpis["total_revenue"]
    data_start = str(orders["order_date"].min().date())
    data_end = str(orders["order_date"].max().date())
    data_span_days = (orders["order_date"].max() - orders["order_date"].min()).days
    if data_span_days > 0 and data_span_days < 365:
        annual_revenue = total_revenue * (365 / data_span_days)
    else:
        annual_revenue = total_revenue
    if annual_revenue <= 0:
        annual_revenue = 0.0

    bmodel = _detect_business_model(orders)
    generate_audit_report(
        health, annual_revenue, data_start=data_start, data_end=data_end,
        output_dir=output, business_model=bmodel,
    )
    generate_executive_summary(health, annual_revenue, output_dir=output, business_model=bmodel)
    generate_scores_json(health, output_dir=output, business_model=bmodel)
    click.echo("Done. Reports: AUDIT-REPORT.md, executive-summary.md, scores.json")


def _audit_shopify(output, since, until, site_url=None):
    """Run audit using Shopify Admin API data."""
    from claude_ecom.config import load_config
    from claude_ecom.sync import load_synced_data, sync_shopify

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

    # Optional site quality audit
    if site_url:
        checks.extend(_run_site_checks(site_url, output))

    click.echo("Scoring...")
    health = score_checks(checks)

    click.echo(f"\nOverall Score: {health.overall_score}/100 (Grade: {health.overall_grade})")
    for cat, cs in health.category_scores.items():
        click.echo(f"  {cat:>12}: {cs.score}/100 ({cs.grade})")

    click.echo(f"\nGenerating reports to {output} ...")
    # Annualize revenue based on data span
    total_revenue = rev_kpis["total_revenue"]
    data_span_days = (orders["order_date"].max() - orders["order_date"].min()).days
    if data_span_days > 0 and data_span_days < 365:
        annual_revenue = total_revenue * (365 / data_span_days)
    else:
        annual_revenue = total_revenue
    if annual_revenue <= 0:
        annual_revenue = 0.0
    data_start = str(orders["order_date"].min().date())
    data_end = str(orders["order_date"].max().date())

    generate_audit_report(
        health, annual_revenue, data_start=data_start, data_end=data_end,
        output_dir=output, business_model="D2C (Shopify)",
    )
    generate_executive_summary(health, annual_revenue, output_dir=output, business_model="D2C (Shopify)")
    generate_scores_json(health, output_dir=output, business_model="D2C (Shopify)")
    click.echo("Done. Reports: AUDIT-REPORT.md, executive-summary.md, scores.json")


# ---------------------------------------------------------------------------
# Site audit helper
# ---------------------------------------------------------------------------


def _run_site_checks(url: str, output_dir: str = "./") -> list[CheckResult]:
    """Run site audit on a URL and return SA01-SA15 checks."""
    try:
        from claude_ecom.site_audit import analyze_page, build_site_checks_single
    except ImportError:
        click.echo("Site audit requires Playwright: pip install claude-ecom[site] && playwright install chromium")
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


# ---------------------------------------------------------------------------
# Shopify Admin API commands
# ---------------------------------------------------------------------------


@cli.group("shopify")
def shopify_group():
    """Shopify Admin API integration."""
    pass


@shopify_group.command("setup")
@click.option("--global", "global_", is_flag=True, help="Save to ~/.claude-ecom/")
def shopify_setup(global_):
    """Interactive setup for Shopify Admin API credentials."""
    from claude_ecom.config import ShopifyConfig, save_config

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
        click.echo("Note: .claude-ecom/ added to .gitignore for token safety.")

    click.echo("\nNext: run 'ecom shopify sync --since 2024-01-01'")


@shopify_group.command("sync")
@click.option("--since", required=True, help="Start date (ISO format, e.g. 2024-01-01)")
@click.option("--until", default=None, help="End date (optional)")
@click.option("--mode", type=click.Choice(["full", "incremental"]), default="full")
@click.option("--out", "out_dir", default=".claude-ecom/data", help="Output directory")
@click.option("--timeout-minutes", default=60, help="Max wait per bulk operation")
def shopify_sync(since, until, mode, out_dir, timeout_minutes):
    """Sync data from Shopify Admin API via Bulk Operations."""
    from claude_ecom.config import load_config
    from claude_ecom.sync import sync_shopify

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

    click.echo("\nSync complete!")
    click.echo(f"  Orders:      {state.record_counts.get('orders', 0):,}")
    click.echo(f"  Line items:  {state.record_counts.get('order_items', 0):,}")
    click.echo(f"  Products:    {state.record_counts.get('products', 0):,}")
    click.echo(f"  Inventory:   {state.record_counts.get('inventory', 0):,}")
    click.echo(f"  Output:      {out_dir}/")
    click.echo(f"\nNext: run 'ecom audit --source shopify --since {since}'")


# ---------------------------------------------------------------------------
# review command
# ---------------------------------------------------------------------------


class _DefaultGroup(click.Group):
    """Click Group that routes to a default subcommand when none is given."""

    def parse_args(self, ctx, args):
        # If first arg is not a known subcommand, insert 'general' as default
        if args and args[0] not in self.commands:
            args = ["general"] + args
        return super().parse_args(ctx, args)


def _review_options(fn):
    """Shared Click options for all review commands."""
    fn = click.argument("orders_path", required=False, default=None)(fn)
    fn = click.option("--products", "products_path", default=None, help="Products CSV path")(fn)
    fn = click.option("--inventory", "inventory_path", default=None, help="Inventory CSV path")(fn)
    fn = click.option("--format", "fmt", default="auto", help="CSV format (shopify|generic|auto)")(fn)
    fn = click.option("--output", default="./", help="Output directory for reports")(fn)
    fn = click.option("--source", type=click.Choice(["csv", "shopify"]), default="csv", help="Data source")(fn)
    fn = click.option("--since", default=None, help="Start date for Shopify sync")(fn)
    fn = click.option("--until", default=None, help="End date for Shopify sync")(fn)
    fn = click.option("--nrows", default=None, type=int, help="Limit rows to read (for large files)")(fn)
    fn = click.option("--period-start", default=None, help="Period start date (ISO format, e.g. 2024-01-01)")(fn)
    fn = click.option("--period-end", default=None, help="Period end date (ISO format, e.g. 2024-03-31)")(fn)
    return fn


@cli.group(cls=_DefaultGroup)
def review():
    """Generate periodic business reviews (MBR / QBR / ABR).

    When invoked without a subcommand (e.g. 'ecom review orders.csv'),
    generates a generic BUSINESS-REVIEW-REPORT.md with auto-detected cadence.
    """
    pass


@review.command("general", hidden=True)
@_review_options
def review_general(orders_path, products_path, inventory_path, fmt, output, source, since, until, nrows, period_start, period_end):
    """Generate a generic Business Review Report (auto-detected cadence)."""
    _run_review("general", orders_path, products_path, inventory_path, fmt, output, source, since, until, nrows, period_start, period_end)


@review.command()
@_review_options
def mbr(orders_path, products_path, inventory_path, fmt, output, source, since, until, nrows, period_start, period_end):
    """Generate a Monthly Business Review."""
    _run_review("mbr", orders_path, products_path, inventory_path, fmt, output, source, since, until, nrows, period_start, period_end)


@review.command()
@_review_options
def qbr(orders_path, products_path, inventory_path, fmt, output, source, since, until, nrows, period_start, period_end):
    """Generate a Quarterly Business Review."""
    _run_review("qbr", orders_path, products_path, inventory_path, fmt, output, source, since, until, nrows, period_start, period_end)


@review.command()
@_review_options
def abr(orders_path, products_path, inventory_path, fmt, output, source, since, until, nrows, period_start, period_end):
    """Generate an Annual Business Review."""
    _run_review("abr", orders_path, products_path, inventory_path, fmt, output, source, since, until, nrows, period_start, period_end)


def _run_review(cadence, orders_path, products_path, inventory_path, fmt, output, source, since, until, nrows=None, period_start=None, period_end=None):
    """Shared implementation for review commands."""
    from datetime import date as date_type

    from claude_ecom.review_engine import build_review_data

    if source == "shopify":
        from claude_ecom.config import load_config
        from claude_ecom.sync import load_synced_data, sync_shopify

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
                "ORDERS_PATH is required when --source=csv. Use --source shopify for Shopify Admin API data."
            )
        click.echo("Loading data...")
        orders = load_orders(orders_path, fmt=fmt, nrows=nrows)
        products = load_products(products_path) if products_path else None
        inventory = load_inventory(inventory_path) if inventory_path else None

    # Parse period boundaries
    ps = date_type.fromisoformat(period_start) if period_start else None
    pe = date_type.fromisoformat(period_end) if period_end else None

    cadence_labels = {"mbr": "Monthly", "qbr": "Quarterly", "abr": "Annual", "general": "General"}
    click.echo(f"Building {cadence_labels.get(cadence, cadence)} Business Review...")
    review_data = build_review_data(
        orders, cadence, products=products, inventory=inventory,
        period_start=ps, period_end=pe,
    )

    click.echo(f"Generating report to {output} ...")
    if cadence == "general":
        path = generate_business_review(review_data, output_dir=output)
    else:
        path = generate_review(review_data, cadence, output_dir=output)
    click.echo(f"Done. Report: {path}")


# ---------------------------------------------------------------------------
# validate command
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("orders_path")
@click.option("--format", "fmt", default="auto", help="CSV format (shopify|generic|auto)")
def validate(orders_path, fmt):
    """Show column mapping diagnostics without running a full audit."""
    df = pd.read_csv(orders_path, nrows=100, low_memory=False)
    click.echo(f"Columns found: {list(df.columns)}\n")

    # Tier 1: exact alias match
    df1, tier1_map = _auto_map_columns(df.copy())
    if tier1_map:
        click.echo("Tier 1 (exact alias match):")
        for orig, canonical in tier1_map.items():
            click.echo(f"  {orig} -> {canonical}")
    else:
        click.echo("Tier 1: no exact alias matches")

    # Tier 2: fuzzy match
    missing_after_t1 = GENERIC_ORDER_REQUIRED - set(df1.columns)
    if missing_after_t1:
        df2, tier2_map = _fuzzy_map_columns(df1.copy())
        if tier2_map:
            click.echo("\nTier 2 (fuzzy token + type inference):")
            for orig, canonical in tier2_map.items():
                click.echo(f"  {orig} -> {canonical}")
        else:
            click.echo(f"\nTier 2: no fuzzy matches found")
        still_missing = GENERIC_ORDER_REQUIRED - set(df2.columns)
    else:
        still_missing = set()

    click.echo(f"\nRequired columns: {GENERIC_ORDER_REQUIRED}")
    if still_missing:
        click.echo(f"Still missing: {still_missing}")
    else:
        click.echo("All required columns resolved.")


# ---------------------------------------------------------------------------
# Internal: business model detection
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

    Implements 35+ checks across all 6 categories.
    """
    checks: list[CheckResult] = []

    # ===== Revenue checks (R01-R14) =====
    mom = rev_kpis.get("mom_growth_latest", float("nan"))
    try:
        mom = float(mom)
    except (ValueError, TypeError):
        mom = float("nan")
    if math.isnan(mom):
        checks.append(
            CheckResult(
                check_id="R01",
                category="revenue",
                severity="high",
                result="na",
                message="Insufficient data for MoM growth (<2 months)",
                current_value=None,
                threshold=0.0,
            )
        )
    else:
        checks.append(
            CheckResult(
                check_id="R01",
                category="revenue",
                severity="high",
                result="pass" if mom > 0 else ("warning" if mom > -0.05 else "fail"),
                message=f"MoM revenue growth: {mom:.1%}",
                current_value=mom,
                threshold=0.0,
            )
        )

    # R03 — AOV Trend
    monthly_aov = rev_kpis.get("monthly_aov", {})
    if len(monthly_aov) >= 2:
        aov_vals = list(monthly_aov.values())
        aov_change = (aov_vals[-1] - aov_vals[-2]) / aov_vals[-2] if aov_vals[-2] else 0
        checks.append(
            CheckResult(
                check_id="R03",
                category="revenue",
                severity="high",
                result="pass" if aov_change > -0.05 else ("warning" if aov_change > -0.1 else "fail"),
                message=f"AOV MoM change: {aov_change:.1%}",
                current_value=aov_change,
                threshold=-0.05,
            )
        )

    # R04 — Order Count Trend
    monthly_orders = rev_kpis.get("monthly_orders", {})
    if len(monthly_orders) >= 2:
        ord_vals = list(monthly_orders.values())
        ord_change = (ord_vals[-1] - ord_vals[-2]) / ord_vals[-2] if ord_vals[-2] else 0
        checks.append(
            CheckResult(
                check_id="R04",
                category="revenue",
                severity="high",
                result="pass" if ord_change > -0.05 else ("warning" if ord_change > -0.1 else "fail"),
                message=f"MoM order count change: {ord_change:.1%}",
                current_value=ord_change,
                threshold=-0.05,
            )
        )

    repeat_share = rev_kpis.get("repeat_revenue_share", 0)
    f2_rate_for_cross_check = cohort_kpis.get("f2_rate", 0)
    # Cross-check: if repeat_share==0 but F2 rate is significant, flag data issue
    if repeat_share == 0 and f2_rate_for_cross_check > 0.3:
        checks.append(
            CheckResult(
                check_id="R05",
                category="revenue",
                severity="critical",
                result="warning",
                message=f"Repeat customer revenue share: {repeat_share:.1%} (data quality issue: F2={f2_rate_for_cross_check:.1%})",
                current_value=repeat_share,
                threshold=0.3,
            )
        )
    else:
        checks.append(
            CheckResult(
                check_id="R05",
                category="revenue",
                severity="critical",
                result="pass" if repeat_share >= 0.3 else ("warning" if repeat_share >= 0.2 else "fail"),
                message=f"Repeat customer revenue share: {repeat_share:.1%}",
                current_value=repeat_share,
                threshold=0.3,
            )
        )

    top10 = rev_kpis.get("top10_customer_share", 0)
    if rev_kpis.get("total_revenue", 0) == 0:
        checks.append(
            CheckResult(
                check_id="R07",
                category="revenue",
                severity="medium",
                result="na",
                message="No revenue data for concentration analysis",
                current_value=None,
                threshold=0.6,
            )
        )
    else:
        checks.append(
            CheckResult(
                check_id="R07",
                category="revenue",
                severity="medium",
                result="pass" if top10 < 0.6 else ("warning" if top10 < 0.8 else "fail"),
                message=f"Top 10% customer revenue share: {top10:.1%}",
                current_value=top10,
                threshold=0.6,
            )
        )

    discount_rate = rev_kpis.get("avg_discount_rate", 0)
    if "discount" not in orders.columns and discount_rate == 0:
        checks.append(
            CheckResult(
                check_id="R08",
                category="revenue",
                severity="high",
                result="na",
                message="No discount data available",
                current_value=None,
                threshold=0.15,
            )
        )
    else:
        checks.append(
            CheckResult(
                check_id="R08",
                category="revenue",
                severity="high",
                result="pass" if discount_rate < 0.15 else ("warning" if discount_rate < 0.25 else "fail"),
                message=f"Average discount rate: {discount_rate:.1%}",
                current_value=discount_rate,
                threshold=0.15,
            )
        )

    daily_cv = rev_kpis.get("daily_revenue_cv", 0)
    if isinstance(daily_cv, float) and math.isnan(daily_cv):
        checks.append(
            CheckResult(
                check_id="R13",
                category="revenue",
                severity="medium",
                result="na",
                message="Insufficient daily data for CV calculation",
                current_value=None,
                threshold=0.5,
            )
        )
    elif rev_kpis.get("total_revenue", 0) == 0:
        checks.append(
            CheckResult(
                check_id="R13",
                category="revenue",
                severity="medium",
                result="na",
                message="No revenue data for CV calculation",
                current_value=None,
                threshold=0.5,
            )
        )
    else:
        checks.append(
            CheckResult(
                check_id="R13",
                category="revenue",
                severity="medium",
                result="pass" if daily_cv < 0.5 else ("warning" if daily_cv < 0.8 else "fail"),
                message=f"Daily revenue coefficient of variation: {daily_cv:.2f}",
                current_value=daily_cv,
                threshold=0.5,
            )
        )

    # R14 — Large Order Dependency
    if rev_kpis.get("total_revenue", 0) > 0:
        order_amounts = orders.groupby("order_id")["amount"].sum()
        largest_share = order_amounts.max() / rev_kpis["total_revenue"]
        checks.append(
            CheckResult(
                check_id="R14",
                category="revenue",
                severity="medium",
                result="pass" if largest_share < 0.05 else ("warning" if largest_share < 0.1 else "fail"),
                message=f"Largest order share of revenue: {largest_share:.1%}",
                current_value=largest_share,
                threshold=0.05,
            )
        )

    # ===== Product checks (P01, P05, P06, P07, P09, P10, P19) =====
    if products is not None:
        from claude_ecom.metrics import compute_product_kpis as prod_kpis_fn

        prod_kpis = prod_kpis_fn(orders, products)

        top20 = prod_kpis.get("top20_revenue_share", 0)
        checks.append(
            CheckResult(
                check_id="P01",
                category="product",
                severity="medium",
                result="pass" if 0.5 <= top20 <= 0.8 else ("warning" if top20 <= 0.9 else "fail"),
                message=f"Top 20% SKU revenue concentration: {top20:.1%}",
                current_value=top20,
                threshold=0.8,
            )
        )

        multi_item = prod_kpis.get("multi_item_order_rate", 0)
        checks.append(
            CheckResult(
                check_id="P06",
                category="product",
                severity="medium",
                result="pass" if multi_item >= 0.25 else ("warning" if multi_item >= 0.15 else "fail"),
                message=f"Multi-item order rate: {multi_item:.1%}",
                current_value=multi_item,
                threshold=0.25,
            )
        )

    # P05 — Converting SKU Rate (works without products CSV too)
    key = "sku" if "sku" in orders.columns else "product_name" if "product_name" in orders.columns else None
    if key:
        total_active = orders[key].nunique()
        selling = orders.groupby(key)["amount"].sum()
        converting = (selling > 0).sum()
        convert_rate = converting / total_active if total_active else 0
        if total_active == 0:
            checks.append(
                CheckResult(
                    check_id="P05",
                    category="product",
                    severity="high",
                    result="na",
                    message="No SKU/product data available for conversion analysis",
                    current_value=None,
                    threshold=0.7,
                )
            )
        else:
            checks.append(
                CheckResult(
                    check_id="P05",
                    category="product",
                    severity="high",
                    result="pass" if convert_rate >= 0.7 else ("warning" if convert_rate >= 0.5 else "fail"),
                    message=f"Converting SKU rate: {convert_rate:.1%} ({converting}/{total_active})",
                    current_value=convert_rate,
                    threshold=0.7,
                )
            )

    # P07 — Cross-Sell Pair Lift
    if key:
        from claude_ecom.product import cross_sell_matrix

        xs = cross_sell_matrix(orders)
        high_lift = len(xs[xs["lift"] > 2.0]) if len(xs) else 0
        checks.append(
            CheckResult(
                check_id="P07",
                category="product",
                severity="medium",
                result="pass" if high_lift >= 3 else ("warning" if high_lift >= 1 else "fail"),
                message=f"Cross-sell pairs with lift > 2.0: {high_lift}",
                current_value=high_lift,
                threshold=3,
            )
        )

    # P10 — Lifecycle Stage Distribution
    if key:
        from claude_ecom.product import product_lifecycle

        lifecycle = product_lifecycle(orders)
        if len(lifecycle):
            decline_pct = (lifecycle["lifecycle_stage"] == "Decline").mean()
            checks.append(
                CheckResult(
                    check_id="P10",
                    category="product",
                    severity="medium",
                    result="pass" if decline_pct < 0.3 else ("warning" if decline_pct < 0.5 else "fail"),
                    message=f"Decline-stage products: {decline_pct:.1%}",
                    current_value=decline_pct,
                    threshold=0.3,
                )
            )

    # P19 — Price Tier Distribution
    if key:
        prices = orders.groupby(key)["amount"].mean()
        if len(prices) == 0:
            checks.append(
                CheckResult(
                    check_id="P19",
                    category="product",
                    severity="medium",
                    result="na",
                    message="No price data available for tier analysis",
                    current_value=None,
                    threshold=3,
                )
            )
        else:
            try:
                n_tiers = len(pd.qcut(prices, q=min(4, len(prices)), duplicates="drop").cat.categories)
            except (ValueError, TypeError):
                n_tiers = 1
            checks.append(
                CheckResult(
                    check_id="P19",
                    category="product",
                    severity="medium",
                    result="pass" if n_tiers >= 3 else ("warning" if n_tiers >= 2 else "fail"),
                    message=f"Distinct price tiers: {n_tiers}",
                    current_value=n_tiers,
                    threshold=3,
                )
            )

    # ===== Retention checks (C01, C02, C08, C09, C10, C11) =====
    f2 = cohort_kpis.get("f2_rate", 0)
    checks.append(
        CheckResult(
            check_id="C01",
            category="retention",
            severity="critical",
            result="pass" if f2 >= 0.25 else ("warning" if f2 >= 0.15 else "fail"),
            message=f"F2 conversion rate: {f2:.1%}",
            current_value=f2,
            threshold=0.25,
        )
    )

    avg_interval = cohort_kpis.get("avg_purchase_interval_days", float("nan"))
    if isinstance(avg_interval, float) and math.isnan(avg_interval):
        checks.append(
            CheckResult(
                check_id="C11",
                category="retention",
                severity="high",
                result="na",
                message="Insufficient data for purchase interval calculation",
                current_value=None,
                threshold=60,
            )
        )
    else:
        checks.append(
            CheckResult(
                check_id="C11",
                category="retention",
                severity="high",
                result="pass" if avg_interval < 60 else ("warning" if avg_interval < 90 else "fail"),
                message=f"Avg days to 2nd purchase: {avg_interval:.0f}",
                current_value=avg_interval,
                threshold=60,
            )
        )

    # C08/C09/C10 — RFM Segment Distribution
    order_counts = orders.groupby("customer_id")["order_id"].nunique()
    total_cust = len(order_counts)
    if total_cust > 0:
        from claude_ecom.cohort import rfm_segmentation

        try:
            rfm = rfm_segmentation(orders)
            seg_dist = rfm["segment"].value_counts(normalize=True)

            champions_loyal = seg_dist.get("Champions", 0) + seg_dist.get("Loyal", 0)
            checks.append(
                CheckResult(
                    check_id="C08",
                    category="retention",
                    severity="medium",
                    result="pass" if champions_loyal >= 0.2 else ("warning" if champions_loyal >= 0.1 else "fail"),
                    message=f"Champions + Loyal segment share: {champions_loyal:.1%}",
                    current_value=champions_loyal,
                    threshold=0.2,
                )
            )

            at_risk = seg_dist.get("At Risk", 0)
            checks.append(
                CheckResult(
                    check_id="C09",
                    category="retention",
                    severity="high",
                    result="pass" if at_risk < 0.25 else ("warning" if at_risk < 0.35 else "fail"),
                    message=f"At-Risk segment share: {at_risk:.1%}",
                    current_value=at_risk,
                    threshold=0.25,
                )
            )

            lost = seg_dist.get("Lost", 0)
            checks.append(
                CheckResult(
                    check_id="C10",
                    category="retention",
                    severity="medium",
                    result="pass" if lost < 0.3 else ("warning" if lost < 0.45 else "fail"),
                    message=f"Lost segment share: {lost:.1%}",
                    current_value=lost,
                    threshold=0.3,
                )
            )
        except Exception:
            pass  # RFM requires sufficient data

    # ===== Inventory checks (O01-O06, O10) =====
    if inventory is not None:
        from claude_ecom.inventory import inventory_turnover, overstock_analysis, stockout_analysis
        from claude_ecom.metrics import compute_inventory_kpis as inv_kpis_fn

        inv_kpis = inv_kpis_fn(inventory, orders)

        so_rate = inv_kpis.get("stockout_rate", 0)
        checks.append(
            CheckResult(
                check_id="O03",
                category="inventory",
                severity="critical",
                result="pass" if so_rate < 0.05 else ("warning" if so_rate < 0.1 else "fail"),
                message=f"Stockout SKU rate: {so_rate:.1%}",
                current_value=so_rate,
                threshold=0.05,
            )
        )

        # O01 — Overall Inventory Turnover
        turn = inventory_turnover(inventory, orders)
        if len(turn) and "turnover" in turn.columns:
            median_turn = turn["turnover"].median()
            checks.append(
                CheckResult(
                    check_id="O01",
                    category="inventory",
                    severity="high",
                    result="pass" if median_turn >= 6 else ("warning" if median_turn >= 4 else "fail"),
                    message=f"Median inventory turnover: {median_turn:.1f}x/year",
                    current_value=median_turn,
                    threshold=6.0,
                )
            )

        # O05 — Overstock Value
        ov = overstock_analysis(inventory, orders)
        inv_val = inv_kpis.get("total_inventory_value", 0)
        if inv_val and inv_val == inv_val:  # not NaN
            overstock_pct = ov.overstock_value / inv_val
            checks.append(
                CheckResult(
                    check_id="O05",
                    category="inventory",
                    severity="high",
                    result="pass" if overstock_pct < 0.2 else ("warning" if overstock_pct < 0.35 else "fail"),
                    message=f"Overstock value (>90d): {overstock_pct:.1%} of inventory",
                    current_value=overstock_pct,
                    threshold=0.2,
                )
            )

        # O06 — Deadstock Rate
        total_inv_skus = inv_kpis.get("total_skus", 1)
        deadstock_rate = len(ov.deadstock_skus) / total_inv_skus if total_inv_skus else 0
        checks.append(
            CheckResult(
                check_id="O06",
                category="inventory",
                severity="high",
                result="pass" if deadstock_rate < 0.1 else ("warning" if deadstock_rate < 0.2 else "fail"),
                message=f"Deadstock rate (>180d): {deadstock_rate:.1%}",
                current_value=deadstock_rate,
                threshold=0.1,
            )
        )

        # O04 — Stockout Opportunity Cost
        so = stockout_analysis(inventory, orders)
        monthly_rev = rev_kpis.get("total_revenue", 0) / 12
        if monthly_rev > 0:
            lost_pct = so.estimated_lost_revenue / monthly_rev
            checks.append(
                CheckResult(
                    check_id="O04",
                    category="inventory",
                    severity="critical",
                    result="pass" if lost_pct < 0.03 else ("warning" if lost_pct < 0.05 else "fail"),
                    message=f"Stockout opportunity cost: {lost_pct:.1%} of monthly revenue",
                    current_value=lost_pct,
                    threshold=0.03,
                )
            )

        # O10 — Inventory Cost as % of Revenue
        if inv_val and inv_val == inv_val and rev_kpis.get("total_revenue", 0):
            inv_rev_pct = inv_val / rev_kpis["total_revenue"]
            checks.append(
                CheckResult(
                    check_id="O10",
                    category="inventory",
                    severity="medium",
                    result="pass" if inv_rev_pct < 0.25 else ("warning" if inv_rev_pct < 0.4 else "fail"),
                    message=f"Inventory cost as % of revenue: {inv_rev_pct:.1%}",
                    current_value=inv_rev_pct,
                    threshold=0.25,
                )
            )

    # ===== Pricing checks (PR01-PR03) =====
    if "discount" in orders.columns:
        from claude_ecom.pricing import discount_dependency as dd_fn

        dd = dd_fn(orders)
        checks.append(
            CheckResult(
                check_id="PR01",
                category="pricing",
                severity="high",
                result="pass"
                if dd.avg_discount_rate < 0.15
                else ("warning" if dd.avg_discount_rate < 0.25 else "fail"),
                message=f"Average discount rate: {dd.avg_discount_rate:.1%}",
                current_value=dd.avg_discount_rate,
                threshold=0.15,
            )
        )
        checks.append(
            CheckResult(
                check_id="PR02",
                category="pricing",
                severity="high",
                result=(
                    "pass"
                    if dd.discounted_order_ratio < 0.4
                    else ("warning" if dd.discounted_order_ratio < 0.6 else "fail")
                ),
                message=f"Discounted order ratio: {dd.discounted_order_ratio:.1%}",
                current_value=dd.discounted_order_ratio,
                threshold=0.4,
            )
        )
        # PR03 — Discount Depth Trend
        trend = dd.discount_rate_trend
        checks.append(
            CheckResult(
                check_id="PR03",
                category="pricing",
                severity="critical",
                result="pass" if trend == "stable" or trend == "decreasing" else "warning",
                message=f"Discount depth trend: {trend}",
                current_value=trend,
                threshold="stable",
            )
        )

    # PR07 — Category Margin Variance (if cost data available)
    if "cost" in orders.columns:
        from claude_ecom.pricing import margin_analysis

        ma = margin_analysis(orders)
        neg_cats = len(ma.negative_margin_categories)
        checks.append(
            CheckResult(
                check_id="PR07",
                category="pricing",
                severity="medium",
                result="pass" if neg_cats == 0 else ("warning" if neg_cats == 1 else "fail"),
                message=f"Categories with negative margin: {neg_cats}",
                current_value=neg_cats,
                threshold=0,
            )
        )

    # PR08 — Free-Shipping Threshold
    from claude_ecom.pricing import free_shipping_threshold

    fst = free_shipping_threshold(orders)
    if fst.suggested_threshold == 0 or fst.current_aov == 0:
        checks.append(
            CheckResult(
                check_id="PR08",
                category="pricing",
                severity="high",
                result="na",
                message="Insufficient order data for free-shipping threshold analysis",
                current_value=None,
                threshold=0.1,
            )
        )
    else:
        checks.append(
            CheckResult(
                check_id="PR08",
                category="pricing",
                severity="high",
                result="pass"
                if fst.potential_aov_lift >= 0.1
                else ("warning" if fst.potential_aov_lift >= 0.05 else "fail"),
                message=(
                    f"Free-shipping threshold AOV lift potential: "
                    f"{fst.potential_aov_lift:.1%} (suggested: {fst.suggested_threshold:,.0f})"
                ),
                current_value=fst.potential_aov_lift,
                threshold=0.1,
            )
        )

    return checks


if __name__ == "__main__":
    cli()
