"""Site / landing page quality audit using Playwright.

Analyzes page quality signals (CTA visibility, form friction, trust signals,
Core Web Vitals, mobile responsiveness, schema markup) and produces SA01-SA15
check results compatible with the claude-ecom scoring system.

Playwright is an optional dependency — install with:
    pip install claude-ecom[site]
"""
# NOTE: Not used by the current review flow. Kept for future integration.

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from .checks import CheckResult


@dataclass
class PageAuditData:
    """Raw signals collected from a single page."""

    url: str
    page_type: str = "top"  # top, lp, collection, pdp, cart, about, contact, etc.

    # Content
    title: str = ""
    h1: str = ""
    meta_description: str = ""
    word_count: int = 0
    image_count: int = 0

    # Performance
    lcp_ms: float | None = None
    cls_score: float | None = None
    ttfb_ms: float | None = None

    # CTA
    cta_above_fold_desktop: bool = False
    cta_above_fold_mobile: bool = False
    cta_best_area: float = 0.0  # bounding box area in px²

    # Forms
    form_present: bool = False
    form_field_count: int = 0

    # Trust signals
    has_testimonials: bool = False
    has_trust_badges: bool = False
    has_reviews: bool = False
    has_guarantees: bool = False

    # Schema
    schema_types: list[str] = field(default_factory=list)

    # Contact
    has_phone: bool = False
    has_chat: bool = False
    has_contact_form: bool = False

    # Mobile
    has_viewport_meta: bool = True
    has_horizontal_scroll: bool = False
    base_font_size: float = 16.0

    # Navigation
    has_nav: bool = True
    logo_links_home: bool = True

    # Security
    is_https: bool = True
    has_payment_badges: bool = False
    has_privacy_link: bool = False

    # Screenshots
    desktop_screenshot: str = ""
    mobile_screenshot: str = ""

    # Error
    error: str = ""


