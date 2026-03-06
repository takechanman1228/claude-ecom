"""Calendar period utilities for business reviews."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass
class PeriodRange:
    """A labelled date range representing a business period."""

    label: str  # e.g. "February 2026", "Q1 2026", "2025"
    start: date
    end: date


def trailing_window(ref: date, days: int) -> PeriodRange:
    """Trailing N-day window ending at ref (inclusive)."""
    from datetime import timedelta

    start = ref - timedelta(days=days - 1)
    return PeriodRange(
        label=f"Past {days} Days",
        start=start,
        end=ref,
    )


# ---------------------------------------------------------------------------
# Data coverage & prior trailing window (new for unified review model)
# ---------------------------------------------------------------------------

COVERAGE_THRESHOLDS = {"30d": 45, "90d": 120, "365d": 400}


def compute_data_coverage(orders: pd.DataFrame) -> dict[str, bool]:
    """Check which trailing periods have enough data.

    Returns ``{"30d": bool, "90d": bool, "365d": bool}`` based on
    whether the data span (in days) meets the threshold for each period.
    """
    span_days = (orders["order_date"].max() - orders["order_date"].min()).days
    return {k: span_days >= v for k, v in COVERAGE_THRESHOLDS.items()}


def prior_trailing_window(ref: date, days: int) -> PeriodRange:
    """Prior N-day window ending the day before the current window starts.

    If the current trailing window is ``[ref - days + 1, ref]``, the prior
    window is ``[ref - 2*days + 1, ref - days]``.
    """
    from datetime import timedelta

    current_start = ref - timedelta(days=days - 1)
    prior_end = current_start - timedelta(days=1)
    prior_start = prior_end - timedelta(days=days - 1)
    return PeriodRange(
        label=f"Prior {days} Days",
        start=prior_start,
        end=prior_end,
    )
