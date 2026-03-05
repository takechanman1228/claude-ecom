# claude-ecom

Claude-powered ecommerce audit toolkit — run `/ecom audit` to get a full-store health score with prioritized fixes.

## What It Does

Drop in your orders CSV and get back:

1. **AUDIT-REPORT.md** — 99-check health audit across 7 categories with action plan and quick wins
2. **executive-summary.md** — one-page stakeholder summary
3. **scores.json** — machine-readable scores for dashboards/CI

## Quick Start

```bash
pip install -e .

# Full audit
ecom audit orders.csv --products products.csv --inventory inventory.csv

# With site quality audit (requires Playwright)
pip install -e ".[site]" && playwright install chromium
ecom audit orders.csv --site-url https://your-store.com

# Business reviews
ecom review mbr orders.csv              # Monthly Business Review
ecom review qbr orders.csv              # Quarterly Business Review
ecom review abr orders.csv              # Annual Business Review
```

## Commands

| Command | What it does |
|---------|-------------|
| `ecom audit` | Full 7-category health audit → AUDIT-REPORT.md + executive-summary.md + scores.json |
| `ecom review mbr\|qbr\|abr` | Periodic business review → MBR.md / QBR.md / ABR.md |
| `ecom shopify setup` | Configure Shopify Admin API credentials |
| `ecom shopify sync` | Sync data from Shopify via Bulk Operations |

## Audit Categories (99 checks)

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

## Shopify Integration

```bash
# Install API dependencies
pip install -e ".[all]"

# Interactive setup (creates .claude-ecom/config.toml)
ecom shopify setup

# Sync and audit
ecom shopify sync --since 2024-01-01
ecom audit --source shopify --since 2024-01-01
```

**Required Shopify Admin API scopes:** `read_orders`, `read_products`, `read_inventory`, `read_customers`, `read_all_orders`

## Claude Code Skill

This project includes a Claude Code skill. Install it to use `/ecom audit` and `/ecom review` directly in Claude Code.

```bash
bash install.sh              # Skill only
bash install.sh --with-cli   # Skill + Python CLI
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
bash validate-skills.sh
```

See [CHANGELOG.md](CHANGELOG.md) for version history.

## License

MIT
