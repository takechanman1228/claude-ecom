#!/usr/bin/env bash
set -euo pipefail

# claude-ecom Installer
# Wraps in main() to prevent partial execution on network failure

main() {
    VERSION="0.1.2"
    SKILL_DIR="${HOME}/.claude/skills/ecom"
    VENV_DIR="${SKILL_DIR}/.venv"
    REPO_URL="https://github.com/takechanman1228/claude-ecom"
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

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

    # Determine install mode: dev (local source) vs stable (PyPI)
    # When piped via curl|bash, $0 is "bash" — not "install.sh"
    if [ "$(basename "$0")" = "install.sh" ] && [ -f "${SCRIPT_DIR}/pyproject.toml" ]; then
        # Dev mode: running from cloned repo — install from local source
        echo "[..] Installing from local source (dev mode)..."

        # Copy skill + references
        echo "[..] Installing skill files..."
        cp "${SCRIPT_DIR}/skills/ecom/SKILL.md" "${SKILL_DIR}/SKILL.md"
        cp "${SCRIPT_DIR}/skills/ecom/references/"*.md "${SKILL_DIR}/references/"

        # Create private venv and install Python CLI from source
        echo "[..] Creating Python environment..."
        python3 -m venv "${VENV_DIR}"

        echo "[..] Installing Python CLI (this may take a minute)..."
        "${VENV_DIR}/bin/pip" install --upgrade pip --quiet 2>/dev/null
        "${VENV_DIR}/bin/pip" install "${SCRIPT_DIR}" --quiet
    else
        # Stable mode: downloaded via curl — install from tagged release + PyPI
        echo "[..] Installing claude-ecom v${VERSION}..."

        TEMP_DIR=$(mktemp -d)
        trap "rm -rf ${TEMP_DIR}" EXIT

        echo "[..] Downloading tagged release v${VERSION}..."
        if ! git clone --depth 1 --branch "v${VERSION}" "${REPO_URL}" "${TEMP_DIR}/claude-ecom" 2>/dev/null; then
            echo "Error: Failed to download v${VERSION} from ${REPO_URL}"
            exit 1
        fi

        # Copy skill + references from tagged release
        echo "[..] Installing skill files..."
        cp "${TEMP_DIR}/claude-ecom/skills/ecom/SKILL.md" "${SKILL_DIR}/SKILL.md"
        cp "${TEMP_DIR}/claude-ecom/skills/ecom/references/"*.md "${SKILL_DIR}/references/"

        # Create private venv and install Python CLI from PyPI
        echo "[..] Creating Python environment..."
        python3 -m venv "${VENV_DIR}"

        echo "[..] Installing Python CLI (this may take a minute)..."
        "${VENV_DIR}/bin/pip" install --upgrade pip --quiet 2>/dev/null
        "${VENV_DIR}/bin/pip" install "claude-ecom==${VERSION}" --quiet
    fi

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
