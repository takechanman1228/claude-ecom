# Contributing

Thanks for your interest in contributing to claude-ecom!

## Getting Started

```bash
git clone <your-fork-url>
cd claude-ecom
pip install -e ".[dev]"
pytest tests/ -v
```

## Adding New Checks

Each check produces a `CheckResult` with these fields:

```python
CheckResult(
    check_id="R16",
    category="revenue",       # revenue | customer | product
    severity="high",          # critical | high | medium | low
    result="fail",            # pass | watch | warning | fail | na
    message="MoM revenue growth: -10.0%",
    current_value=-0.10,
    threshold=0.0,
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

1. Add the check function in the appropriate module (`claude_ecom/metrics.py`, `decomposition.py`, etc.)
2. Add the check definition to the matching reference file in `skills/ecom/references/`
3. Add the check to `_build_checks()` in `claude_ecom/review_engine.py`
4. Add a test in `tests/`
5. Run `pytest tests/ -v` to verify

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
