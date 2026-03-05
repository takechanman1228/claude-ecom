# Executive Narrative Templates
<!-- Updated: 2026-03-04 | Source: DR3 -->

## Placeholder definitions

Use these placeholders exactly as shown in the templates. Values should be
pre-formatted for executive readability so the paragraph can be inserted without
additional processing.

| Placeholder | Type | Description |
|---|---|---|
| `{score}` | integer 0-100 | Overall health score |
| `{grade}` | letter A-F | Letter grade |
| `{business_model}` | string | Short descriptor (e.g. `DTC`, `subscription`, `B2B`, `marketplace`, `wholesale`) |
| `{top_category}` | string | Highest-scoring category name |
| `{bottom_category}` | string | Lowest-scoring category name |
| `{top_issue}` | string | Single most critical / highest-leverage issue (plain language, action-oriented) |
| `{cluster_names}` | string | Comma-separated list of the most important finding clusters, ordered by priority. For Grade D/F, pass the top 2 clusters to keep urgency focused |
| `{num_critical}` | integer | Count of critical findings |
| `{num_warnings}` | integer | Count of warning findings |
| `{total_impact}` | string | Business impact estimate with timeframe and direction (e.g. `$420k/yr at risk`, `$310k/yr recoverable upside`) |

---

## Grade A (90-100): Strong store, minor optimizations

### Tone guidance

Professional and confident. Acknowledge strengths clearly, keep opportunities
narrow and practical, and frame experiments as upside on top of a stable
baseline.

### Template

```python
GRADE_A_EXEC_NARRATIVE = (
    "With a {score}/100 health score ({grade}), this {business_model} store is performing strongly—"
    "especially in {top_category}—with only {num_critical} critical issues and {num_warnings} warning-level items detected. "
    "The remaining opportunity clusters are {cluster_names}, led by {top_issue}, representing an estimated annualized impact of {total_impact}. "
    "The quickest win is to lift {bottom_category} by removing the few friction points that remain and validating the uplift using controlled tests. "
    "With that baseline protected, run two low-risk growth experiments (pricing or offer positioning, merchandising, and post-purchase messaging) to compound gains "
    "without destabilizing what is already working."
)
```

### Worked example

> With a 94/100 health score (A), this DTC store is performing strongly--especially in Acquisition & Traffic Quality--with only 0 critical issues and 5 warning-level items detected. The remaining opportunity clusters are Checkout friction, PDP clarity gaps, led by mobile checkout field confusion, representing an estimated annualized impact of $85k/yr recoverable upside. The quickest win is to lift Checkout & Conversion by removing the few friction points that remain and validating the uplift using controlled tests. With that baseline protected, run two low-risk growth experiments (pricing or offer positioning, merchandising, and post-purchase messaging) to compound gains without destabilizing what is already working.

---

## Grade B (75-89): Solid foundation with improvement opportunities

### Tone guidance

Professional but direct. Name the strongest category, then be explicit about
2-3 high-leverage gaps--always tied to revenue and efficiency.

### Template

```python
GRADE_B_EXEC_NARRATIVE = (
    "With a {score}/100 health score ({grade}), this {business_model} store has a solid foundation, with {top_category} currently the strongest area. "
    "The biggest constraints sit in {bottom_category} and the clusters {cluster_names}, where {top_issue} is the most immediate blocker. "
    "We flagged {num_critical} critical issues and {num_warnings} warnings; closing the top two to three gaps is expected to unlock an estimated annualized impact of {total_impact} "
    "through higher conversion, larger order size, and stronger repeat purchase behavior. "
    "Prioritize fixes that remove direct buying friction first, then run two fast-follow experiments to confirm lift before scaling changes broadly."
)
```

### Worked example

> With a 82/100 health score (B), this subscription store has a solid foundation, with Retention & Lifecycle currently the strongest area. The biggest constraints sit in Checkout & Conversion and the clusters Checkout friction, Offer clarity, Site speed, where unclear shipping costs at checkout is the most immediate blocker. We flagged 2 critical issues and 9 warnings; closing the top two to three gaps is expected to unlock an estimated annualized impact of $310k/yr recoverable upside through higher conversion, larger order size, and stronger repeat purchase behavior. Prioritize fixes that remove direct buying friction first, then run two fast-follow experiments to confirm lift before scaling changes broadly.

---

## Grade C (60-74): Notable issues need attention

### Tone guidance

Serious and focused. Lead with the most critical cluster and quantify risk,
then present a clear sequencing roadmap (stabilize -> rebuild trust/clarity ->
compound via retention).

### Template

```python
GRADE_C_EXEC_NARRATIVE = (
    "At {score}/100 ({grade}), performance for this {business_model} store is being materially constrained by {top_issue} within the {cluster_names} cluster set. "
    "Given {num_critical} critical issues and {num_warnings} warnings, we estimate approximately {total_impact} in annualized revenue is at risk if these leaks persist. "
    "First, stabilize the purchase path by fixing the highest-friction elements in {bottom_category} (the steps closest to checkout and payment). "
    "Second, rebuild clarity and trust in the pre-purchase experience by addressing the remaining drivers across {cluster_names} that create hesitation or confusion. "
    "Third, once conversion stops leaking, invest in retention and repeat-purchase levers anchored in {top_category} so the recovery compounds through more returning customers."
)
```

### Worked example

