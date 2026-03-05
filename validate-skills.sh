#!/usr/bin/env bash
# validate-skills.sh — Validate SKILL.md frontmatter for ecom-analytics skills
#
# Checks:
#   1. Each SKILL.md has a YAML frontmatter block (--- ... ---)
#   2. Required fields: name, description
#   3. Main orchestrator has argument-hint and allowed-tools
#   4. name field matches directory name

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

    # Orchestrator-specific: check argument-hint and allowed-tools
    if [ "$dir_name" = "ecom-analytics" ]; then
        if ! echo "$frontmatter" | grep -q '^argument-hint:'; then
            echo "FAIL  $dir_name: Orchestrator missing 'argument-hint'"
            ERRORS=$((ERRORS + 1))
        fi
        if ! echo "$frontmatter" | grep -q '^allowed-tools:'; then
            echo "FAIL  $dir_name: Orchestrator missing 'allowed-tools'"
            ERRORS=$((ERRORS + 1))
        fi
    fi
done

# --- Reference file existence check ---
echo ""
echo "=== Reference File Validation ==="
echo ""
ref_dir="$SKILLS_DIR/ecom-analytics/references"

if [ ! -d "$ref_dir" ]; then
    echo "FAIL  Reference directory not found: $ref_dir"
    ERRORS=$((ERRORS + 1))
else
    for skill_md in "$SKILLS_DIR"/*/SKILL.md; do
        dir_name="$(basename "$(dirname "$skill_md")")"
        # Extract referenced .md filenames from ecom-analytics/references/ context
        refs=$(grep -oE '[a-z][-a-z]*\.md' "$skill_md" | grep -v 'SKILL.md' | sort -u || true)
        for ref in $refs; do
            # Skip output files (generated, not references)
            if echo "$ref" | grep -qiE '^(audit-report|action-plan|quick-wins)'; then
                continue
            fi
            # Check against actual files in references directory
            known_refs=$(ls "$ref_dir"/*.md 2>/dev/null | xargs -I{} basename {} | sort)
            if echo "$known_refs" | grep -qx "$ref"; then
                if [ ! -f "$ref_dir/$ref" ]; then
                    echo "FAIL  $dir_name: Reference '$ref' not found in $ref_dir"
                    ERRORS=$((ERRORS + 1))
                else
                    echo "PASS  $dir_name: '$ref' exists"
                fi
            fi
        done
    done
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
