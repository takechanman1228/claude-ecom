"""Tests for claude_ecom.site_audit.

All tests use mock PageAuditData — no browser/Playwright required.
"""

import pytest

from claude_ecom.site_audit import (
    PageAuditData,
    build_site_checks,
    build_site_checks_single,
    _trust_signal_count,
)

def _healthy_page(**overrides) -> PageAuditData:
    """Create a PageAuditData with all signals in a healthy state."""
    defaults = dict(
        url="https://example.com",
        page_type="top",
        title="Example Store — Best Products",
        h1="Welcome to Example Store",
        word_count=350,
        image_count=8,
        lcp_ms=1800,
        cls_score=0.05,
        cta_above_fold_desktop=True,
        cta_above_fold_mobile=True,
        cta_best_area=5000.0,
        form_present=True,
        form_field_count=3,
        has_testimonials=True,
        has_trust_badges=True,
        has_reviews=True,
        has_guarantees=False,
        schema_types=["Product", "Organization"],
        has_phone=True,
        has_chat=False,
        has_contact_form=True,
        has_viewport_meta=True,
        has_horizontal_scroll=False,
        base_font_size=16.0,
        has_nav=True,
        logo_links_home=True,
        is_https=True,
        has_payment_badges=True,
        has_privacy_link=True,
    )
    defaults.update(overrides)
    return PageAuditData(**defaults)


class TestTrustSignalCount:
    def test_all_present(self):
        p = _healthy_page(has_testimonials=True, has_trust_badges=True, has_reviews=True, has_guarantees=True)
        assert _trust_signal_count(p) == 4

    def test_none_present(self):
        p = _healthy_page(has_testimonials=False, has_trust_badges=False, has_reviews=False, has_guarantees=False)
        assert _trust_signal_count(p) == 0

    def test_partial(self):
        p = _healthy_page(has_testimonials=False, has_trust_badges=True, has_reviews=True, has_guarantees=False)
        assert _trust_signal_count(p) == 2


