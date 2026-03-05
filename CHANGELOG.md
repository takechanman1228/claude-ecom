# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2026-03-04

### Changed
- **Project renamed** from `ecom-analytics` to `claude-ecom`
- Package directory: `ecom_analytics/` → `claude_ecom/`
- CLI entry point: `ecom-analytics` → `ecom`
- Skills consolidated: 13 (orchestrator + 12 sub-skills) → 1 (`ecom`)
- Agents removed: 6 agent files deleted (audit logic stays in Python)
- CLI simplified: 11 commands → 2 (`audit` + `review`) + `shopify` subgroup
- Output consolidated: AUDIT-REPORT.md now includes action plan, quick wins, and site audit sections
- New outputs: `executive-summary.md` (one-page stakeholder summary) + `scores.json` (machine-readable)
- Removed standalone commands: `revenue`, `cohort`, `product`, `inventory`, `report`, `site-audit`, `audit-analytics`
- Removed templates: `action_plan.md.j2`, `quick_wins.md.j2`, `site_audit_report.md.j2`
- Removed files: `requirements.txt`, `VERSIONS.md`, root `cli.py`
- Reference `experiment-design.md` removed

### Added
- `executive_summary.md.j2` template
- `generate_executive_summary()` and `generate_scores_json()` in report.py
- Proper `CLAUDE.md` project instructions

## [0.3.0] — 2026-03-04

### Added
- Site / landing page audit (SA01-SA15) using Playwright
- Priority BFS crawler with page type detection
- SITE-AUDIT.md report template
- `ecom-site-audit` sub-skill
- Shopify Admin API integration (setup, sync, audit)
- Business review commands (MBR / QBR / ABR)

## [0.2.0] — 2026-03-04

### Changed
- Unified reference paths: all sub-skills now resolve from `ecom-analytics/references/`
- Check coverage expanded: 19 → 41 checks

### Added
- Reference file existence check in `validate-skills.sh`
- GitHub Actions CI workflow
- 6 audit agents for parallel delegation
- Finding clusters, benchmark comparison, ASCII bar charts

## [0.1.0] — 2026-03-04

Initial release.

- 11 SKILL.md definitions (orchestrator + 10 sub-skills)
- Python package with 84-check scoring system
- Jinja2 report templates
- Shopify CSV and generic CSV format support
