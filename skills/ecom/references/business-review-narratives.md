# Business Review Narrative Templates

Reference file for interpreting business review reports (BUSINESS-REVIEW-REPORT.md,
MBR, QBR, ABR). Use these templates to write natural language interpretation.

---

## 1. Performance Narrative Templates

Select the template matching the growth trajectory:

### Strong Growth (revenue > +10% POP)

> {Period} delivered strong revenue growth of {delta}%, driven primarily by
> {primary_driver: new customers / returning customers / AOV increase}.
> {secondary_observation}. The key question going forward is whether this
> momentum is sustainable or driven by one-time factors.

### Stable Performance (-5% to +10% POP)

> {Period} showed stable performance with revenue {direction} {delta}%,
> largely in line with expectations. {strength_callout}. The focus should
> shift to identifying incremental optimization opportunities rather than
> diagnosing problems.

### Declining Performance (revenue < -5% POP)

> {Period} saw a {delta}% revenue decline, primarily driven by
> {primary_driver: fewer orders / lower AOV / customer churn}.
> {urgency_statement}. Immediate investigation is needed to determine
> whether this is cyclical or structural.

### Volatile / Mixed Signals

> {Period} presents a mixed picture: {positive_signal} but offset by
> {negative_signal}. The {metric} improvement of {value} is encouraging,
> but the {concerning_metric} decline of {value} warrants monitoring.
> Net revenue impact: {direction} {delta}%.

---

## 2. SCQA Finding Templates

### Seasonality Pattern

- **Situation:** Revenue in {period} shows a {direction} pattern consistent with seasonal trends.
- **Complication:** Without separating seasonal effects from underlying growth, strategic decisions may be based on misleading signals.
- **Decision:** Compare YoY (same period last year) rather than POP for strategic decisions. Adjust targets and inventory for expected seasonal shifts.

### Product Lifecycle Shift

- **Situation:** {n} products ({pct}%) are in decline stage, up from {prev_n} in the prior period.
- **Complication:** Aging product portfolio erodes revenue as top-performing products lose momentum. New product introduction may not keep pace.
- **Decision:** Accelerate new product development. Implement markdown cadence for decline-stage products. Cross-sell emerging products from growth/introduction stages.

### Customer Mix Shift

- **Situation:** New customer share {increased/decreased} to {pct}% from {prev_pct}%.
- **Complication:** A shift toward {new/returning} customers impacts AOV, margin, and lifetime value dynamics. {Acquisition-heavy models are expensive; retention-heavy models are vulnerable to churn.}
- **Decision:** {Rebalance acquisition/retention investment. Target F2 conversion for new-heavy; launch win-back for returning-heavy.}

### Competitive Pressure

- **Situation:** AOV declined {delta}% while order volume held steady, suggesting customers are trading down.
- **Complication:** Price sensitivity signals may indicate competitive pressure or changing customer expectations.
- **Decision:** Review competitive pricing landscape. Test value propositions beyond price (convenience, quality, service).

---

## 3. Risk Assessment Rubric

### Severity Determination

| Risk Factor | High (Immediate) | Medium (Monitor) | Low (Awareness) |
|-------------|------------------|-------------------|-----------------|
| Revenue Concentration | Top product >50% share | Top product 30-50% share | Top product <30% share |
| Acquisition Dependency | Returning share <30% | Returning share 30-40% | Returning share >40% |
| Discount Dependency | Avg discount >25% or rising trend | Avg discount 15-25% | Avg discount <15% stable |
| Product Lifecycle | Decline stage >50% | Decline stage 30-50% | Decline stage <30% |
| Growth Sustainability | Revenue AND customers declining | Revenue OR customers declining | Both stable/growing |

### Risk Description Template

> **{Risk Title}** ({Severity})
>
> {Current state with specific numbers}. {Why this matters for the business}.
> {What could happen if unaddressed}. {Monitoring trigger: what to watch}.

---

## 4. Recommendation Templates by Cadence

### MBR (Next 30 Days) -- Operational Actions

Recommendations should be:
- Immediately executable (this week or next)
- Measurable within 30 days
- Focused on quick wins and course corrections

Template:
> **{Action Title}**
> {Specific action steps, 1-2 sentences}
> - Expected Impact: {quantified, e.g., "reduce stockout rate by 5pp"}
> - Timeline: Next 30 days

### QBR (Next 90 Days) -- Tactical + Strategic Mix

Recommendations should be:
- Mix of quick wins (30-day) and structural changes (60-90 day)
- Connected to quarterly targets
- Include progress metrics

Template:
> **{Action Title}**
> {Strategic context + specific implementation, 2-3 sentences}
> - Expected Impact: {quantified with range}
> - Timeline: Next 90 days
> - Success Metric: {what to measure}

### ABR (Next 12 Months) -- Strategic Bets

Recommendations should be:
- Transformational or foundational
- Require investment decisions
- Impact measured over 6-12 months

Template:
> **{Action Title}**
> {Strategic rationale + multi-step plan, 3-4 sentences}
> - Expected Impact: {annual revenue/margin impact estimate}
> - Timeline: Next 12 months
> - Investment Required: {effort/cost estimate}
> - Key Milestones: {quarterly checkpoints}
