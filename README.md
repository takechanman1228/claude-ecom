# ecom-analytics

EC-specialized data analytics toolkit — audit, diagnose, and improve your ecommerce store.

## Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | Revenue Decomposition | Break down Revenue = Traffic × CVR × AOV over time |
| 2 | CVR Analysis | Funnel drop-off, device/channel-level conversion |
| 3 | Product Analysis | ABC analysis, cross-sell discovery, lifecycle diagnosis |
| 4 | Inventory Analysis | Stockout opportunity cost, overstock identification |
| 5 | Cohort / LTV | Monthly cohort retention, LTV estimation, churn signals |
| 6 | Pricing Analysis | Price elasticity, discount dependency, margin impact |
| 7 | Site / LP Audit | CTA visibility, Core Web Vitals, trust signals, mobile UX (Playwright) |
| 8 | A/B Test Design | Power calculation, test duration, initiative prioritization |
| 9 | Quick Wins | Top improvements executable in < 15 minutes |
| 10 | Full Audit | Run all analyses in parallel, produce unified health score |
| 11 | EC Context | Business model detection, industry benchmarks |

## Current Status (v0.3.0)

All **99 checks** are defined across 12 SKILL.md files. The Python backend implements **56 checks** across all 7 categories (Revenue 10, Conversion 6, Product 6, Inventory 6, Retention 7, Pricing 6, Site 15); remaining checks use SKILL.md-guided analysis by Claude Code.

### v0.3.0 Changes — Site / Landing Page Audit

**New 7th category: Site Quality (SA01-SA15)**

Uses **Playwright** headless browser to analyze page quality signals:

| Check | What it measures |
|-------|-----------------|
| SA01-SA03 | CTA visibility (desktop + mobile + size) |
| SA04 | Form friction (field count) |
| SA05 | Mobile responsiveness (viewport meta, horizontal scroll) |
| SA06-SA07 | Core Web Vitals (LCP, CLS) |
| SA08 | Trust signals (reviews, testimonials, badges, guarantees) |
| SA09 | Schema markup (Product, FAQ, Service) |
| SA10 | Contact/support access |
| SA11-SA12 | Content quality (H1 heading, image count) |
| SA13-SA14 | Security & navigation |
| SA15 | Font readability on mobile |

```bash
# Single-page audit
ecom-analytics site-audit https://example.com

# Multi-page crawl (priority BFS: homepage → collections → PDP → cart → ...)
ecom-analytics site-audit https://example.com --crawl --max-pages 10

# Combined with order data audit (7 categories)
ecom-analytics audit orders.csv --site-url https://example.com
```

**Playwright is an optional dependency** — install with:
```bash
pip install ecom-analytics[site]
playwright install chromium
```

The base package works without Playwright. The 7th "site" category is auto-excluded from scoring when not present (weights renormalize).

**Other additions:**
- Priority BFS crawler with page type detection (top, collection, PDP, cart, about, etc.)
- Bot block detection (Cloudflare challenge, captcha, 403)
- Cookie banner auto-dismissal before measurements
- Desktop (1920×1080) + mobile (375×812) screenshots per page
- SITE-AUDIT.md report with per-page performance table
- New skill: `ecom-site-audit`
- 60+ new mock-based tests (no browser required)

### v0.2.0 Changes

**Check coverage: 19 → 41 checks (49% of 84)**

| Category | Before | After |
|----------|--------|-------|
| Revenue (R01-R15) | 5 | 10 |
| Conversion (CV01-CV12) | 4 | 6 |
| Product (P01-P20) | 2 | 6 |
| Inventory (O01-O10) | 1 | 6 |
| Retention (C01-C15) | 3 | 7 |
| Pricing (PR01-PR12) | 2 | 6 |

**Report quality improvements:**
- **Benchmark comparison** — industry median and top quartile table in audit reports
- **Finding clusters** — cross-category theme grouping (5 clusters) with root cause hypotheses
- **ASCII bar chart** — category score visualization in executive summary
- **Business model detection** — auto-detects D2C / Marketplace / Subscription / O2O
- **Check-specific revenue impact** — per-check formulas (CV01, CV05, CV06, R10, R08, PR01, R14) with severity-based fallback
- **Top Issue bug fix** — now surfaces highest-severity non-pass finding (was showing "None")
- **Quick Wins actions** — `recommended_action` field rendered when populated

**Infrastructure:**
- **Version unified** — `pyproject.toml`, `SKILL.md`, and report footers via `importlib.metadata`
- **6 audit agents** — parallel sub-agent delegation for full audit (revenue, product, retention, operations, pricing, growth)
- **PowerShell installers** — `install.ps1` and `uninstall.ps1` for Windows
- **`install.sh` hardened** — clone failure shows actionable error + agents copy step
- **`validate-skills.sh`** — dynamic reference file listing
- **New reference files:**
  - `references/recommended-actions.md` — per-check improvement playbooks
  - `references/impact-formulas.md` — revenue impact calculation formulas
  - `references/finding-clusters.md` — 8 cross-category theme clusters

## Quick Start

```bash
pip install -e .

# Full audit
ecom-analytics audit orders.csv --products products.csv --inventory inventory.csv

# Individual analyses
ecom-analytics revenue orders.csv
ecom-analytics cohort orders.csv --horizon 12
ecom-analytics product orders.csv --products products.csv

# Business reviews (MBR / QBR / ABR)
ecom-analytics review mbr orders.csv              # Monthly Business Review
ecom-analytics review qbr orders.csv              # Quarterly Business Review
ecom-analytics review abr orders.csv              # Annual Business Review

# Site audit (requires Playwright)
pip install -e ".[site]" && playwright install chromium
ecom-analytics site-audit https://your-store.com
ecom-analytics site-audit https://your-store.com --crawl --max-pages 10
```