def check_playwright_available() -> None:
    """Raise ImportError with install instructions if Playwright is not available."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        raise ImportError(
            "Playwright is required for site audits. Install with:\n"
            "  pip install claude-ecom[site]\n"
            "  playwright install chromium"
        )


# ---------------------------------------------------------------------------
# CTA selectors — ecommerce-expanded
# ---------------------------------------------------------------------------

_CTA_SELECTORS = [
    # Ecommerce
    "button:has-text('Add to Cart')",
    "button:has-text('Buy Now')",
    "button:has-text('Shop Now')",
    "button:has-text('Order Now')",
    "[class*='add-to-cart']",
    "[class*='buy-now']",
    "[data-action='add-to-cart']",
    # General CTA
    "a[href*='signup']",
    "a[href*='register']",
    "button:has-text('Get Started')",
    "button:has-text('Sign Up')",
    "button:has-text('Free Trial')",
    "button:has-text('Book')",
    "button:has-text('Contact')",
    "button:has-text('Subscribe')",
    ".cta",
    "[class*='cta']",
    # Links with CTA-like paths
    "a[href*='buy']",
    "a[href*='demo']",
    "a[href*='trial']",
    "a[href*='contact']",
]

_COOKIE_SELECTORS = [
    "[class*='cookie'] button",
    "[class*='consent'] button",
    "[id*='cookie'] button",
    "#onetrust-accept-btn-handler",
    ".cc-dismiss",
    "[class*='cookie-banner'] button",
    "button:has-text('Accept')",
    "button:has-text('Got it')",
    "button:has-text('OK')",
]

_CHAT_SELECTORS = [
    "[class*='chat']",
    "[id*='chat']",
    "[class*='intercom']",
    "[class*='drift']",
    "[class*='hubspot']",
    "[class*='zendesk']",
    "[class*='tidio']",
    "[class*='crisp']",
    "[class*='tawk']",
]


def _dismiss_cookie_banners(page) -> None:
    """Try to dismiss cookie banners using common selectors."""
    for selector in _COOKIE_SELECTORS:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(500)
                return
        except Exception:
            continue


def _detect_bot_block(page) -> bool:
    """Detect common bot-blocking patterns (Cloudflare, captcha, 403)."""
    try:
        title = page.title().lower()
        body_text = page.evaluate("() => (document.body.innerText || '').substring(0, 2000).toLowerCase()")

        bot_signals = [
            "just a moment" in title,  # Cloudflare
            "attention required" in title,
            "access denied" in title,
            "403 forbidden" in title,
            "captcha" in body_text,
            "verify you are human" in body_text,
            "checking your browser" in body_text,
            "ray id" in body_text and "cloudflare" in body_text,
        ]
        return any(bot_signals)
    except Exception:
        return False


def analyze_page(
    url: str,
    page_type: str = "top",
    timeout: int = 30000,
    screenshot_dir: str | None = None,
) -> PageAuditData:
    """Analyze a single page using Playwright and return raw signals.

    Opens headless Chromium with desktop (1920x1080) and mobile (375x812)
    viewports. Measures CTA visibility, content quality, performance metrics,
    trust signals, schema markup, and mobile responsiveness.
    """
    check_playwright_available()
    from playwright.sync_api import sync_playwright

    data = PageAuditData(url=url, page_type=page_type)
    parsed = urlparse(url)
    data.is_https = parsed.scheme == "https"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # --- Desktop pass ---
            desktop_ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = desktop_ctx.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout)

            # Bot block check
            if _detect_bot_block(page):
                data.error = "Bot block detected (Cloudflare/captcha/403)"
                desktop_ctx.close()
                browser.close()
                return data

            _dismiss_cookie_banners(page)

            # Content
            data.title = page.title() or ""
            h1 = page.query_selector("h1")
            if h1:
                data.h1 = (h1.text_content() or "").strip()

            meta_desc = page.query_selector('meta[name="description"]')
            if meta_desc:
                data.meta_description = meta_desc.get_attribute("content") or ""

            data.word_count = page.evaluate(
                "() => document.body.innerText.split(/\\s+/).filter(w => w.length > 0).length"
            )
            data.image_count = page.evaluate("() => document.querySelectorAll('img').length")

            # CTA detection (desktop)
            best_area = 0.0
            for selector in _CTA_SELECTORS:
                try:
                    cta = page.query_selector(selector)
                    if cta:
                        box = cta.bounding_box()
                        if box:
                            area = box["width"] * box["height"]
                            if area > best_area:
                                best_area = area
                            if box["y"] < 1080:
                                data.cta_above_fold_desktop = True
                except Exception:
                    continue
            data.cta_best_area = best_area

            # Forms
            forms = page.query_selector_all("form")
            if forms:
                data.form_present = True
                inputs = page.query_selector_all(
                    "form input:not([type='hidden']):not([type='submit']):not([type='button'])"
                )
                data.form_field_count = len(inputs)
                # Check textareas and selects too
                textareas = page.query_selector_all("form textarea")
                selects = page.query_selector_all("form select")
                data.form_field_count += len(textareas) + len(selects)

            # Trust signals
            page_text = page.evaluate("() => document.body.innerText.toLowerCase()")
            data.has_testimonials = any(
                k in page_text for k in ["testimonial", "customer said", "what our customers", "client says"]
            )
            data.has_trust_badges = any(
                k in page_text for k in ["trusted by", "as seen", "certified", "award", "secure checkout"]
            )
            data.has_reviews = any(k in page_text for k in ["review", "rating", "stars", "★"])
            data.has_guarantees = any(
                k in page_text for k in ["guarantee", "money back", "free returns", "free shipping", "satisfaction"]
            )

            # Contact signals
            data.has_phone = page.query_selector("a[href^='tel:']") is not None
            for sel in _CHAT_SELECTORS:
                try:
                    if page.query_selector(sel):
                        data.has_chat = True
                        break
                except Exception:
                    continue
            # Contact form detection (form with email/message fields)
            contact_form = page.query_selector("form[action*='contact']")
            if not contact_form:
                contact_form = page.query_selector("form#contact")
            data.has_contact_form = contact_form is not None or data.form_present

            # Schema markup
            schemas = page.evaluate("""
                () => {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    const types = [];
                    scripts.forEach(s => {
                        try {
                            const data = JSON.parse(s.textContent);
                            if (data['@type']) types.push(data['@type']);
                            if (Array.isArray(data['@graph'])) {
                                data['@graph'].forEach(item => { if (item['@type']) types.push(item['@type']); });
                            }
                        } catch(e) {}
                    });
                    return types;
                }
            """)
            data.schema_types = schemas or []

            # Navigation
            nav = page.query_selector("nav")
            header = page.query_selector("header")
            data.has_nav = nav is not None or header is not None

            logo_link = page.query_selector("a[href='/'] img") or page.query_selector("a[href='/']")
            data.logo_links_home = logo_link is not None

            # Security signals
            data.has_payment_badges = any(
                k in page_text for k in ["visa", "mastercard", "paypal", "stripe", "ssl", "secure payment"]
            )
            data.has_privacy_link = (
                page.query_selector("a[href*='privacy']") is not None
                or page.query_selector("a[href*='policy']") is not None
            )

            # CLS on desktop
            cls = page.evaluate("""
                () => new Promise(resolve => {
                    let clsValue = 0;
                    new PerformanceObserver(list => {
                        for (const entry of list.getEntries()) {
                            if (!entry.hadRecentInput) clsValue += entry.value;
                        }
                        resolve(clsValue);
                    }).observe({type: 'layout-shift', buffered: true});
                    setTimeout(() => resolve(clsValue), 3000);
                })
            """)
            data.cls_score = round(cls, 4) if cls is not None else None

            # Screenshot (desktop)
            if screenshot_dir:
                domain = parsed.netloc.replace(".", "_")
                ss_path = Path(screenshot_dir) / f"{domain}_{page_type}_desktop.png"
                ss_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(ss_path), full_page=False)
                data.desktop_screenshot = str(ss_path)

            desktop_ctx.close()

            # --- Mobile pass ---
            mobile_ctx = browser.new_context(viewport={"width": 375, "height": 812})
            mpage = mobile_ctx.new_page()
            mpage.goto(url, wait_until="networkidle", timeout=timeout)
            _dismiss_cookie_banners(mpage)

            # LCP on mobile
            lcp = mpage.evaluate("""
                () => new Promise(resolve => {
                    new PerformanceObserver(list => {
                        const entries = list.getEntries();
                        resolve(entries.length > 0 ? entries[entries.length - 1].startTime : null);
                    }).observe({type: 'largest-contentful-paint', buffered: true});
                    setTimeout(() => resolve(null), 3000);
                })
            """)
            if lcp is not None:
                data.lcp_ms = round(lcp)

            # Mobile CTA
            for selector in _CTA_SELECTORS:
                try:
                    cta = mpage.query_selector(selector)
                    if cta:
                        box = cta.bounding_box()
                        if box and box["y"] < 812:
                            data.cta_above_fold_mobile = True
                            break
                except Exception:
                    continue

            # Mobile viewport meta
            data.has_viewport_meta = mpage.query_selector('meta[name="viewport"]') is not None

            # Horizontal scroll
            scroll_width = mpage.evaluate("document.documentElement.scrollWidth")
            viewport_width = mpage.evaluate("window.innerWidth")
            data.has_horizontal_scroll = scroll_width > viewport_width

            # Font size
            base_font = mpage.evaluate("() => parseFloat(window.getComputedStyle(document.body).fontSize)")
            data.base_font_size = base_font if base_font else 16.0

            # TTFB
            ttfb = mpage.evaluate("""
                () => {
                    const nav = performance.getEntriesByType('navigation')[0];
                    return nav ? nav.responseStart : null;
                }
            """)
            if ttfb is not None:
                data.ttfb_ms = round(ttfb)

            # Screenshot (mobile)
            if screenshot_dir:
                domain = parsed.netloc.replace(".", "_")
                ss_path = Path(screenshot_dir) / f"{domain}_{page_type}_mobile.png"
                mpage.screenshot(path=str(ss_path), full_page=False)
                data.mobile_screenshot = str(ss_path)

            mobile_ctx.close()
            browser.close()

    except ImportError:
        raise
    except Exception as e:
        err_type = type(e).__name__
        data.error = f"{err_type}: {e}"

    return data


# ---------------------------------------------------------------------------
# SA01-SA15 check builders
# ---------------------------------------------------------------------------


def _trust_signal_count(data: PageAuditData) -> int:
    """Count the number of distinct trust signal types present."""
    return sum(
        [
            data.has_testimonials,
            data.has_trust_badges,
            data.has_reviews,
            data.has_guarantees,
        ]
    )


def build_site_checks(pages: list[PageAuditData]) -> list[CheckResult]:
    """Build SA01-SA15 CheckResults from one or more PageAuditData.

    For multi-page crawls, uses worst-case for performance and best-case
    for content quality (at least one page should pass).
    """
    if not pages:
        return []

    checks: list[CheckResult] = []

    # Filter out pages with errors for most checks
    valid = [p for p in pages if not p.error]
    if not valid:
        # All pages errored — emit a single fail with the error
        checks.append(
            CheckResult(
                check_id="SA01",
                category="site",
                severity="critical",
                result="fail",
                message=f"Could not analyze any page: {pages[0].error}",
                recommended_action="Check that the URL is accessible and not blocked.",
            )
        )
        return checks

    # SA01 — CTA above fold (desktop)
    any_cta_desktop = any(p.cta_above_fold_desktop for p in valid)
    checks.append(
        CheckResult(
            check_id="SA01",
            category="site",
            severity="critical",
            result="pass" if any_cta_desktop else "fail",
            message="CTA visible above fold on desktop" if any_cta_desktop else "No CTA found above fold on desktop",
            current_value=any_cta_desktop,
            threshold=True,
            recommended_action=(
                "" if any_cta_desktop else "Add a prominent CTA (Buy Now, Add to Cart) in the first viewport."
            ),
        )
    )

    # SA02 — CTA contrast & size
    best_area = max(p.cta_best_area for p in valid)
    if best_area >= 3000:
        sa02_result = "pass"
        sa02_msg = f"Best CTA area: {best_area:,.0f}px²"
    elif best_area >= 1500:
        sa02_result = "warning"
        sa02_msg = f"CTA area may be small: {best_area:,.0f}px²"
    else:
        sa02_result = "fail"
        sa02_msg = f"CTA too small or not found: {best_area:,.0f}px²"
    checks.append(
        CheckResult(
            check_id="SA02",
            category="site",
            severity="high",
            result=sa02_result,
            message=sa02_msg,
            current_value=best_area,
            threshold=3000,
            recommended_action=""
            if sa02_result == "pass"
            else "Increase CTA button size and use high-contrast colors.",
        )
    )

    # SA03 — Mobile CTA visibility
    any_cta_mobile = any(p.cta_above_fold_mobile for p in valid)
    checks.append(
        CheckResult(
            check_id="SA03",
            category="site",
            severity="critical",
            result="pass" if any_cta_mobile else "fail",
            message="CTA visible on mobile viewport" if any_cta_mobile else "No CTA found on mobile viewport",
            current_value=any_cta_mobile,
            threshold=True,
            recommended_action="" if any_cta_mobile else "Ensure CTA is visible without scrolling on mobile devices.",
        )
    )

    # SA04 — Form friction
    form_pages = [p for p in valid if p.form_present]
    if form_pages:
        worst_fields = max(p.form_field_count for p in form_pages)
        if worst_fields <= 5:
            sa04_result = "pass"
            sa04_msg = f"Form fields: {worst_fields} (low friction)"
        elif worst_fields <= 8:
            sa04_result = "warning"
            sa04_msg = f"Form fields: {worst_fields} (moderate friction)"
        else:
            sa04_result = "fail"
            sa04_msg = f"Form fields: {worst_fields} (high friction)"
        checks.append(
            CheckResult(
                check_id="SA04",
                category="site",
                severity="high",
                result=sa04_result,
                message=sa04_msg,
                current_value=worst_fields,
                threshold=5,
                recommended_action=(
                    "" if sa04_result == "pass" else "Reduce form fields to 5 or fewer; use progressive disclosure."
                ),
            )
        )

    # SA05 — Mobile responsiveness
    all_viewport = all(p.has_viewport_meta for p in valid)
    any_hscroll = any(p.has_horizontal_scroll for p in valid)
    sa05_pass = all_viewport and not any_hscroll
    checks.append(
        CheckResult(
            check_id="SA05",
            category="site",
            severity="critical",
            result="pass" if sa05_pass else "fail",
            message=(
                "Mobile responsive: viewport meta present, no horizontal scroll"
                if sa05_pass
                else (
                    f"Mobile issues: viewport_meta="
                    f"{'yes' if all_viewport else 'MISSING'}, "
                    f"h_scroll={'yes' if any_hscroll else 'no'}"
                )
            ),
            current_value=sa05_pass,
            threshold=True,
            recommended_action="" if sa05_pass else "Add <meta name='viewport'> and fix horizontal overflow.",
        )
    )

    # SA06 — Page speed (LCP)
    lcp_values = [p.lcp_ms for p in valid if p.lcp_ms is not None]
    if lcp_values:
        worst_lcp = max(lcp_values)
        if worst_lcp < 2500:
            sa06_result = "pass"
            sa06_msg = f"LCP: {worst_lcp:,.0f}ms (good)"
        elif worst_lcp < 4000:
            sa06_result = "warning"
            sa06_msg = f"LCP: {worst_lcp:,.0f}ms (needs improvement)"
        else:
            sa06_result = "fail"
            sa06_msg = f"LCP: {worst_lcp:,.0f}ms (poor)"
        checks.append(
            CheckResult(
                check_id="SA06",
                category="site",
                severity="high",
                result=sa06_result,
                message=sa06_msg,
                current_value=worst_lcp,
                threshold=2500,
                recommended_action=""
                if sa06_result == "pass"
                else "Optimize images, reduce JS, use CDN to improve LCP.",
            )
        )

    # SA07 — Layout shift (CLS)
    cls_values = [p.cls_score for p in valid if p.cls_score is not None]
    if cls_values:
        worst_cls = max(cls_values)
        if worst_cls < 0.1:
            sa07_result = "pass"
            sa07_msg = f"CLS: {worst_cls:.4f} (good)"
        elif worst_cls < 0.25:
            sa07_result = "warning"
            sa07_msg = f"CLS: {worst_cls:.4f} (needs improvement)"
        else:
            sa07_result = "fail"
            sa07_msg = f"CLS: {worst_cls:.4f} (poor)"
        checks.append(
            CheckResult(
                check_id="SA07",
                category="site",
                severity="medium",
                result=sa07_result,
                message=sa07_msg,
                current_value=worst_cls,
                threshold=0.1,
                recommended_action=(
                    "" if sa07_result == "pass" else "Set explicit dimensions on images/ads to prevent layout shifts."
                ),
            )
        )

    # SA08 — Trust signals
    best_trust = max(_trust_signal_count(p) for p in valid)
    if best_trust >= 2:
        sa08_result = "pass"
        sa08_msg = f"Trust signal types: {best_trust} (reviews, testimonials, badges, guarantees)"
    elif best_trust == 1:
        sa08_result = "warning"
        sa08_msg = "Only 1 trust signal type found"
    else:
        sa08_result = "fail"
        sa08_msg = "No trust signals found (reviews, testimonials, badges, guarantees)"
    checks.append(
        CheckResult(
            check_id="SA08",
            category="site",
            severity="high",
            result=sa08_result,
            message=sa08_msg,
            current_value=best_trust,
            threshold=2,
            recommended_action=(
                "" if sa08_result == "pass" else "Add customer reviews, trust badges, or satisfaction guarantees."
            ),
        )
    )

    # SA09 — Schema markup
    all_schema = set()
    for p in valid:
        all_schema.update(p.schema_types)
    relevant_schema = all_schema & {"Product", "FAQPage", "Service", "Organization", "LocalBusiness", "BreadcrumbList"}
    checks.append(
        CheckResult(
            check_id="SA09",
            category="site",
            severity="medium",
            result="pass" if relevant_schema else "fail",
            message=f"Schema types found: {', '.join(sorted(all_schema))}" if all_schema else "No schema markup found",
            current_value=", ".join(sorted(relevant_schema)) if relevant_schema else "",
            threshold="Product/FAQ/Service",
            recommended_action="" if relevant_schema else "Add structured data (Product, FAQ, or Organization schema).",
        )
    )

    # SA10 — Contact/support access
    has_contact = any(p.has_phone or p.has_chat or p.has_contact_form for p in valid)
    checks.append(
        CheckResult(
            check_id="SA10",
            category="site",
            severity="medium",
            result="pass" if has_contact else "fail",
            message="Contact/support channel available" if has_contact else "No contact channel found",
            current_value=has_contact,
            threshold=True,
            recommended_action="" if has_contact else "Add a visible phone number, chat widget, or contact form.",
        )
    )

    # SA11 — H1 heading present
    any_h1 = any(p.h1 for p in valid)
    checks.append(
        CheckResult(
            check_id="SA11",
            category="site",
            severity="high",
            result="pass" if any_h1 else "fail",
            message=f"H1: {valid[0].h1[:80]}" if any_h1 else "No H1 heading found",
            current_value=any_h1,
            threshold=True,
            recommended_action="" if any_h1 else "Add a clear H1 heading that describes the page content.",
        )
    )

    # SA12 — Image count
    best_img = max(p.image_count for p in valid) if valid else 0
    if 2 <= best_img <= 20:
        sa12_result = "pass"
        sa12_msg = f"Image count: {best_img}"
    elif best_img == 1 or 21 <= best_img <= 30:
        sa12_result = "warning"
        sa12_msg = f"Image count: {best_img} ({'too few' if best_img < 2 else 'many'})"
    else:
        sa12_result = "fail"
        sa12_msg = f"Image count: {best_img} ({'none' if best_img == 0 else 'excessive'})"
    checks.append(
        CheckResult(
            check_id="SA12",
            category="site",
            severity="medium",
            result=sa12_result,
            message=sa12_msg,
            current_value=best_img,
            threshold="2-20",
            recommended_action="" if sa12_result == "pass" else "Aim for 2-20 images per page for optimal engagement.",
        )
    )

    # SA13 — Security indicators
    all_https = all(p.is_https for p in valid)
    any_payment = any(p.has_payment_badges or p.has_privacy_link for p in valid)
    if all_https and any_payment:
        sa13_result = "pass"
        sa13_msg = "HTTPS + payment/privacy signals present"
    elif all_https:
        sa13_result = "warning"
        sa13_msg = "HTTPS present but no payment badges or privacy link"
    else:
        sa13_result = "fail"
        sa13_msg = "Site not served over HTTPS"
    checks.append(
        CheckResult(
            check_id="SA13",
            category="site",
            severity="medium",
            result=sa13_result,
            message=sa13_msg,
            current_value=all_https,
            threshold=True,
            recommended_action=(
                "" if sa13_result == "pass" else "Ensure HTTPS and add payment badges / privacy policy link."
            ),
        )
    )

    # SA14 — Navigation consistency
    all_nav = all(p.has_nav for p in valid)
    all_logo = all(p.logo_links_home for p in valid)
    if all_nav and all_logo:
        sa14_result = "pass"
        sa14_msg = "Navigation present with logo linking home"
    elif all_nav:
        sa14_result = "warning"
        sa14_msg = "Navigation present but logo does not link home"
    else:
        sa14_result = "fail"
        sa14_msg = "Navigation missing on some pages"
    checks.append(
        CheckResult(
            check_id="SA14",
            category="site",
            severity="medium",
            result=sa14_result,
            message=sa14_msg,
            current_value=all_nav,
            threshold=True,
            recommended_action=""
            if sa14_result == "pass"
            else "Add consistent navigation with logo linking to homepage.",
        )
    )

    # SA15 — Font readability (mobile)
    font_sizes = [p.base_font_size for p in valid if p.base_font_size > 0]
    if font_sizes:
        min_font = min(font_sizes)
        if min_font >= 16:
            sa15_result = "pass"
            sa15_msg = f"Base font size: {min_font:.0f}px"
        elif min_font >= 14:
            sa15_result = "warning"
            sa15_msg = f"Base font size: {min_font:.0f}px (slightly small)"
        else:
            sa15_result = "fail"
            sa15_msg = f"Base font size: {min_font:.0f}px (too small for mobile)"
        checks.append(
            CheckResult(
                check_id="SA15",
                category="site",
                severity="low",
                result=sa15_result,
                message=sa15_msg,
                current_value=min_font,
                threshold=16,
                recommended_action=(
                    "" if sa15_result == "pass" else "Increase base font size to at least 16px for mobile readability."
                ),
            )
        )

    return checks


def build_site_checks_single(data: PageAuditData) -> list[CheckResult]:
    """Convenience wrapper: build site checks from a single PageAuditData."""
    return build_site_checks([data])
