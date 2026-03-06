#!/usr/bin/env bash
set -euo pipefail

# claude-ecom Installer
# Wraps in main() to prevent partial execution on network failure

main() {
    SKILL_DIR="${HOME}/.claude/skills/ecom"
    REPO_URL="https://github.com/takechanman1228/claude-ecom"
    WITH_CLI=false

    # Parse arguments
    for arg in "$@"; do
        case "$arg" in
            --with-cli) WITH_CLI=true ;;
            *) echo "Unknown argument: $arg"; exit 1 ;;
        esac
    done

    echo "════════════════════════════════════════"
    echo "║   claude-ecom - Installer            ║"
    echo "║   Ecom Data Analytics Skill          ║"
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

    echo "[..] Downloading claude-ecom..."
    if ! git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}/claude-ecom" 2>/dev/null; then
        echo "Error: Failed to clone from ${REPO_URL}"
        echo "  If the repository hasn't been created yet, update REPO_URL in this script."
        exit 1
    fi

    # Copy skill + references
    echo "[..] Installing skill files..."
    cp "${TEMP_DIR}/claude-ecom/skills/ecom/SKILL.md" "${SKILL_DIR}/SKILL.md"
    cp "${TEMP_DIR}/claude-ecom/skills/ecom/references/"*.md "${SKILL_DIR}/references/"

    # Optional: install Python CLI
    if [ "${WITH_CLI}" = true ]; then
        echo "[..] Installing Python CLI..."
        command -v pip >/dev/null 2>&1 || { echo "Error: pip is required for --with-cli."; exit 1; }
        pip install "${TEMP_DIR}/claude-ecom" --quiet
    fi

    echo ""
    echo "[ok] claude-ecom installed successfully!"
    echo ""
    echo "  Installed:"
    echo "    - 1 skill (ecom)"
    echo "    - 6 reference files"
    echo ""
    echo "  Usage:"
    echo "    1. Start Claude Code:  claude"
    echo "    2. Run command:        /ecom review"
    echo ""
    if [ "${WITH_CLI}" = true ]; then
        echo "  CLI installed. Run: ecom review orders.csv"
    else
        echo "  To also install the Python CLI: bash install.sh --with-cli"
    fi
    echo ""
    echo "  To uninstall: bash uninstall.sh"
}

main "$@"
