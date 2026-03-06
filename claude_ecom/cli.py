"""CLI entry point for claude-ecom."""

from __future__ import annotations

import click
import pandas as pd

from claude_ecom import __version__
from claude_ecom.loader import (
    GENERIC_ORDER_REQUIRED,
    _auto_map_columns,
    _fuzzy_map_columns,
    load_orders,
)
from claude_ecom.report import generate_review_json


@click.group()
@click.version_option(version=__version__)
def cli():
    """claude-ecom: EC-specialized data analytics toolkit."""
    pass


# ---------------------------------------------------------------------------
# review command (single unified command)
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("orders_path")
@click.option(
    "--period",
    type=click.Choice(["30d", "90d", "365d"]),
    default=None,
    help="Focus on a specific period (default: auto-select all)",
)
@click.option("--output", default="./", help="Output directory for reports")
@click.option("--format", "fmt", default="auto", help="CSV format (shopify|generic|auto)")
@click.option("--nrows", default=None, type=int, help="Limit rows to read (for large files)")
def review(orders_path, period, output, fmt, nrows):
    """Run a business review and generate review.json."""
    from claude_ecom.review_engine import build_review_data

    click.echo("Loading data...")
    orders = load_orders(orders_path, fmt=fmt, nrows=nrows)
    if nrows:
        click.echo(f"  (limited to {nrows:,} rows)")

    click.echo("Building review...")
    review_data = build_review_data(orders, period=period)

    # Display coverage
    cov = review_data["data_coverage"]
    covered = [p for p, v in cov.items() if v]
    click.echo(f"  Data coverage: {', '.join(covered) if covered else 'insufficient data'}")

    click.echo(f"\nGenerating review.json to {output} ...")
    path = generate_review_json(review_data, output_dir=output)
    click.echo(f"Done. Output: {path}")


# ---------------------------------------------------------------------------
# validate command
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("orders_path")
@click.option("--format", "fmt", default="auto", help="CSV format (shopify|generic|auto)")
def validate(orders_path, fmt):
    """Show column mapping diagnostics for order data."""
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
            click.echo("\nTier 2: no fuzzy matches found")
        still_missing = GENERIC_ORDER_REQUIRED - set(df2.columns)
    else:
        still_missing = set()

    click.echo(f"\nRequired columns: {GENERIC_ORDER_REQUIRED}")
    if still_missing:
        click.echo(f"Still missing: {still_missing}")
    else:
        click.echo("All required columns resolved.")


if __name__ == "__main__":
    cli()