class TestBuildSiteChecks:
    """Test SA01-SA15 check generation from PageAuditData."""

    def test_healthy_page_mostly_passes(self):
        page = _healthy_page()
        checks = build_site_checks_single(page)
        results = {c.check_id: c.result for c in checks}
        # All should pass for a healthy page
        for cid, result in results.items():
            assert result == "pass", f"{cid} should pass but got {result}"

    def test_all_checks_have_site_category(self):
        checks = build_site_checks_single(_healthy_page())
        for c in checks:
            assert c.category == "site", f"{c.check_id} has category {c.category}"

    def test_check_ids_are_sa_prefixed(self):
        checks = build_site_checks_single(_healthy_page())
        for c in checks:
            assert c.check_id.startswith("SA"), f"Unexpected check_id: {c.check_id}"

    def test_expected_check_count(self):
        checks = build_site_checks_single(_healthy_page())
        # SA01-SA15, but SA04 only if form present, SA06/SA07 only if perf data
        # With healthy page: all 15 should be present
        assert len(checks) == 15

    # --- SA01: CTA above fold (desktop) ---

    def test_sa01_fail_no_cta_desktop(self):
        page = _healthy_page(cta_above_fold_desktop=False, cta_above_fold_mobile=True)
        checks = build_site_checks_single(page)
        sa01 = next(c for c in checks if c.check_id == "SA01")
        assert sa01.result == "fail"
        assert sa01.severity == "critical"

    def test_sa01_pass_with_cta(self):
        page = _healthy_page(cta_above_fold_desktop=True)
        checks = build_site_checks_single(page)
        sa01 = next(c for c in checks if c.check_id == "SA01")
        assert sa01.result == "pass"

    # --- SA02: CTA contrast & size ---

    def test_sa02_pass_large_cta(self):
        page = _healthy_page(cta_best_area=5000.0)
        checks = build_site_checks_single(page)
        sa02 = next(c for c in checks if c.check_id == "SA02")
        assert sa02.result == "pass"

    def test_sa02_warning_medium_cta(self):
        page = _healthy_page(cta_best_area=2000.0)
        checks = build_site_checks_single(page)
        sa02 = next(c for c in checks if c.check_id == "SA02")
        assert sa02.result == "warning"

    def test_sa02_fail_tiny_cta(self):
        page = _healthy_page(cta_best_area=500.0)
        checks = build_site_checks_single(page)
        sa02 = next(c for c in checks if c.check_id == "SA02")
        assert sa02.result == "fail"

    # --- SA03: Mobile CTA ---

    def test_sa03_fail_no_mobile_cta(self):
        page = _healthy_page(cta_above_fold_mobile=False)
        checks = build_site_checks_single(page)
        sa03 = next(c for c in checks if c.check_id == "SA03")
        assert sa03.result == "fail"
        assert sa03.severity == "critical"

    # --- SA04: Form friction ---

    def test_sa04_pass_few_fields(self):
        page = _healthy_page(form_present=True, form_field_count=3)
        checks = build_site_checks_single(page)
        sa04 = next(c for c in checks if c.check_id == "SA04")
        assert sa04.result == "pass"

    def test_sa04_warning_moderate_fields(self):
        page = _healthy_page(form_present=True, form_field_count=7)
        checks = build_site_checks_single(page)
        sa04 = next(c for c in checks if c.check_id == "SA04")
        assert sa04.result == "warning"

    def test_sa04_fail_many_fields(self):
        page = _healthy_page(form_present=True, form_field_count=12)
        checks = build_site_checks_single(page)
        sa04 = next(c for c in checks if c.check_id == "SA04")
        assert sa04.result == "fail"

    def test_sa04_skipped_no_form(self):
        page = _healthy_page(form_present=False)
        checks = build_site_checks_single(page)
        sa04_checks = [c for c in checks if c.check_id == "SA04"]
        assert len(sa04_checks) == 0

    # --- SA05: Mobile responsiveness ---

    def test_sa05_fail_no_viewport(self):
        page = _healthy_page(has_viewport_meta=False)
        checks = build_site_checks_single(page)
        sa05 = next(c for c in checks if c.check_id == "SA05")
        assert sa05.result == "fail"
        assert sa05.severity == "critical"

    def test_sa05_fail_horizontal_scroll(self):
        page = _healthy_page(has_horizontal_scroll=True)
        checks = build_site_checks_single(page)
        sa05 = next(c for c in checks if c.check_id == "SA05")
        assert sa05.result == "fail"

    # --- SA06: Page speed (LCP) ---

    def test_sa06_pass_fast(self):
        page = _healthy_page(lcp_ms=1500)
        checks = build_site_checks_single(page)
        sa06 = next(c for c in checks if c.check_id == "SA06")
        assert sa06.result == "pass"

    def test_sa06_warning_moderate(self):
        page = _healthy_page(lcp_ms=3000)
        checks = build_site_checks_single(page)
        sa06 = next(c for c in checks if c.check_id == "SA06")
        assert sa06.result == "warning"

    def test_sa06_fail_slow(self):
        page = _healthy_page(lcp_ms=5000)
        checks = build_site_checks_single(page)
        sa06 = next(c for c in checks if c.check_id == "SA06")
        assert sa06.result == "fail"

    def test_sa06_skipped_no_data(self):
        page = _healthy_page(lcp_ms=None)
        checks = build_site_checks_single(page)
        sa06_checks = [c for c in checks if c.check_id == "SA06"]
        assert len(sa06_checks) == 0

    # --- SA07: Layout shift (CLS) ---

    def test_sa07_pass_low_cls(self):
        page = _healthy_page(cls_score=0.05)
        checks = build_site_checks_single(page)
        sa07 = next(c for c in checks if c.check_id == "SA07")
        assert sa07.result == "pass"

    def test_sa07_warning_moderate_cls(self):
        page = _healthy_page(cls_score=0.15)
        checks = build_site_checks_single(page)
        sa07 = next(c for c in checks if c.check_id == "SA07")
        assert sa07.result == "warning"

    def test_sa07_fail_high_cls(self):
        page = _healthy_page(cls_score=0.30)
        checks = build_site_checks_single(page)
        sa07 = next(c for c in checks if c.check_id == "SA07")
        assert sa07.result == "fail"

    # --- SA08: Trust signals ---

    def test_sa08_pass_multiple_signals(self):
        page = _healthy_page(has_reviews=True, has_trust_badges=True)
        checks = build_site_checks_single(page)
        sa08 = next(c for c in checks if c.check_id == "SA08")
        assert sa08.result == "pass"

    def test_sa08_warning_one_signal(self):
        page = _healthy_page(
            has_testimonials=False, has_trust_badges=False,
            has_reviews=True, has_guarantees=False,
        )
        checks = build_site_checks_single(page)
        sa08 = next(c for c in checks if c.check_id == "SA08")
        assert sa08.result == "warning"

    def test_sa08_fail_no_signals(self):
        page = _healthy_page(
            has_testimonials=False, has_trust_badges=False,
            has_reviews=False, has_guarantees=False,
        )
        checks = build_site_checks_single(page)
        sa08 = next(c for c in checks if c.check_id == "SA08")
        assert sa08.result == "fail"

    # --- SA09: Schema markup ---

    def test_sa09_pass_with_product_schema(self):
        page = _healthy_page(schema_types=["Product"])
        checks = build_site_checks_single(page)
        sa09 = next(c for c in checks if c.check_id == "SA09")
        assert sa09.result == "pass"

    def test_sa09_fail_no_schema(self):
        page = _healthy_page(schema_types=[])
        checks = build_site_checks_single(page)
        sa09 = next(c for c in checks if c.check_id == "SA09")
        assert sa09.result == "fail"

    # --- SA10: Contact/support access ---

    def test_sa10_pass_with_phone(self):
        page = _healthy_page(has_phone=True, has_chat=False, has_contact_form=False)
        checks = build_site_checks_single(page)
        sa10 = next(c for c in checks if c.check_id == "SA10")
        assert sa10.result == "pass"

    def test_sa10_fail_no_contact(self):
        page = _healthy_page(has_phone=False, has_chat=False, has_contact_form=False)
        checks = build_site_checks_single(page)
        sa10 = next(c for c in checks if c.check_id == "SA10")
        assert sa10.result == "fail"

    # --- SA11: H1 heading ---

    def test_sa11_pass_with_h1(self):
        page = _healthy_page(h1="Welcome")
        checks = build_site_checks_single(page)
        sa11 = next(c for c in checks if c.check_id == "SA11")
        assert sa11.result == "pass"

    def test_sa11_fail_no_h1(self):
        page = _healthy_page(h1="")
        checks = build_site_checks_single(page)
        sa11 = next(c for c in checks if c.check_id == "SA11")
        assert sa11.result == "fail"

    # --- SA12: Image count ---

    def test_sa12_pass_normal_count(self):
        page = _healthy_page(image_count=10)
        checks = build_site_checks_single(page)
        sa12 = next(c for c in checks if c.check_id == "SA12")
        assert sa12.result == "pass"

    def test_sa12_warning_one_image(self):
        page = _healthy_page(image_count=1)
        checks = build_site_checks_single(page)
        sa12 = next(c for c in checks if c.check_id == "SA12")
        assert sa12.result == "warning"

    def test_sa12_fail_no_images(self):
        page = _healthy_page(image_count=0)
        checks = build_site_checks_single(page)
        sa12 = next(c for c in checks if c.check_id == "SA12")
        assert sa12.result == "fail"

    def test_sa12_fail_too_many(self):
        page = _healthy_page(image_count=35)
        checks = build_site_checks_single(page)
        sa12 = next(c for c in checks if c.check_id == "SA12")
        assert sa12.result == "fail"

    # --- SA13: Security indicators ---

    def test_sa13_pass_https_with_payment(self):
        page = _healthy_page(is_https=True, has_payment_badges=True, has_privacy_link=True)
        checks = build_site_checks_single(page)
        sa13 = next(c for c in checks if c.check_id == "SA13")
        assert sa13.result == "pass"

    def test_sa13_warning_https_only(self):
        page = _healthy_page(is_https=True, has_payment_badges=False, has_privacy_link=False)
        checks = build_site_checks_single(page)
        sa13 = next(c for c in checks if c.check_id == "SA13")
        assert sa13.result == "warning"

    def test_sa13_fail_no_https(self):
        page = _healthy_page(is_https=False)
        checks = build_site_checks_single(page)
        sa13 = next(c for c in checks if c.check_id == "SA13")
        assert sa13.result == "fail"

    # --- SA14: Navigation consistency ---

    def test_sa14_pass_nav_with_logo(self):
        page = _healthy_page(has_nav=True, logo_links_home=True)
        checks = build_site_checks_single(page)
        sa14 = next(c for c in checks if c.check_id == "SA14")
        assert sa14.result == "pass"

    def test_sa14_warning_nav_no_logo(self):
        page = _healthy_page(has_nav=True, logo_links_home=False)
        checks = build_site_checks_single(page)
        sa14 = next(c for c in checks if c.check_id == "SA14")
        assert sa14.result == "warning"

    def test_sa14_fail_no_nav(self):
        page = _healthy_page(has_nav=False)
        checks = build_site_checks_single(page)
        sa14 = next(c for c in checks if c.check_id == "SA14")
        assert sa14.result == "fail"

    # --- SA15: Font readability ---

    def test_sa15_pass_good_font(self):
        page = _healthy_page(base_font_size=16.0)
        checks = build_site_checks_single(page)
        sa15 = next(c for c in checks if c.check_id == "SA15")
        assert sa15.result == "pass"

    def test_sa15_warning_small_font(self):
        page = _healthy_page(base_font_size=14.5)
        checks = build_site_checks_single(page)
        sa15 = next(c for c in checks if c.check_id == "SA15")
        assert sa15.result == "warning"

    def test_sa15_fail_tiny_font(self):
        page = _healthy_page(base_font_size=12.0)
        checks = build_site_checks_single(page)
        sa15 = next(c for c in checks if c.check_id == "SA15")
        assert sa15.result == "fail"

    # --- Error handling ---

    def test_error_page_returns_single_fail(self):
        page = PageAuditData(url="https://blocked.com", error="Bot block detected")
        checks = build_site_checks_single(page)
        assert len(checks) == 1
        assert checks[0].check_id == "SA01"
        assert checks[0].result == "fail"

    def test_empty_pages_returns_empty(self):
        checks = build_site_checks([])
        assert checks == []


