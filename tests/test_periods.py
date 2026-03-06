"""Tests for calendar period utilities."""

from datetime import date

import pandas as pd

from claude_ecom.periods import (
    compute_data_coverage,
    prior_trailing_window,
    trailing_window,
)


class TestTrailingWindow:
    def test_30_day(self):
        p = trailing_window(date(2026, 3, 15), 30)
        assert p.start == date(2026, 2, 14)
        assert p.end == date(2026, 3, 15)
        assert p.label == "Past 30 Days"

    def test_90_day(self):
        p = trailing_window(date(2026, 3, 15), 90)
        assert p.start == date(2025, 12, 16)
        assert p.end == date(2026, 3, 15)
        assert p.label == "Past 90 Days"


class TestComputeDataCoverage:
    def test_short_data_only_30d(self):
        df = pd.DataFrame(
            {
                "order_date": pd.to_datetime(["2025-06-01", "2025-08-01"]),
            }
        )
        cov = compute_data_coverage(df)
        assert cov["30d"] is True  # 61 days >= 45
        assert cov["90d"] is False  # 61 days < 120
        assert cov["365d"] is False

    def test_medium_data_30d_90d(self):
        df = pd.DataFrame(
            {
                "order_date": pd.to_datetime(["2025-01-01", "2025-06-01"]),
            }
        )
        cov = compute_data_coverage(df)
        assert cov["30d"] is True
        assert cov["90d"] is True  # 151 days >= 120
        assert cov["365d"] is False

    def test_long_data_all_periods(self):
        df = pd.DataFrame(
            {
                "order_date": pd.to_datetime(["2024-01-01", "2025-06-01"]),
            }
        )
        cov = compute_data_coverage(df)
        assert cov["30d"] is True
        assert cov["90d"] is True
        assert cov["365d"] is True  # 517 days >= 400

    def test_very_short_data_none(self):
        df = pd.DataFrame(
            {
                "order_date": pd.to_datetime(["2025-06-01", "2025-06-30"]),
            }
        )
        cov = compute_data_coverage(df)
        assert cov["30d"] is False  # 29 days < 45
        assert cov["90d"] is False
        assert cov["365d"] is False


class TestPriorTrailingWindow:
    def test_30_day_prior(self):
        p = prior_trailing_window(date(2026, 3, 15), 30)
        # Current window: [2026-02-14, 2026-03-15]
        # Prior window: [2026-01-15, 2026-02-13]
        assert p.end == date(2026, 2, 13)
        assert p.start == date(2026, 1, 15)
        assert p.label == "Prior 30 Days"

    def test_90_day_prior(self):
        p = prior_trailing_window(date(2026, 3, 15), 90)
        # Current window: [2025-12-16, 2026-03-15]
        # Prior window: [2025-09-17, 2025-12-15]
        assert p.end == date(2025, 12, 15)
        assert p.start == date(2025, 9, 17)
        assert p.label == "Prior 90 Days"

    def test_windows_dont_overlap(self):
        ref = date(2026, 3, 15)
        current = trailing_window(ref, 30)
        prior = prior_trailing_window(ref, 30)
        assert prior.end < current.start
