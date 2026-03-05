#!/usr/bin/env bash
set -euo pipefail

# ecom-analytics Installer
# Wraps in main() to prevent partial execution on network failure

main() {
    SKILL_DIR="${HOME}/.claude/skills/ecom-analytics"
    # TODO: Replace with actual repo URL once created
    REPO_URL="https://github.com/<user>/ecom-analytics"
    WITH_CLI=false

    # Parse arguments
    for arg in "$@"; do
        case "$arg" in
            --with-cli) WITH_CLI=true ;;
            *) echo "Unknown argument: $arg"; exit 1 ;;
        esac
    done

    echo "════════════════════════════════════════"
    echo "║   ecom-analytics - Installer         ║"
    echo "║   EC Data Analytics Skill            ║"
    echo "════════════════════════════════════════"
    echo ""

    # Check prerequisites
    command -v git >/dev/null 2>&1 || { echo "Error: git is required but not installed."; exit 1; }
    echo "[ok] Git detected"

    # Create directories
    mkdir -p "${SKILL_DIR}/references"

    # Clone to temp dir
    TEMP_DIR=$(mktemp -d)
    trap "rm -rf ${TEMP_DIR}" EXIT

    echo "[..] Downloading ecom-analytics..."
    if ! git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}/ecom-analytics" 2>/dev/null; then
        echo "Error: Failed to clone from ${REPO_URL}"
        echo "  If the repository hasn't been created yet, update REPO_URL in this script."
        exit 1
    fi

    # Copy main skill + references
    echo "[..] Installing skill files..."
    cp "${TEMP_DIR}/ecom-analytics/skills/ecom-analytics/SKILL.md" "${SKILL_DIR}/SKILL.md"
    cp "${TEMP_DIR}/ecom-analytics/skills/ecom-analytics/references/"*.md "${SKILL_DIR}/references/"

    # Copy sub-skills (10 sub-skills)
    echo "[..] Installing sub-skills..."
    for skill_dir in "${TEMP_DIR}/ecom-analytics/skills"/ecom-*/; do
        skill_name=$(basename "${skill_dir}")
        # Skip the main orchestrator (already copied)
        if [ "${skill_name}" = "ecom-analytics" ]; then
            continue
        fi
        target="${HOME}/.claude/skills/${skill_name}"
        mkdir -p "${target}"
        cp "${skill_dir}SKILL.md" "${target}/SKILL.md"
    done

    # Copy audit agents
    echo "[..] Installing audit agents..."
    AGENT_DIR="${HOME}/.claude/agents"
    mkdir -p "${AGENT_DIR}"
    for agent_file in "${TEMP_DIR}/ecom-analytics/agents/"audit-*.md; do
        cp "${agent_file}" "${AGENT_DIR}/"
    done

    # Optional: install Python CLI
    if [ "${WITH_CLI}" = true ]; then
        echo "[..] Installing Python CLI..."
        command -v pip >/dev/null 2>&1 || { echo "Error: pip is required for --with-cli."; exit 1; }
        pip install "${TEMP_DIR}/ecom-analytics" --quiet
    fi

    echo ""
    echo "[ok] ecom-analytics installed successfully!"
    echo ""
    echo "  Installed:"
    echo "    - 1 main skill (ecom-analytics orchestrator)"
    echo "    - 11 sub-skills"
    echo "    - 6 audit agents"
    echo "    - 11 reference files"
    echo ""
    echo "  Usage:"
    echo "    1. Start Claude Code:  claude"
    echo "    2. Run commands:       /ecom-analytics audit"
    echo "                           /ecom-analytics revenue"
    echo "                           /ecom-analytics cohort"
    echo ""
    if [ "${WITH_CLI}" = true ]; then
        echo "  CLI installed. Run: ecom-analytics audit orders.csv"
    else
        echo "  To also install the Python CLI: bash install.sh --with-cli"
    fi
    echo ""
    echo "  To uninstall: bash uninstall.sh"
}

main "$@"
