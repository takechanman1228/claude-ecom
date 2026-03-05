"""Tests for claude_ecom.decomposition."""

import os
import pytest

from claude_ecom.loader import load_orders
from claude_ecom.decomposition import waterfall_analysis

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
ORDERS_CSV = os.path.join(FIXTURES, "sample_orders.csv")


@pytest.fixture
def orders():
    return load_orders(ORDERS_CSV)


class TestWaterfallAnalysis:
    def test_returns_result(self, orders):
        result = waterfall_analysis(orders, "2025-03", "2025-06")
        assert hasattr(result, "total_change")
        assert "aov_effect" in result.components
        assert "order_count_effect" in result.components
