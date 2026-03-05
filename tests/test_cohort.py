"""Tests for claude_ecom.cohort."""

import os
import pytest
import pandas as pd

from claude_ecom.loader import load_orders
from claude_ecom.cohort import rfm_segmentation

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
ORDERS_CSV = os.path.join(FIXTURES, "sample_orders.csv")


@pytest.fixture
def orders():
    return load_orders(ORDERS_CSV)


class TestRFMSegmentation:
    def test_returns_dataframe(self, orders):
        rfm = rfm_segmentation(orders)
        assert isinstance(rfm, pd.DataFrame)

    def test_has_segment_column(self, orders):
        rfm = rfm_segmentation(orders)
        assert "segment" in rfm.columns

    def test_valid_segments(self, orders):
        rfm = rfm_segmentation(orders)
        valid = {"Champions", "Loyal", "New Customers", "At Risk", "Lost", "Potential"}
        assert set(rfm["segment"].unique()).issubset(valid)
