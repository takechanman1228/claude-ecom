"""Calendar period utilities for business reviews (MBR / QBR / ABR)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class PeriodRange:
    """A labelled date range representing a business period."""

    label: str  # e.g. "February 2026", "Q1 2026", "2025"
    start: date
    end: date


def last_complete_month(ref: date | None = None) -> PeriodRange:
    """Return the most recently completed calendar month."""
    ref = ref or date.today()
    # Go to first of current month, then back one day → last day of prev month
    first_of_month = ref.replace(day=1)
    end = first_of_month.replace(day=1)  # same as first_of_month
    # Last day of previous month
    end = date(first_of_month.year, first_of_month.month, 1)
    if first_of_month.month == 1:
        start = date(first_of_month.year - 1, 12, 1)
        end = date(first_of_month.year - 1, 12, 31)
    else:
        import calendar

        prev_month = first_of_month.month - 1
        prev_year = first_of_month.year
        start = date(prev_year, prev_month, 1)
        last_day = calendar.monthrange(prev_year, prev_month)[1]
        end = date(prev_year, prev_month, last_day)

    label = start.strftime("%B %Y")
    return PeriodRange(label=label, start=start, end=end)


def last_complete_quarter(ref: date | None = None) -> PeriodRange:
    """Return the most recently completed calendar quarter."""
    ref = ref or date.today()
    # Current quarter: Q1=1-3, Q2=4-6, Q3=7-9, Q4=10-12
    current_q = (ref.month - 1) // 3 + 1
    if current_q == 1:
        # Previous quarter is Q4 of last year
        return PeriodRange(
            label=f"Q4 {ref.year - 1}",
            start=date(ref.year - 1, 10, 1),
            end=date(ref.year - 1, 12, 31),
        )
    else:
        prev_q = current_q - 1
        start_month = (prev_q - 1) * 3 + 1
        end_month = prev_q * 3
        import calendar

        last_day = calendar.monthrange(ref.year, end_month)[1]
        return PeriodRange(
            label=f"Q{prev_q} {ref.year}",
            start=date(ref.year, start_month, 1),
            end=date(ref.year, end_month, last_day),
        )


def last_complete_year(ref: date | None = None) -> PeriodRange:
    """Return the most recently completed calendar year."""
    ref = ref or date.today()
    prev_year = ref.year - 1
    return PeriodRange(
        label=str(prev_year),
        start=date(prev_year, 1, 1),
        end=date(prev_year, 12, 31),
    )


def prior_period(period: PeriodRange, cadence: str) -> PeriodRange:
    """Return the previous period of the same cadence.

    MBR → previous month, QBR → previous quarter, ABR → previous year.
    """
    if cadence == "mbr":
        return last_complete_month(period.start)
    elif cadence == "qbr":
        return last_complete_quarter(period.start)
    elif cadence == "abr":
        return last_complete_year(period.start)
    raise ValueError(f"Unknown cadence: {cadence}")


def prior_year_same_period(period: PeriodRange, cadence: str) -> PeriodRange:
    """Return the same period one year ago.

    MBR → same month last year, QBR → same quarter last year.
    """
    import calendar

    if cadence == "mbr":
        start = date(period.start.year - 1, period.start.month, 1)
        last_day = calendar.monthrange(start.year, start.month)[1]
        end = date(start.year, start.month, last_day)
        label = start.strftime("%B %Y")
        return PeriodRange(label=label, start=start, end=end)
    elif cadence == "qbr":
        start = date(period.start.year - 1, period.start.month, 1)
        end_month = period.end.month
        last_day = calendar.monthrange(period.end.year - 1, end_month)[1]
        end = date(period.end.year - 1, end_month, last_day)
        q_num = (start.month - 1) // 3 + 1
        label = f"Q{q_num} {start.year}"
        return PeriodRange(label=label, start=start, end=end)
    raise ValueError(f"prior_year_same_period not applicable for cadence: {cadence}")


def trailing_window(ref: date, days: int) -> PeriodRange:
    """Trailing N-day window ending at ref (inclusive)."""
    from datetime import timedelta

    start = ref - timedelta(days=days - 1)
    return PeriodRange(
        label=f"Past {days} Days",
        start=start,
        end=ref,
    )
