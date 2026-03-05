#!/usr/bin/env bash
# validate-skills.sh — Validate SKILL.md frontmatter for claude-ecom skill

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$SCRIPT_DIR/skills"
ERRORS=0
CHECKED=0

echo "=== SKILL.md Validation ==="
echo ""

for skill_md in "$SKILLS_DIR"/*/SKILL.md; do
    dir_name="$(basename "$(dirname "$skill_md")")"
    CHECKED=$((CHECKED + 1))

    # Check frontmatter exists
    if ! head -1 "$skill_md" | grep -q '^---$'; then
        echo "FAIL  $dir_name: Missing YAML frontmatter (no opening ---)"
        ERRORS=$((ERRORS + 1))
        continue
    fi

    # Extract frontmatter (between first and second ---)
    frontmatter=$(awk '/^---$/{n++; next} n==1{print} n>=2{exit}' "$skill_md")

    # Check name field
    name=$(echo "$frontmatter" | grep '^name:' | head -1 | sed 's/^name:[[:space:]]*//')
    if [ -z "$name" ]; then
        echo "FAIL  $dir_name: Missing 'name' field"
        ERRORS=$((ERRORS + 1))
    elif [ "$name" != "$dir_name" ]; then
        echo "FAIL  $dir_name: name '$name' does not match directory '$dir_name'"
        ERRORS=$((ERRORS + 1))
    else
        echo "PASS  $dir_name: name='$name'"
    fi

    # Check description field
    if ! echo "$frontmatter" | grep -q '^description:'; then
        echo "FAIL  $dir_name: Missing 'description' field"
        ERRORS=$((ERRORS + 1))
    fi

    # Check argument-hint and allowed-tools
    if ! echo "$frontmatter" | grep -q '^argument-hint:'; then
        echo "FAIL  $dir_name: Missing 'argument-hint'"
        ERRORS=$((ERRORS + 1))
    fi
    if ! echo "$frontmatter" | grep -q '^allowed-tools:'; then
        echo "FAIL  $dir_name: Missing 'allowed-tools'"
        ERRORS=$((ERRORS + 1))
    fi
done

# --- Reference file existence check ---
echo ""
echo "=== Reference File Validation ==="
echo ""
ref_dir="$SKILLS_DIR/ecom/references"

if [ ! -d "$ref_dir" ]; then
    echo "FAIL  Reference directory not found: $ref_dir"
    ERRORS=$((ERRORS + 1))
else
    ref_count=$(ls "$ref_dir"/*.md 2>/dev/null | wc -l | tr -d ' ')
    echo "PASS  Found $ref_count reference files in $ref_dir"
fi

echo ""
echo "=== Results ==="
echo "Checked: $CHECKED SKILL.md files"
echo "Errors:  $ERRORS"

if [ "$ERRORS" -gt 0 ]; then
    echo "FAILED"
    exit 1
else
    echo "ALL PASSED"
    exit 0
fi
