"""Tests for report generation."""

import json
import os
from datetime import date

import pytest

from claude_ecom.loader import load_orders
from claude_ecom.report import generate_review_json, _sanitize_for_json
from claude_ecom.review_engine import build_review_data

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
ORDERS_CSV = os.path.join(FIXTURES_DIR, "sample_orders.csv")


@pytest.fixture
def orders():
    return load_orders(ORDERS_CSV)


class TestGenerateReviewJson:
    def test_creates_file(self, orders, tmp_path):
        data = build_review_data(orders)
        path = generate_review_json(data, output_dir=str(tmp_path))
        assert os.path.exists(path)
        assert path.endswith("review.json")

    def test_valid_json(self, orders, tmp_path):
        data = build_review_data(orders)
        path = generate_review_json(data, output_dir=str(tmp_path))
        with open(path) as f:
            parsed = json.load(f)
        assert "version" in parsed
        assert "metadata" in parsed
        assert "data_coverage" in parsed
        assert "periods" in parsed
        assert "health" in parsed
        assert "action_candidates" in parsed

    def test_health_structure(self, orders, tmp_path):
        data = build_review_data(orders)
        path = generate_review_json(data, output_dir=str(tmp_path))
        with open(path) as f:
            parsed = json.load(f)
        health = parsed["health"]
        assert "category_scores" in health
        assert "checks" in health
        assert "top_issues" in health

    def test_no_nan_in_output(self, orders, tmp_path):
        data = build_review_data(orders)
        path = generate_review_json(data, output_dir=str(tmp_path))
        content = open(path).read()
        assert "NaN" not in content
        assert "Infinity" not in content


class TestSanitizeForJson:
    def test_replaces_nan(self):
        result = _sanitize_for_json({"a": float("nan")})
        assert result["a"] is None

    def test_replaces_infinity(self):
        result = _sanitize_for_json({"a": float("inf")})
        assert result["a"] is None

    def test_preserves_normal_values(self):
        result = _sanitize_for_json({"a": 42, "b": "hello", "c": 3.14})
        assert result == {"a": 42, "b": "hello", "c": 3.14}

    def test_handles_nested(self):
        result = _sanitize_for_json({"a": {"b": float("nan")}, "c": [float("inf"), 1]})
        assert result["a"]["b"] is None
        assert result["c"][0] is None
        assert result["c"][1] == 1
