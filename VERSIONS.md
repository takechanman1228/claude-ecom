# Versions

## v0.3.0 — 2026-03-04

Site / landing page quality audit via Playwright.

- New modules: `site_audit`, `site_crawler`
- `ecom-analytics site-audit <url>` — single-page site quality audit (SA01-SA15)
- `ecom-analytics site-audit <url> --crawl --max-pages N` — multi-page crawl audit
- `ecom-analytics audit orders.csv --site-url <url>` — combined audit with 7 categories
- 15 new site checks: CTA visibility (SA01-SA03), form friction (SA04), mobile responsiveness (SA05), page speed/LCP (SA06), layout shift/CLS (SA07), trust signals (SA08), schema markup (SA09), contact access (SA10), H1 heading (SA11), image count (SA12), security indicators (SA13), navigation consistency (SA14), font readability (SA15)
- 7th scoring category "site" (10% weight, auto-renormalized when absent)
- Priority BFS crawler with page type detection (top, collection, PDP, cart, about, etc.)
- Bot block detection (Cloudflare, captcha, 403)
- Cookie banner auto-dismissal before measurements
- Screenshots: desktop (1920x1080) + mobile (375x812) per page
- SITE-AUDIT.md report with per-page performance table
- Optional dep: `playwright>=1.40` (`pip install ecom-analytics[site]`)
- New skill: `ecom-site-audit`
- Test suite: 2 new test files, 60+ new tests (all mock-based, no browser required)

## v0.2.0 — 2026-03-04

Shopify Admin API integration via Bulk Operations.

- New modules: `config`, `shopify_api`, `normalize`, `sync`
- `ecom-analytics shopify setup` — interactive API credential configuration
- `ecom-analytics shopify sync --since <date>` — bulk data import (orders, products, inventory)
- `ecom-analytics audit --source shopify --since <date>` — end-to-end API-backed audit
- Bridge function `build_orders_compat()` — zero changes to existing analysis modules
- ~30 additional checks enabled: R07, C11, O01-O10, P05-P07, PR01-PR02
- Optional deps: `httpx` (API), `pyarrow` (Parquet), `tomli` (Python <3.11)
- PII protection: customer emails SHA-256 hashed by default
- Token security: `.ecom-analytics/` auto-added to `.gitignore`
- New skill: `ecom-shopify-import`
- Test suite: 5 new test files, 73 new tests

## v0.1.0 — 2026-03-04

Initial release.

- 11 SKILL.md definitions (orchestrator + 10 sub-skills)
- Python package: loader, metrics, decomposition, cohort, product, inventory, pricing, scoring, report
- CLI via Click (`ecom-analytics audit|revenue|cohort|product|inventory|report`)
- 84-check scoring system across 6 categories (R15 + CV12 + P20 + O10 + C15 + PR12)
- Weighted health score with A–F grading
- Jinja2 report templates: AUDIT-REPORT.md, ACTION-PLAN.md, QUICK-WINS.md
- Shopify CSV and generic CSV format support
- 10 shared reference files (benchmarks, checklists, scoring algorithm)
- Test suite with sample fixture data