### Auditing Shopify Analytics Exports

```bash
# Export your Shopify orders CSV, then:
ecom-analytics audit shopify_orders.csv --products shopify_products.csv
```

The loader auto-detects Shopify CSV format and maps columns accordingly.

### Shopify Admin API (v0.2.0+)

Connect directly to a Shopify store via the Admin API — no manual CSV exports needed.

#### Setup

```bash
pip install -e ".[all]"   # installs httpx, pyarrow

# Interactive setup (creates .ecom-analytics/config.toml)
ecom-analytics shopify setup
```

Or create `.ecom-analytics/config.toml` manually:

```toml
[shopify]
store_domain = "your-store.myshopify.com"
access_token = "shpat_..."
api_version = "2025-01"
timezone = "America/Los_Angeles"
currency = "USD"
allow_pii = false
```

**Required Shopify Admin API scopes:**

| Scope | Purpose |
|-------|---------|
| `read_orders` | Fetch orders and line items |
| `read_products` | Fetch product catalog and variants |
| `read_inventory` | Fetch inventory levels by location |
| `read_customers` | Access customer data in bulk operations (required for customer ID/email on orders) |
| `read_all_orders` | Access orders older than 60 days |

To create a Custom App: **Shopify Admin → Settings → Apps and sales channels → Develop apps → Create an app → Configuration → Admin API access scopes** — enable all 5 scopes above, then install the app and copy the access token.

#### Credential Management

- **Config file:** `.ecom-analytics/config.toml` (auto-added to `.gitignore`)
- **Env var override:** Set `SHOPIFY_ACCESS_TOKEN` to override the file token (recommended for CI/CD)
- **Search order:** `./ecom-analytics/config.toml` → `~/.ecom-analytics/config.toml`

#### Sync Data

```bash
ecom-analytics shopify sync --since 2024-01-01
ecom-analytics shopify sync --since 2024-01-01 --mode incremental
```

Output: `.ecom-analytics/data/{orders,order_items,products,inventory}.parquet` + `sync_state.json`

#### Audit from API

```bash
ecom-analytics audit --source shopify --since 2024-01-01 -o output/
```

This syncs data first (if needed), then runs the full audit pipeline.

#### Security

- PII (email addresses) is SHA-256 hashed by default (`allow_pii = false`)
- Never commit access tokens — use env vars in CI/CD
- `.ecom-analytics/` is auto-added to `.gitignore` by `shopify setup`

See `doc/shopify-api-setup-guide.md` for the full step-by-step procedure.

## Scoring

Seven categories (weights renormalize to present categories only):

| Category | Weight | Checks |
|----------|--------|--------|
| Revenue Structure | 25% | R01–R15 |
| Conversion | 20% | CV01–CV12 |
| Product | 20% | P01–P20 |
| Inventory | 10% | O01–O10 |
| Retention / LTV | 15% | C01–C15 |
| Pricing | 10% | PR01–PR12 |
| Site Quality | 10% | SA01–SA15 |

Grades: **A** (90–100) · **B** (75–89) · **C** (60–74) · **D** (40–59) · **F** (< 40)

## Claude Code Skills

This project includes 13 slash commands usable as Claude Code skills.
Type any command in Claude Code to run it.

| Command | Description |
|---------|-------------|
| `/ecom-analytics` | Main orchestrator — full store audit across all categories |
| `/ecom-audit` | Full audit with parallel sub-agent delegation (revenue, product, retention, ops, pricing, growth) |
| `/ecom-revenue` | Revenue decomposition (Revenue = Traffic x CVR x AOV), trend analysis, 15 checks (R01-R15) |
| `/ecom-conversion` | Conversion funnel analysis — CVR, cart/checkout abandonment, 12 checks (CV01-CV12) |
| `/ecom-product` | Product performance — ABC classification, cross-sell, lifecycle, 20 checks (P01-P20) |
| `/ecom-inventory` | Inventory health — stockout/overstock, turnover, deadstock, 10 checks (O01-O10) |
| `/ecom-cohort` | Cohort retention, LTV estimation, RFM segmentation, 15 checks (C01-C15) |
| `/ecom-pricing` | Price & discount analysis — elasticity, margin, discount dependency, 12 checks (PR01-PR12) |
| `/ecom-site-audit` | Site/LP quality audit via Playwright — CTA, Core Web Vitals, trust signals (SA01-SA15) |
| `/ecom-experiment` | A/B test design — power calculation, sample size, MDE, ICE/RICE prioritization |
| `/ecom-quickwins` | Extract top high-severity, low-effort improvements (< 15 min each) |
| `/ecom-context` | Business model detection (D2C/marketplace/subscription/O2O) + industry benchmarks |
| `/ecom-shopify-import` | Shopify Admin API bulk import (orders, products, inventory) |

See `skills/ecom-analytics/SKILL.md` for the main orchestrator.

**Reference path convention:** All sub-skills resolve references from
`ecom-analytics/references/`. When installed via `install.sh`, this maps to
`~/.claude/skills/ecom-analytics/references/`.

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
bash validate-skills.sh
```

CI runs automatically on push/PR via GitHub Actions (`.github/workflows/ci.yml`).

See [CHANGELOG.md](CHANGELOG.md) for version history.

## License

MIT
