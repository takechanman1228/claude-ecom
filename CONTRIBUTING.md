# Contributing

Thanks for your interest in contributing to ecom-analytics!

## Getting Started

```bash
git clone <your-fork-url>
cd ecom-analytics
pip install -e ".[dev]"
pytest tests/ -v
```

## Adding New Checks

Each check produces a `CheckResult` with these fields:

```python
CheckResult(
    check_id="R16",           # Category prefix + number
    name="New Revenue Check",
    severity="high",          # critical | high | medium | low
    passed=True,              # Whether the check passed
    score=0.85,               # 0.0–1.0
    detail="Explanation of the finding",
    recommendation="What to do about it",
)
```

**Severity guidelines:**

| Severity | When to use | Multiplier |
|----------|-------------|-----------|
| Critical | Direct revenue loss, data integrity | 5.0x |
| High | Significant missed opportunity | 3.0x |
| Medium | Improvement opportunity | 1.5x |
| Low | Nice-to-have optimization | 0.5x |

**Steps:**

1. Add the check function in the appropriate module (`ecom_analytics/metrics.py`, `decomposition.py`, etc.)
2. Add the check definition to the matching reference file in `skills/ecom-analytics/references/`
3. Register the check in `ecom_analytics/scoring.py`
4. Add a test in `tests/`
5. Run `pytest tests/ -v` to verify

## Adding New Skills

1. Create `skills/ecom-<name>/SKILL.md` with YAML frontmatter:

```yaml
---
name: ecom-<name>
description: >
  When to use this skill. Include trigger phrases.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---
```

2. Register the sub-skill in the main `skills/ecom-analytics/SKILL.md`
3. Run `bash validate-skills.sh` to verify frontmatter is valid

## Improving Existing Skills

- Update benchmark thresholds in `skills/ecom-analytics/references/benchmarks.md`
- Adjust severity levels based on real-world audit feedback
- Keep reference files focused and under 300 lines each

## Pull Request Process

1. **Branch naming:** `feature/<description>`, `fix/<description>`, or `docs/<description>`
2. **Tests required:** All PRs must pass `pytest tests/ -v`
3. **Skill validation:** Run `bash validate-skills.sh` if skills were modified
4. **One concern per PR:** Keep PRs focused on a single change

## Skill Quality Checklist

Before submitting, verify:

- [ ] `name` in frontmatter matches directory name
- [ ] `description` includes trigger phrases for agent routing
- [ ] Check thresholds are backed by industry benchmarks or documented reasoning
- [ ] No hardcoded paths or credentials
- [ ] Tests cover the new/changed functionality
