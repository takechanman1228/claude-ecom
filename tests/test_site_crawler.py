"""Tests for ecom_analytics.site_crawler.

All tests use mock data — no browser/Playwright required.
"""

import pytest

from ecom_analytics.site_crawler import (
    CrawlConfig,
    CrawlResult,
    detect_page_type,
    _normalize_url,
    _PAGE_PRIORITY,
)


class TestDetectPageType:
    @pytest.mark.parametrize(
        "url, expected",
        [
            ("https://shop.com/", "top"),
            ("https://shop.com", "top"),
            ("https://shop.com/collections/shoes", "collection"),
            ("https://shop.com/category/womens", "collection"),
            ("https://shop.com/shop/hats", "collection"),
            ("https://shop.com/products/blue-widget", "pdp"),
            ("https://shop.com/product/123", "pdp"),
            ("https://shop.com/item/sku-456", "pdp"),
            ("https://shop.com/dp/B001234", "pdp"),
            ("https://shop.com/cart", "cart"),
            ("https://shop.com/basket", "cart"),
            ("https://shop.com/checkout", "checkout"),
            ("https://shop.com/about", "about"),
            ("https://shop.com/about-us", "about"),
            ("https://shop.com/our-story", "about"),
            ("https://shop.com/contact", "contact"),
            ("https://shop.com/contact-us", "contact"),
            ("https://shop.com/support", "contact"),
            ("https://shop.com/help", "contact"),
            ("https://shop.com/faq", "faq"),
            ("https://shop.com/frequently-asked-questions", "faq"),
            ("https://shop.com/shipping-info", "shipping"),
            ("https://shop.com/delivery", "shipping"),
            ("https://shop.com/returns", "shipping"),
            ("https://shop.com/privacy-policy", "privacy"),
            ("https://shop.com/terms-of-service", "privacy"),
            ("https://shop.com/blog/post-1", "blog"),
            ("https://shop.com/account/orders", "account"),
            ("https://shop.com/login", "account"),
            ("https://shop.com/random-page", "other"),
        ],
    )
    def test_page_type_detection(self, url, expected):
        assert detect_page_type(url) == expected


class TestNormalizeUrl:
    def test_strips_trailing_slash(self):
        assert _normalize_url("https://shop.com/page/") == "https://shop.com/page"

    def test_strips_fragment(self):
        assert _normalize_url("https://shop.com/page#section") == "https://shop.com/page"

    def test_preserves_root(self):
        assert _normalize_url("https://shop.com/") == "https://shop.com/"

    def test_preserves_path(self):
        assert _normalize_url("https://shop.com/a/b/c") == "https://shop.com/a/b/c"


class TestCrawlConfig:
    def test_defaults(self):
        config = CrawlConfig()
        assert config.max_pages == 20
        assert config.timeout_per_page == 30000
        assert config.respect_robots is True
        assert config.screenshot_dir is None

    def test_custom(self):
        config = CrawlConfig(max_pages=5, timeout_per_page=10000, respect_robots=False)
        assert config.max_pages == 5
        assert config.timeout_per_page == 10000
        assert config.respect_robots is False


class TestCrawlResult:
    def test_empty_result(self):
        result = CrawlResult(base_url="https://shop.com")
        assert result.base_url == "https://shop.com"
        assert result.pages == []
        assert result.skipped_urls == []
        assert result.errors == []


class TestPagePriority:
    def test_top_has_highest_priority(self):
        assert _PAGE_PRIORITY["top"] == 0

    def test_pdp_before_blog(self):
        assert _PAGE_PRIORITY["pdp"] < _PAGE_PRIORITY["blog"]

    def test_collection_before_contact(self):
        assert _PAGE_PRIORITY["collection"] < _PAGE_PRIORITY["contact"]

    def test_account_is_low_priority(self):
        assert _PAGE_PRIORITY["account"] > _PAGE_PRIORITY["pdp"]
