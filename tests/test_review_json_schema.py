"""Tests for review.json schema stability.

review.json is the contract between the Python compute engine and the LLM
interpretation layer. If the schema breaks, the LLM cannot interpret results.
"""

import json
import math
import os

import pytest

from claude_ecom.review_engine import build_review_data
from claude_ecom.loader import load_orders

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
ORDERS_CSV = os.path.join(FIXTURES_DIR, "sample_orders.csv")


@pytest.fixture
def review_data():
    orders = load_orders(ORDERS_CSV)
    return build_review_data(orders)


class TestReviewJsonTopLevel:
    """Top-level fields that the LLM reads first."""

    def test_has_required_top_level_fields(self, review_data):
        required = {"version", "metadata", "data_coverage", "periods", "health", "action_candidates"}
        assert required.issubset(set(review_data.keys()))


class TestReviewJsonHealth:
    """Health section schema."""

    def test_checks_is_list(self, review_data):
        checks = review_data["health"]["checks"]
        assert isinstance(checks, list)
        assert len(checks) > 0

    def test_each_check_has_required_fields(self, review_data):
        required = {"id", "category", "severity", "result", "message"}
        for check in review_data["health"]["checks"]:
            missing = required - set(check.keys())
            assert not missing, f"Check {check.get('id', '?')} missing: {missing}"

    def test_result_values_include_watch(self, review_data):
        valid_results = {"pass", "watch", "warning", "fail", "na"}
        for check in review_data["health"]["checks"]:
            assert check["result"] in valid_results, f"{check['id']} invalid result: {check['result']}"

class TestReviewJsonNoNaN:
    """Ensure review data never contains NaN -- breaks JSON parsing."""

    def _check_no_nan(self, obj, path=""):
        if isinstance(obj, float):
            assert not math.isnan(obj), f"NaN at {path}"
            assert not math.isinf(obj), f"Infinity at {path}"
        elif isinstance(obj, dict):
            for k, v in obj.items():
                self._check_no_nan(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                self._check_no_nan(v, f"{path}[{i}]")

    def test_no_nan_or_infinity(self, review_data):
        from claude_ecom.report import _sanitize_for_json
        sanitized = _sanitize_for_json(review_data)
        self._check_no_nan(sanitized)

    def test_json_serializable(self, review_data):
        from claude_ecom.report import _sanitize_for_json
        sanitized = _sanitize_for_json(review_data)
        content = json.dumps(sanitized, default=str)
        assert "NaN" not in content
        assert "Infinity" not in content
