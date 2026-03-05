---
name: ecom-site-audit
description: >
  Site / landing page quality audit using Playwright. Analyzes CTA visibility,
  form friction, trust signals, Core Web Vitals (LCP, CLS), mobile responsiveness,
  schema markup, and navigation quality. Produces SA01-SA15 checks.
  Triggers on: "site audit", "LP analysis", "landing page audit", "CTA check",
  "page speed", "mobile audit", "site quality".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# ecom-site-audit — Site / Landing Page Quality Audit

Analyzes ecommerce site quality using headless Chromium (Playwright).

## Commands

| Command | What it does |
|---------|-------------|
| `ecom-analytics site-audit <url>` | Single-page quality audit |
| `ecom-analytics site-audit <url> --crawl` | Multi-page crawl audit |
| `ecom-analytics site-audit <url> --crawl --max-pages 5` | Crawl up to 5 pages |
| `ecom-analytics site-audit <url> --json` | JSON output |
| `ecom-analytics site-audit <url> --no-screenshots` | Skip screenshots |
| `ecom-analytics audit orders.csv --site-url <url>` | Combined audit (7 categories) |

## Prerequisites

```bash
pip install ecom-analytics[site]
playwright install chromium
```

## Process

1. Open URL in headless Chromium (desktop 1920x1080 + mobile 375x812)
2. Dismiss cookie banners, detect bot blocks
3. Desktop pass: content, CTA, forms, trust signals, schema, navigation, security
4. Mobile pass: LCP, CLS, viewport meta, horizontal scroll, font size, CTA
5. Build SA01-SA15 check results
6. Score and generate SITE-AUDIT.md report

## SA01-SA15 Checks

| ID | Check | Severity | Pass | Warning | Fail |
|----|-------|----------|------|---------|------|
| SA01 | CTA above fold (desktop) | Critical | CTA in first viewport | — | No CTA above fold |
| SA02 | CTA contrast & size | High | Area >= 3000px² | Area >= 1500px² | Small/missing CTA |
| SA03 | Mobile CTA visibility | Critical | CTA in mobile viewport | — | No CTA on mobile |
| SA04 | Form friction | High | <= 5 fields | 6-8 fields | > 8 fields |
| SA05 | Mobile responsiveness | Critical | viewport meta + no h-scroll | — | Missing viewport or h-scroll |
| SA06 | Page speed (LCP) | High | < 2500ms | 2500-4000ms | > 4000ms |
| SA07 | Layout shift (CLS) | Medium | < 0.1 | 0.1-0.25 | > 0.25 |
| SA08 | Trust signals | High | >= 2 types | 1 type | None |
| SA09 | Schema markup | Medium | Product/FAQ/Service | — | None |
| SA10 | Contact/support access | Medium | Phone/chat/form | — | None |
| SA11 | H1 heading present | High | H1 exists | — | No H1 |
| SA12 | Image count | Medium | 2-20 images | 1 or 21-30 | 0 or > 30 |
| SA13 | Security indicators | Medium | HTTPS + payment/privacy | HTTPS only | Not HTTPS |
| SA14 | Navigation consistency | Medium | Nav + logo links home | Nav present | No nav |
| SA15 | Font readability (mobile) | Low | >= 16px | 14-15px | < 14px |

## Page Types (for --crawl)

Priority order: top > collection > pdp > cart > about > shipping > contact > faq

## Notes

- Playwright is an optional dependency — base package works without it
- All unit tests are mock-based and don't require a browser
- Bot blocks (Cloudflare, captcha) are detected and reported as errors
- Cookie banners are auto-dismissed before measurement
- Combined with `audit` command via `--site-url`, site becomes the 7th scoring category

## Python Backend

```bash
cd ecom-analytics
ecom-analytics site-audit https://example.com
ecom-analytics site-audit https://example.com --crawl --max-pages 10
```