class TestMultiPage:
    """Test multi-page aggregation logic."""

    def test_worst_lcp_used(self):
        fast = _healthy_page(lcp_ms=1000)
        slow = _healthy_page(lcp_ms=5000)
        checks = build_site_checks([fast, slow])
        sa06 = next(c for c in checks if c.check_id == "SA06")
        assert sa06.result == "fail"
        assert sa06.current_value == 5000

    def test_best_trust_used(self):
        poor = _healthy_page(
            has_testimonials=False, has_trust_badges=False,
            has_reviews=False, has_guarantees=False,
        )
        rich = _healthy_page(
            has_testimonials=True, has_trust_badges=True,
            has_reviews=True, has_guarantees=True,
        )
        checks = build_site_checks([poor, rich])
        sa08 = next(c for c in checks if c.check_id == "SA08")
        assert sa08.result == "pass"

    def test_any_cta_sufficient(self):
        no_cta = _healthy_page(cta_above_fold_desktop=False)
        has_cta = _healthy_page(cta_above_fold_desktop=True)
        checks = build_site_checks([no_cta, has_cta])
        sa01 = next(c for c in checks if c.check_id == "SA01")
        assert sa01.result == "pass"

    def test_nav_consistency_all_must_have(self):
        good = _healthy_page(has_nav=True)
        bad = _healthy_page(has_nav=False)
        checks = build_site_checks([good, bad])
        sa14 = next(c for c in checks if c.check_id == "SA14")
        assert sa14.result == "fail"

    def test_error_pages_filtered(self):
        good = _healthy_page()
        error = PageAuditData(url="https://err.com", error="Timeout")
        checks = build_site_checks([good, error])
        # Should still produce all checks from the good page
        assert len(checks) == 15
