

<p align="center">
  <img src="assets/banner.png" alt="Claude Ecom" width="100%">
</p>

# claude-ecom

Turn an ecommerce orders CSV into an executive-grade business review — KPI decomposition, prioritized findings, and concrete next actions. One command.

---

## Who This Is For

- Data Analysts / Marketers who write monthly business reviews from scratch every time
- D2C brand owners who have Shopify order exports but no analyst on staff
- Anyone who knows revenue dropped but can't explain why

## What You Get

A single `REVIEW.md` that reads like a consultant wrote it:

```
Revenue $1.38M (+25.7% YoY)
├── New Customer Revenue $584K (42.3%)
│   ├── New Customers: 1,472 (+8.2%)
│   └── New Customer AOV: $397 (+3.1%)
└── Existing Customer Revenue $799K (57.7%)
    ├── Returning Customers: 1,293 (+12.4%)
    ├── Returning AOV: $618 (+14.8%)
    └── Repeat Purchase Rate: 38%
```

Executive summary → KPI trees → findings with "what / why / what to do" → prioritized action plan with deadlines and guardrails.

Health checks across Revenue (40%), Customer (30%), and Product (30%) power the signals automatically.

## Example

Tested on [Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) (UCI, CC BY 4.0) — a real UK retailer with ~1M transactions over 2 years.

> Revenue reached $8.6M for the year but was essentially flat YoY (-2.3%), masking a dramatic shift underneath: new customer acquisition collapsed 57.7% while the returning customer base expanded nearly 4x. Short-term momentum is strong — the last 90 days surged 87% on Q4 seasonal demand — but this growth is built entirely on an aging customer base and aging catalog (60% of SKUs in decline stage). The most urgent priority is relaunching acquisition channels to replenish the customer pipeline before retention gains plateau.

```
            30d Pulse        90d Momentum      365d Structure
Revenue     $1.32M (+ 27%)   $3.46M (+ 87%)    $8.6M (- 2%)
Orders      2,681 (+ 28%)    6,626 (+ 68%)     17,756 (- 4%)
AOV         $494 (- 1%)      $522 (+ 11%)      $484 (+ 1%)
Customers   1,628 (+ 12%)    2,889 (+ 52%)     4,264 (= flat)
```

The report surfaces findings with business context and concrete actions:

### New customer acquisition collapsed (365d)

**What is:** New customer count fell 57.7% YoY (from ~3,700 to 1,566), and new customer revenue share dropped to 20.3%.

**Why it matters:** The 72.4% repeat purchase rate and 5-day median time-to-second-purchase are exceptional — well above D2C benchmarks. However, even the strongest retention engine needs fresh customers entering the top of the funnel. At the current rate of decline, the returning customer base will begin shrinking within 2-3 quarters as natural churn outpaces new-to-repeat conversion.

**What to do:** Reactivate acquisition channels with dedicated budget, separate from retention spend, targeting a return to 200+ new customers per month.

[See the full report →](examples/online-retail-ii/REVIEW.md) | [Try it yourself →](examples/online-retail-ii/)

## Prerequisites

- **Python 3.10+** — [python.org](https://python.org) or `brew install python@3.12`
- **git** — [git-scm.com](https://git-scm.com) or `brew install git`

## Install

### Claude Code skill (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/takechanman1228/claude-ecom/v0.1.2/install.sh | bash
```

### CLI only (for developers)

```bash
pipx install claude-ecom
```

<details>
<summary>Development install (from source)</summary>

```bash
git clone https://github.com/takechanman1228/claude-ecom.git
cd claude-ecom && bash install.sh
```

This installs from local source instead of PyPI — useful for development and testing.

</details>

The installer creates a private Python environment in `~/.claude/skills/ecom/.venv/` — no global packages are modified. The skill is ready in Claude Code.

## Usage

```bash
/ecom review                        # full business review — auto-selects 30d / 90d / 365d
/ecom review 90d                    # quarterly focus
/ecom review How's retention?       # ask a question instead of generating a full report
```

Drop your orders CSV into the conversation and run the command. Claude handles the rest.

## Input

Any ecommerce orders CSV works. Shopify exports drop in directly.

Required columns: order ID, order date, customer ID or email, revenue (after discounts, before tax/shipping).
Optional (enables deeper analysis): quantity, SKU or product name, discount amount.

## How It Works

```
Orders CSV → Python engine → review.json → Claude → REVIEW.md
```

Python computes every KPI and runs health checks. Claude reads the structured output and writes the business narrative. Numbers are precise because Python owns them. Interpretation is sharp because Claude owns that.

<details>
<summary>Using the Python CLI directly</summary>

After installation, the CLI is available via the wrapper:

```bash
~/.claude/skills/ecom/bin/ecom review orders.csv
~/.claude/skills/ecom/bin/ecom review orders.csv --period 90d
~/.claude/skills/ecom/bin/ecom validate orders.csv
```

</details>

<details>
<summary>Development</summary>

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

</details>

## Roadmap

- [ ] Shopify API integration (skip CSV export)
- [ ] Weekly digest mode
- [ ] Multi-store comparison

## License

MIT
