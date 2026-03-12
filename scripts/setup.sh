#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SKILL_DIR="${HOME}/.claude/skills/ecom"
VENV_DIR="${SKILL_DIR}/.venv"

# Fast path: already installed
if [ -x "${SKILL_DIR}/bin/ecom" ] && "${VENV_DIR}/bin/python" -c "import claude_ecom" 2>/dev/null; then
    exit 0
fi

# Check Python 3.10+
if ! command -v python3 &>/dev/null; then
    echo "claude-ecom: Python 3.10+ required. Install from https://python.org" >&2
    exit 0  # Don't block session
fi

python3 -c "import sys; assert sys.version_info >= (3,10)" 2>/dev/null || {
    echo "claude-ecom: Python 3.10+ required. Found: $(python3 --version)" >&2
    exit 0
}

# Create venv + install
mkdir -p "${SKILL_DIR}/bin"
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/pip" install --upgrade pip --quiet 2>/dev/null
"${VENV_DIR}/bin/pip" install "${REPO_DIR}" --quiet

# Create wrapper
cat > "${SKILL_DIR}/bin/ecom" << 'WRAPPER'
#!/usr/bin/env bash
exec "$(dirname "$0")/../.venv/bin/python" -m claude_ecom.cli "$@"
WRAPPER
chmod +x "${SKILL_DIR}/bin/ecom"

echo "claude-ecom: installed successfully"
