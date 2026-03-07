# CLAUDE.md

## Project: claude-ecom

Ecommerce data analytics toolkit -- review and improve online stores.

## Architecture: Hybrid (Python Compute + LLM Interpretation)

```
Order CSV Data
    |
    v
Python CLI (ecom review)    <-- Deterministic: KPI calc, scoring, check evaluation
    |
    v
review.json / review_{period}.json   <-- Machine-readable structured data
    |
    v
Claude (SKILL.md)           <-- LLM: reads review.json + reference files, generates
    |                            natural language report with business interpretation
    v
REVIEW.md / REVIEW_{PERIOD}.md       <-- Human-readable: narrative insights, not just numbers
```

**Key principle:** Python computes the numbers. Claude interprets them.

## Structure

```
claude_ecom/          # Python package (pip install -e .)
  cli.py              # Click CLI: ecom review | validate
  loader.py           # CSV/Parquet data loading
  checks.py           # Check result types, impact estimation, action builders
  report.py           # Report generation (generate_review_json)
  review_engine.py    # Unified period-based review builder (30d/90d/365d)
  periods.py          # Trailing window + data coverage utilities
  scoring.py          # Health scoring, top issues, action candidates
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
- Check IDs are semantic snake_case keys (e.g., `monthly_revenue_trend`, `repeat_purchase_rate`, `multi_item_order_rate`)
- 3 categories: Revenue, Customer, Product
- Each check returns pass / watch / fail (no numeric scores)
- Python handles computation; Claude handles interpretation
- Reference files (references/*.md) are the knowledge base for LLM interpretation
- Reports output to current directory by default (--output flag)
- Never present raw numbers without business context and actionable recommendations
