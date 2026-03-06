# claude-ecom

Claude-powered ecommerce analytics toolkit — run `/ecom review` to get a full-store health review with prioritized fixes.

## What It Does

Drop in your orders CSV and get back:

1. **review.json** — Structured health data with KPI trees, check results, and action candidates
2. **REVIEW.md** — Human-readable business review written by Claude from the structured data

## Quick Start

```bash
pip install -e .

# Run a review (auto-selects periods based on data coverage)
ecom review orders.csv

# Focus on a specific period
ecom review orders.csv --period 90d
```

## Commands

| Command | What it does |
|---------|-------------|
| `ecom review orders.csv` | Full health review → review.json |
| `ecom review orders.csv --period 30d\|90d\|365d` | Period-focused review |
| `ecom validate orders.csv` | Validate CSV column mapping |

## Health Categories

| Category | Weight | Checks |
|----------|--------|--------|
| Revenue | 40% | R01, R03–R05, R07–R08, R13–R14, PR02–PR03, PR07–PR08 |
| Customer | 30% | C01, C08–C11 |
| Product | 30% | P01, P05–P07, P10, P19 |

Health levels: **pass** · **watch** · **fail**

## Multi-Period Architecture

The review engine analyzes up to 3 trailing windows based on data coverage:

| Period | Min data span | What it covers |
|--------|--------------|----------------|
| 30d | 45 days | Recent performance snapshot |
| 90d | 120 days | Quarterly trends |
| 365d | 400 days | Annual view with monthly trend |

Each period includes a KPI tree, growth drivers (AOV/volume/mix effects), and period-over-period comparison.

## Claude Code Skill

This project includes a Claude Code skill. Install it to use `/ecom review` directly in Claude Code.

```bash
bash install.sh              # Skill only
bash install.sh --with-cli   # Skill + Python CLI
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
