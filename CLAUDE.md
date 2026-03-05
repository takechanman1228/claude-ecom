# CLAUDE.md

## Project: claude-ecom

EC-specialized data analytics toolkit -- audit, diagnose, and improve ecommerce stores.

## Architecture: Hybrid (Python Compute + LLM Interpretation)

```
CSV/Shopify Data
    |
    v
Python CLI (ecom audit)     <-- Deterministic: KPI calc, scoring, check evaluation
    |
    v
scores.json                 <-- Machine-readable structured data
    |
    v
Claude (SKILL.md)           <-- LLM: reads scores.json + reference files, generates
    |                            natural language report with business interpretation
    v
AUDIT-REPORT.md             <-- Human-readable: narrative insights, not just numbers
ACTION-PLAN.md
QUICK-WINS.md
```

**Key principle:** Python computes the numbers. Claude interprets them.
The Jinja2 templates (templates/*.j2) produce a basic structural output from the CLI,
but the primary report should be written by Claude using SKILL.md instructions,
which reads scores.json and reference files to produce natural language insights.

## Structure

```
claude_ecom/          # Python package (pip install -e .)
  cli.py              # Click CLI: ecom audit | review | shopify
  loader.py           # CSV/Parquet data loading
  metrics.py          # KPI computation
  scoring.py          # 99-check scoring system (0-100, A-F grading)
  report.py           # Jinja2 report generation (basic structural output)
  templates/          # .j2 templates (basic structure, not the primary output)
  site_audit.py       # Playwright-based site quality checks (SA01-SA15)
  site_crawler.py     # Priority BFS crawler
  review_engine.py    # MBR/QBR/ABR data builder
  shopify_api.py      # Shopify Admin API client
  sync.py             # Shopify bulk data sync
  config.py           # Config file management
  ...                 # cohort, product, inventory, pricing, decomposition, normalize, periods
skills/ecom/          # Claude Code skill (SKILL.md + references/)
  SKILL.md            # LLM instructions for interpreting scores.json
  references/         # 16 reference files loaded on-demand for interpretation
tests/                # pytest test suite
```

## Commands

```bash
pip install -e ".[dev]"       # Install for development
pytest tests/ -v              # Run tests
ecom audit orders.csv         # Run audit (generates scores.json)
ecom review mbr orders.csv    # Generate MBR
ecom shopify setup            # Configure Shopify
```

## Conventions

- Package name: `claude-ecom` (pip), `claude_ecom` (import)
- CLI entry point: `ecom` (defined in pyproject.toml)
- Config dir: `.claude-ecom/` (user-facing, contains tokens -- never commit)
- All check IDs follow pattern: `{CATEGORY}{NUMBER}` (e.g., R01, CV05, SA15)
- Python handles computation; Claude handles interpretation
- Reference files (references/*.md) are the knowledge base for LLM interpretation
- Reports output to current directory by default (--output flag)
- Never present raw numbers without business context and actionable recommendations