> At 74/100 (C), performance for this DTC store is being materially constrained by mobile checkout errors and weak value messaging within the Conversion friction, Retention erosion cluster set. Given 4 critical issues and 12 warnings, we estimate approximately $420k/yr at risk in annualized revenue is at risk if these leaks persist. First, stabilize the purchase path by fixing the highest-friction elements in Checkout & Conversion (the steps closest to checkout and payment). Second, rebuild clarity and trust in the pre-purchase experience by addressing the remaining drivers across Conversion friction, Retention erosion that create hesitation or confusion. Third, once conversion stops leaking, invest in retention and repeat-purchase levers anchored in Acquisition & Traffic Quality so the recovery compounds through more returning customers.

---

## Grade D (40-59): Significant problems

### Tone guidance

Urgent, direct, and unambiguous. Frame the situation as business risk, be clear
about "what happens if we do nothing," and name the first actions.

### Template

```python
GRADE_D_EXEC_NARRATIVE = (
    "With a {score}/100 health score ({grade}), this {business_model} store is facing significant problems that are likely suppressing sales and wasting acquisition spend. "
    "The most urgent breakdowns sit in {cluster_names}, with {top_issue} and low performance in {bottom_category} indicating structural friction in the path to purchase. "
    "We identified {num_critical} critical issues and {num_warnings} warnings, representing an estimated annualized business impact of {total_impact}. "
    "Immediate action is recommended on the top clusters first, then re-test the full customer path so strengths in {top_category} can translate into dependable growth."
)
```

### Worked example

> With a 55/100 health score (D), this marketplace store is facing significant problems that are likely suppressing sales and wasting acquisition spend. The most urgent breakdowns sit in Checkout failures, Tracking and attribution gaps, with payment method errors on mobile and low performance in Checkout & Conversion indicating structural friction in the path to purchase. We identified 9 critical issues and 18 warnings, representing an estimated annualized business impact of $1.3M/yr at risk. Immediate action is recommended on the top clusters first, then re-test the full customer path so strengths in Product Assortment & Merchandising can translate into dependable growth.

---

## Grade F (<40): Urgent intervention

### Tone guidance

Crisis clarity. Keep it short, explicit, and action-sequenced. Avoid growth
language until baseline transacting and trust are restored.

### Template

```python
GRADE_F_EXEC_NARRATIVE = (
    "At {score}/100 ({grade}), this {business_model} store needs urgent intervention because current issues threaten near-term revenue stability and customer trust. "
    "The most critical failures are concentrated in {cluster_names}, led by {top_issue}, and the weakness in {bottom_category} suggests fundamental blockers to completing purchases. "
    "With {num_critical} critical issues and {num_warnings} warnings, we estimate {total_impact} in annualized impact is at immediate risk without rapid remediation. "
    "Triage step one is to restore the ability to transact end-to-end (pricing, cart, checkout, payments, and fulfillment) and eliminate any hard-stop errors. "
    "Step two is a 30-day stabilization plan to rebuild baseline conversion and retention, then rebuild growth around what works best today in {top_category}."
)
```

### Worked example

> At 32/100 (F), this DTC store needs urgent intervention because current issues threaten near-term revenue stability and customer trust. The most critical failures are concentrated in Checkout hard-stops, Site instability, led by recurring checkout crashes, and the weakness in Checkout & Conversion suggests fundamental blockers to completing purchases. With 16 critical issues and 22 warnings, we estimate $3.6M/yr at risk in annualized impact is at immediate risk without rapid remediation. Triage step one is to restore the ability to transact end-to-end (pricing, cart, checkout, payments, and fulfillment) and eliminate any hard-stop errors. Step two is a 30-day stabilization plan to rebuild baseline conversion and retention, then rebuild growth around what works best today in Acquisition & Traffic Quality.

---

## Reusable sentence modules

### Strengths sentence (for categories scoring 85+)

```python
STRENGTH_SENTENCE = (
    "{category_name} is a clear strength ({category_score}/100), supporting "
    "{business_outcome} through {specific_strength}."
)
```

**Example:**

> Retention & Lifecycle is a clear strength (88/100), supporting repeat revenue through strong post-purchase flows and timely replenishment prompts.

### Key risk sentence (for categories scoring <60)

```python
KEY_RISK_SENTENCE = (
    "{category_name} is underperforming ({category_score}/100), creating "
    "{business_risk}; addressing {first_fix} is the fastest way to reduce "
    "exposure and protect {business_outcome}."
)
```

**Example:**

> Checkout & Conversion is underperforming (52/100), creating avoidable cart abandonment; addressing guest checkout visibility is the fastest way to reduce exposure and protect paid traffic efficiency.

### Transition phrases

Use these to keep a single paragraph flowing from strengths to gaps to impact
to actions:

- "On the strength side, ..."
- "The main constraint on growth is ..."
- "However, the data also shows ..."
- "This matters because ..."
- "In practical terms, that translates to ..."
- "The fastest path to impact is ..."
- "Once that's stabilized, ..."
- "In parallel, ..."
- "Taken together, ..."
- "Net result: ..."

---

## Implementation notes

### Python usage

Pass a dictionary of pre-formatted values and call `.format(**data)` on the
appropriate grade template:

```python
data = {
    "score": 74,
    "grade": "C",
    "top_category": "Acquisition & Traffic Quality",
    "bottom_category": "Checkout & Conversion",
    "top_issue": "mobile checkout errors and weak value messaging",
    "total_impact": "$420k/yr at risk",
    "num_critical": 4,
    "num_warnings": 12,
    "cluster_names": "Conversion friction, Retention erosion",
    "business_model": "DTC",
}

narrative = GRADE_C_EXEC_NARRATIVE.format(**data)
print(narrative)
```

All templates use Python `str.format` placeholders (`{name}`) and are also
compatible with f-strings if you interpolate variables directly. Choose the
grade constant that matches the computed `{grade}` value, then call
`.format(**data)` to produce the final executive paragraph.
