

<p align="center">
  <img src="assets/banner.png" alt="Claude Ecom" width="100%">
</p>

# claude-ecom

Turn an ecommerce orders CSV into an executive-grade business review — KPI decomposition, prioritized findings, and concrete next actions. One command.

<p align="center">
  <img src="assets/claude_ecom_demo.gif" alt="claude-ecom demo" width="100%">
</p>

---

## Who This Is For

- Data Analysts / Marketers who write monthly business reviews from scratch every time
- Sales managers / D2C brand owners, but no analyst on staff
- Anyone who knows revenue dropped but can't explain why

## Quick Start

```bash
# Install
curl -fsSL https://raw.githubusercontent.com/takechanman1228/claude-ecom/v0.1.3/install.sh | bash

# Drop your orders CSV, Start Claude Code, and run:
/ecom review
```
Requires: Claude Code CLI, Python 3.10+, and git

## What You Get

A single `REVIEW.md` that reads like a consultant wrote it:


```
# Business Review
> Revenue reached $9.37M for the year, essentially flat YoY (-1.7%), despite strong
> short-term momentum — the last 90 days surged 84% and November posted +28.5%,
> both driven by Q4 seasonal demand rather than structural growth. The flat annual...
```

```
           30d Pulse       90d Momentum     365d Structure
Revenue    $1.47M (+ 28%)  $3.73M (+ 84%)   $9.37M (= -2%)
Orders     3,499 (+ 26%)   8,814 (+ 60%)    24,812 (- 11%)
AOV        $419 (+ 2%)     $424 (+ 15%)     $378 (+ 10%)
Customers  1,676 (+ 11%)   2,918 (+ 51%)    4,296 (= flat)
...
```
```
Revenue $9.37M (YoY: -1.7%)
├── 🔴 New Customer Revenue $1.45M (15.5%)
│   ├── New Customers: 1,559 (-57.8%)
│   └── New Customer AOV: $305
└── 🟢 Existing Customer Revenue $7.92M (84.5%)
    ├── Returning Customers: 2,737 (+345%)
    ├── Returning AOV: $395
    └── Repeat Purchase Rate: 75.4%
```
Executive summary → Multi-horizon dashboard → KPI trees with 🔴/🟢 signals → Findings with "what / why / what to do" → Prioritized action plan with deadlines, success metrics, and guardrails.
[See a full example output →](examples/online-retail-ii/REVIEW.md)


## Commands

| Command | Description |
|---------|-------------|
| `/ecom review` | Full business review — auto-selects 30d / 90d / 365d |
| `/ecom review 90d` | Quarterly focus |
| `/ecom review How's retention?` | Ask a question instead of a full report |

## Input

Any e-commerce orders CSV works. 

Required columns: order ID, order date, customer ID or email, revenue (after discounts, before tax/shipping).
Optional (enables deeper analysis): quantity, SKU or product name, discount amount. In many cases, column names don't need to match exactly.


## How It Works

```
Orders CSV → Python engine → review.json → Claude → REVIEW.md
```

Python computes every KPI and runs health checks. Claude reads the structured output and writes the business narrative. Numbers are precise because Python owns them. Interpretation is sharp because Claude owns that.



## Example

Tested on [Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) (UCI, CC BY 4.0) — a real UK retailer with ~1M transactions over 2 years.

[See the full report →](examples/online-retail-ii/REVIEW.md) | [Try it yourself →](examples/online-retail-ii/)

## Roadmap

- [ ] Shopify API integration (skip CSV export)
- [ ] Weekly digest mode
- [ ] Multi-store comparison

## License

MIT
