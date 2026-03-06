# CLAUDE.md

## Project: claude-ecom

EC-specialized data analytics toolkit -- review and improve ecommerce stores.

## Architecture: Hybrid (Python Compute + LLM Interpretation)

```
Order CSV Data
    |
    v
Python CLI (ecom review)    <-- Deterministic: KPI calc, scoring, check evaluation
    |
    v
review.json                 <-- Machine-readable structured data
    |
    v
Claude (SKILL.md)           <-- LLM: reads review.json + reference files, generates
    |                            natural language report with business interpretation
    v
REVIEW.md                   <-- Human-readable: narrative insights, not just numbers
```

**Key principle:** Python computes the numbers. Claude interprets them.
The Jinja2 templates (templates/*.j2) are legacy and unused by the new flow.
The primary report is written by Claude using SKILL.md instructions,
which reads review.json and reference files to produce natural language insights.

## Structure

```
claude_ecom/          # Python package (pip install -e .)
  cli.py              # Click CLI: ecom review | validate
  loader.py           # CSV/Parquet data loading
  metrics.py          # KPI computation
  scoring.py          # Health scoring (0-100, strong/needs_attention/weak)
  report.py           # Report generation (generate_review_json)
  review_engine.py    # Unified period-based review builder (30d/90d/365d)
  periods.py          # Trailing window + data coverage utilities
  ...                 # cohort, product, pricing, decomposition, normalize (+ unused: inventory, site_audit, shopify_api, sync, config)
skills/ecom/          # Claude Code skill (SKILL.md + references/)
  SKILL.md            # LLM instructions for interpreting review.json
  references/         # 6 reference files loaded on-demand for interpretation
tests/                # pytest test suite
```

## Commands

```bash
pip install -e ".[dev]"       # Install for development
pytest tests/ -v              # Run tests
ecom review orders.csv        # Run review (generates review.json)
ecom review orders.csv --period 90d  # Focus on specific period
```

## Conventions

- Package name: `claude-ecom` (pip), `claude_ecom` (import)
- CLI entry point: `ecom` (defined in pyproject.toml)
- All check IDs follow pattern: `{CATEGORY}{NUMBER}` (e.g., R01, C01, P06)
- 3 categories: Revenue (40%), Customer (30%), Product (30%)
- Health levels: strong (75-100), needs_attention (50-74), weak (<50)
- Python handles computation; Claude handles interpretation
- Reference files (references/*.md) are the knowledge base for LLM interpretation
- Reports output to current directory by default (--output flag)
- Never present raw numbers without business context and actionable recommendations
