"""Tests for report generation."""

import os
from datetime import date

import pytest

from claude_ecom.loader import load_orders
from claude_ecom.report import generate_business_review, generate_review
from claude_ecom.review_engine import build_review_data

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
ORDERS_CSV = os.path.join(FIXTURES_DIR, "sample_orders.csv")


@pytest.fixture
def orders():
    return load_orders(ORDERS_CSV)


class TestGenerateBusinessReview:
    def test_creates_file(self, orders, tmp_path):
        data = build_review_data(orders, "general", ref_date=date(2025, 7, 15))
        path = generate_business_review(data, output_dir=str(tmp_path))
        assert os.path.exists(path)
        assert path.endswith("BUSINESS-REVIEW-REPORT.md")

    def test_contains_sections(self, orders, tmp_path):
        data = build_review_data(orders, "general", ref_date=date(2025, 7, 15))
        path = generate_business_review(data, output_dir=str(tmp_path))
        content = open(path).read()
        assert "## 1. Executive Summary" in content
        assert "## 2. KPI Dashboard" in content
        assert "## 7. Risk Assessment" in content
        assert "## 8. Recommendations" in content
        assert "## 9. Trailing Temperature Check" in content


class TestGenerateReviewNewFilenames:
    def test_mbr_filename(self, orders, tmp_path):
        data = build_review_data(orders, "mbr", ref_date=date(2025, 7, 15))
        path = generate_review(data, "mbr", output_dir=str(tmp_path))
        assert path.endswith("BUSINESS-REVIEW-MBR.md")

    def test_qbr_filename(self, orders, tmp_path):
        data = build_review_data(orders, "qbr", ref_date=date(2025, 7, 15))
        path = generate_review(data, "qbr", output_dir=str(tmp_path))
        assert path.endswith("BUSINESS-REVIEW-QBR.md")

    def test_abr_filename(self, orders, tmp_path):
        data = build_review_data(orders, "abr", ref_date=date(2026, 1, 15))
        path = generate_review(data, "abr", output_dir=str(tmp_path))
        assert path.endswith("BUSINESS-REVIEW-ABR.md")

    def test_mbr_has_next_month_actions(self, orders, tmp_path):
        data = build_review_data(orders, "mbr", ref_date=date(2025, 7, 15))
        path = generate_review(data, "mbr", output_dir=str(tmp_path))
        content = open(path).read()
        assert "## 7. Next Month Actions" in content

    def test_qbr_has_risk_and_recommendations(self, orders, tmp_path):
        data = build_review_data(orders, "qbr", ref_date=date(2025, 7, 15))
        path = generate_review(data, "qbr", output_dir=str(tmp_path))
        content = open(path).read()
        assert "## 7. Risk Assessment" in content
        assert "## 8. Recommendations" in content

    def test_abr_has_growth_drivers(self, orders, tmp_path):
        data = build_review_data(orders, "abr", ref_date=date(2026, 1, 15))
        path = generate_review(data, "abr", output_dir=str(tmp_path))
        content = open(path).read()
        assert "Annual Growth Drivers" in content or "12-Month KPI Trend" in content
        assert "## 8. Risk Assessment" in content
        assert "## 9. Annual Strategy Recommendations" in content
