# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] — 2026-03-04

### Changed
- Unified reference paths: all sub-skills now resolve from `ecom-analytics/references/`
- Deduplicated business model detection table (canonical source: `ecom-context`)
- Deduplicated scoring weights table (canonical source: `references/scoring-system.md`)

### Added
- Reference file existence check in `validate-skills.sh`
- GitHub Actions CI workflow (`.github/workflows/ci.yml`)
- `.gitignore` for Python build artifacts
- This CHANGELOG file

## [0.1.0] — 2026-03-04

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
