"""Priority BFS crawler for ecommerce sites.

Discovers and classifies pages by type (homepage, collection, PDP, cart, etc.),
then analyzes each using site_audit.analyze_page().
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import urljoin, urlparse

from .site_audit import PageAuditData, analyze_page, check_playwright_available


@dataclass
class CrawlConfig:
    """Configuration for site crawling."""

    max_pages: int = 20
    timeout_per_page: int = 30000
    respect_robots: bool = True
    screenshot_dir: str | None = None


@dataclass
class CrawlResult:
    """Result of a site crawl."""

    base_url: str
    pages: list[PageAuditData] = field(default_factory=list)
    skipped_urls: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# Page type detection patterns (order matters — first match wins)
_PAGE_TYPE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("cart", re.compile(r"/cart|/basket|/bag", re.I)),
    ("checkout", re.compile(r"/checkout|/pay", re.I)),
    ("pdp", re.compile(r"/products?/[^/]+|/item/|/p/[^/]+|/dp/", re.I)),
    ("collection", re.compile(r"/collections?/|/categor|/shop/[^/]+|/c/[^/]+", re.I)),
    ("about", re.compile(r"/about|/our-story|/team", re.I)),
    ("contact", re.compile(r"/contact|/support|/help", re.I)),
    ("faq", re.compile(r"/faq|/frequently-asked", re.I)),
    ("shipping", re.compile(r"/shipping|/delivery|/returns", re.I)),
    ("privacy", re.compile(r"/privacy|/terms|/legal|/policy", re.I)),
    ("blog", re.compile(r"/blog|/news|/article", re.I)),
    ("account", re.compile(r"/account|/login|/register|/my-", re.I)),
]

# Priority order for crawling — lower index = higher priority
_PAGE_PRIORITY = {
    "top": 0,
    "lp": 1,
    "collection": 2,
    "pdp": 3,
    "cart": 4,
    "about": 5,
    "shipping": 6,
    "contact": 7,
    "faq": 8,
    "other": 9,
    "blog": 10,
    "privacy": 11,
    "account": 12,
    "checkout": 13,
}


def detect_page_type(url: str) -> str:
    """Classify a URL into a page type based on path patterns."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")

    if not path or path == "/":
        return "top"

    for ptype, pattern in _PAGE_TYPE_PATTERNS:
        if pattern.search(path):
            return ptype

    return "other"


def _normalize_url(url: str) -> str:
    """Normalize a URL for deduplication (strip fragment, trailing slash)."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def discover_links(page, base_domain: str) -> list[str]:
    """Extract internal links from a Playwright page object."""
    try:
        hrefs = page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]'))
                .map(a => a.href)
                .filter(h => h.startsWith('http'))
        """)
    except Exception:
        return []

    internal = []
    for href in hrefs:
        parsed = urlparse(href)
        if parsed.netloc == base_domain or parsed.netloc.endswith(f".{base_domain}"):
            normalized = _normalize_url(href)
            internal.append(normalized)

    return list(set(internal))


def check_robots_txt(base_url: str, path: str) -> bool:
    """Check if a path is allowed by robots.txt. Returns True if allowed."""
    try:
        import urllib.request
        from urllib.robotparser import RobotFileParser

        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch("*", f"{parsed.scheme}://{parsed.netloc}{path}")
    except Exception:
        return True  # Allow if robots.txt can't be read


def crawl_site(
    start_url: str,
    config: CrawlConfig | None = None,
    progress_cb: Callable[[str, int, int], None] | None = None,
) -> CrawlResult:
    """Crawl an ecommerce site starting from start_url.

    Uses priority BFS: analyzes start_url first, then discovers internal links,
    classifies them by page type, and visits them in priority order until
    max_pages is reached.

    Args:
        start_url: The URL to start crawling from.
        config: Crawl configuration. Defaults to CrawlConfig().
        progress_cb: Optional callback(url, current_count, max_pages).
    """
    check_playwright_available()
    from playwright.sync_api import sync_playwright

    if config is None:
        config = CrawlConfig()

    result = CrawlResult(base_url=start_url)
    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc

    visited: set[str] = set()
    # Queue: list of (priority, url, page_type)
    queue: list[tuple[int, str, str]] = []

    # Add start URL
    start_normalized = _normalize_url(start_url)
    start_type = detect_page_type(start_url)
    queue.append((_PAGE_PRIORITY.get(start_type, 9), start_normalized, start_type))

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            while queue and len(result.pages) < config.max_pages:
                # Sort by priority and pick the highest priority URL
                queue.sort(key=lambda x: x[0])
                _, url, page_type = queue.pop(0)

                normalized = _normalize_url(url)
                if normalized in visited:
                    continue
                visited.add(normalized)

                # Robots.txt check
                if config.respect_robots:
                    url_path = urlparse(url).path
                    if not check_robots_txt(start_url, url_path):
                        result.skipped_urls.append(f"{url} (robots.txt)")
                        continue

                if progress_cb:
                    progress_cb(url, len(result.pages) + 1, config.max_pages)

                # Analyze page
                try:
                    page_data = analyze_page(
                        url,
                        page_type=page_type,
                        timeout=config.timeout_per_page,
                        screenshot_dir=config.screenshot_dir,
                    )
                    result.pages.append(page_data)
                except Exception as e:
                    result.errors.append(f"{url}: {e}")
                    continue

                # Discover new links from this page (use a lightweight page load)
                try:
                    ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
                    page = ctx.new_page()
                    page.goto(url, wait_until="domcontentloaded", timeout=config.timeout_per_page)
                    links = discover_links(page, base_domain)
                    ctx.close()

                    for link in links:
                        link_norm = _normalize_url(link)
                        if link_norm not in visited:
                            link_type = detect_page_type(link)
                            # Skip account/checkout pages
                            if link_type in ("account", "checkout"):
                                continue
                            priority = _PAGE_PRIORITY.get(link_type, 9)
                            queue.append((priority, link_norm, link_type))
                except Exception:
                    pass  # Link discovery failure is non-fatal

            browser.close()

    except Exception as e:
        result.errors.append(f"Crawl error: {e}")

    return result
