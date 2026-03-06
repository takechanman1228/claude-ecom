

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

<!-- TODO: sample REVIEW.md screenshot -->

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/takechanman1228/claude-ecom/main/install.sh | bash
```

Or clone and run:

```bash
git clone https://github.com/takechanman1228/claude-ecom.git
cd claude-ecom && bash install.sh
```

That's it. The skill is ready in Claude Code.

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

```bash
bash install.sh --with-cli
# or
pip install -e .

ecom review orders.csv
ecom review orders.csv --period 90d
ecom validate orders.csv
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
