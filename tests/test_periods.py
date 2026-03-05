"""Tests for calendar period utilities."""

from datetime import date

from claude_ecom.periods import (
    PeriodRange,
    last_complete_month,
    last_complete_quarter,
    last_complete_year,
    prior_period,
    prior_year_same_period,
    trailing_window,
)


class TestLastCompleteMonth:
    def test_mid_month(self):
        p = last_complete_month(date(2026, 3, 15))
        assert p.start == date(2026, 2, 1)
        assert p.end == date(2026, 2, 28)
        assert p.label == "February 2026"

    def test_first_of_month(self):
        p = last_complete_month(date(2026, 3, 1))
        assert p.start == date(2026, 2, 1)
        assert p.end == date(2026, 2, 28)

    def test_january(self):
        p = last_complete_month(date(2026, 1, 15))
        assert p.start == date(2025, 12, 1)
        assert p.end == date(2025, 12, 31)
        assert p.label == "December 2025"

    def test_leap_year_february(self):
        p = last_complete_month(date(2024, 3, 15))
        assert p.start == date(2024, 2, 1)
        assert p.end == date(2024, 2, 29)

    def test_non_leap_year_february(self):
        p = last_complete_month(date(2025, 3, 10))
        assert p.start == date(2025, 2, 1)
        assert p.end == date(2025, 2, 28)


class TestLastCompleteQuarter:
    def test_mid_q2(self):
        # May 15 is mid-Q2, so last *complete* quarter is Q1
        p = last_complete_quarter(date(2026, 5, 15))
        assert p.start == date(2026, 1, 1)
        assert p.end == date(2026, 3, 31)
        assert p.label == "Q1 2026"

    def test_q2_gives_q1(self):
        p = last_complete_quarter(date(2026, 4, 10))
        assert p.start == date(2026, 1, 1)
        assert p.end == date(2026, 3, 31)
        assert p.label == "Q1 2026"

    def test_q1_gives_q4_prev_year(self):
        p = last_complete_quarter(date(2026, 1, 15))
        assert p.start == date(2025, 10, 1)
        assert p.end == date(2025, 12, 31)
        assert p.label == "Q4 2025"

    def test_q3(self):
        p = last_complete_quarter(date(2026, 9, 1))
        assert p.start == date(2026, 4, 1)
        assert p.end == date(2026, 6, 30)
        assert p.label == "Q2 2026"


class TestLastCompleteYear:
    def test_current(self):
        p = last_complete_year(date(2026, 3, 15))
        assert p.start == date(2025, 1, 1)
        assert p.end == date(2025, 12, 31)
        assert p.label == "2025"


class TestPriorPeriod:
    def test_mbr_prior_month(self):
        feb = PeriodRange("February 2026", date(2026, 2, 1), date(2026, 2, 28))
        p = prior_period(feb, "mbr")
        assert p.start == date(2026, 1, 1)
        assert p.end == date(2026, 1, 31)
        assert p.label == "January 2026"

    def test_qbr_prior_quarter(self):
        q1 = PeriodRange("Q1 2026", date(2026, 1, 1), date(2026, 3, 31))
        p = prior_period(q1, "qbr")
        assert p.start == date(2025, 10, 1)
        assert p.end == date(2025, 12, 31)
        assert p.label == "Q4 2025"

    def test_abr_prior_year(self):
        y2025 = PeriodRange("2025", date(2025, 1, 1), date(2025, 12, 31))
        p = prior_period(y2025, "abr")
        assert p.start == date(2024, 1, 1)
        assert p.end == date(2024, 12, 31)
        assert p.label == "2024"

    def test_mbr_january_wraps_to_december(self):
        jan = PeriodRange("January 2026", date(2026, 1, 1), date(2026, 1, 31))
        p = prior_period(jan, "mbr")
        assert p.start == date(2025, 12, 1)
        assert p.end == date(2025, 12, 31)


class TestPriorYearSamePeriod:
    def test_mbr_yoy(self):
        feb2026 = PeriodRange("February 2026", date(2026, 2, 1), date(2026, 2, 28))
        p = prior_year_same_period(feb2026, "mbr")
        assert p.start == date(2025, 2, 1)
        assert p.end == date(2025, 2, 28)
        assert p.label == "February 2025"

    def test_qbr_yoy(self):
        q1_2026 = PeriodRange("Q1 2026", date(2026, 1, 1), date(2026, 3, 31))
        p = prior_year_same_period(q1_2026, "qbr")
        assert p.start == date(2025, 1, 1)
        assert p.end == date(2025, 3, 31)
        assert p.label == "Q1 2025"


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
