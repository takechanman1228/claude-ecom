# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-03-06

Initial release.

- Single `ecom review` command for full-store health review
- Multi-period architecture: 30d / 90d / 365d trailing windows with automatic data coverage detection
- ~30 health checks across Revenue (40%), Customer (30%), Product (30%)
- Each check returns pass / watch / fail
- KPI tree with growth drivers (AOV / volume / mix effects)
- review.json output with top issues and action candidates
- Claude Code skill (`/ecom review`) with full review and focused query modes
- Shopify CSV and generic CSV format support with fuzzy column mapping
- Install script for bash and PowerShell
