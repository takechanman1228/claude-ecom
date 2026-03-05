#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="${HOME}/.claude/skills/ecom"

echo "This will remove claude-ecom skill from ~/.claude/skills/"
echo ""
echo "  Directory to remove:"
echo "    - ${SKILL_DIR}"
echo ""

read -rp "Continue? [y/N] " confirm
if [[ ! "${confirm}" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

rm -rf "${SKILL_DIR}"

echo ""
echo "[ok] claude-ecom uninstalled."
