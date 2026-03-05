#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="${HOME}/.claude/skills/ecom-analytics"

# Sub-skill directories to remove
SUB_SKILLS=(
    ecom-audit
    ecom-cohort
    ecom-context
    ecom-conversion
    ecom-experiment
    ecom-inventory
    ecom-pricing
    ecom-product
    ecom-quickwins
    ecom-revenue
)

echo "This will remove ecom-analytics skills from ~/.claude/skills/"
echo ""
echo "  Directories to remove:"
echo "    - ${SKILL_DIR}"
for s in "${SUB_SKILLS[@]}"; do
    echo "    - ${HOME}/.claude/skills/${s}"
done
echo ""

read -rp "Continue? [y/N] " confirm
if [[ ! "${confirm}" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

rm -rf "${SKILL_DIR}"
for s in "${SUB_SKILLS[@]}"; do
    rm -rf "${HOME}/.claude/skills/${s}"
done

echo ""
echo "[ok] ecom-analytics uninstalled."
