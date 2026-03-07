#!/usr/bin/env bash
set -euo pipefail

# claude-ecom Installer
# Wraps in main() to prevent partial execution on network failure

main() {
    SKILL_DIR="${HOME}/.claude/skills/ecom"
    VENV_DIR="${SKILL_DIR}/.venv"
    REPO_URL="https://github.com/takechanman1228/claude-ecom"

    echo "════════════════════════════════════════"
    echo "║   claude-ecom - Installer            ║"
    echo "║   Ecom Data Analytics Skill          ║"
    echo "════════════════════════════════════════"
    echo ""

    # Check prerequisites
    command -v git >/dev/null 2>&1 || { echo "Error: git is required but not installed."; exit 1; }
    echo "[ok] Git detected"

    command -v python3 >/dev/null 2>&1 || {
        echo "Error: Python 3 is required but not installed."
        echo "  Install from https://python.org or via your package manager."
        echo "  macOS: brew install python@3.12"
        exit 1
    }
    echo "[ok] Python 3 detected"

    python3 -c "import sys; assert sys.version_info >= (3,10), f'Python 3.10+ required, found {sys.version}'" 2>/dev/null || {
        echo "Error: Python 3.10+ is required. Found: $(python3 --version)"
        echo "  Upgrade from https://python.org or via your package manager."
        echo "  macOS: brew install python@3.12"
        exit 1
    }
    echo "[ok] Python $(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

    python3 -c "import venv" 2>/dev/null || {
        echo "Error: Python venv module is required but not available."
        echo "  Debian/Ubuntu: sudo apt install python3-venv"
        echo "  Fedora: sudo dnf install python3-venv"
        exit 1
    }

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

    # Create private venv and install Python CLI
    echo "[..] Creating Python environment..."
    python3 -m venv "${VENV_DIR}"

    echo "[..] Installing Python CLI (this may take a minute)..."
    "${VENV_DIR}/bin/pip" install --upgrade pip --quiet 2>/dev/null
    "${VENV_DIR}/bin/pip" install "${TEMP_DIR}/claude-ecom" --quiet

    # Create wrapper script
    mkdir -p "${SKILL_DIR}/bin"
    cat > "${SKILL_DIR}/bin/ecom" << 'WRAPPER'
#!/usr/bin/env bash
exec "$(dirname "$0")/../.venv/bin/python" -m claude_ecom.cli "$@"
WRAPPER
    chmod +x "${SKILL_DIR}/bin/ecom"

    echo ""
    echo "[ok] claude-ecom installed successfully!"
    echo ""
    echo "  Installed:"
    echo "    - 1 skill (ecom)"
    echo "    - 6 reference files"
    echo "    - Python CLI (in private venv)"
    echo ""
    echo "  Usage:"
    echo "    1. Start Claude Code:  claude"
    echo "    2. Run command:        /ecom review"
    echo ""
    echo "  CLI: ~/.claude/skills/ecom/bin/ecom review orders.csv"
    echo ""
    echo "  To uninstall: bash uninstall.sh"
}

main "$@"
