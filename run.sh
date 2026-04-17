#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  EKX Live Feedback App — Direct Python setup & run script
#  Works on macOS, Linux, and Windows (Git Bash / WSL)
# ─────────────────────────────────────────────────────────────────────────────

set -e

# ── Colour helpers ────────────────────────────────────────────────────────────
BLUE='\033[0;34m'; BOLD='\033[1m'; RESET='\033[0m'; GREEN='\033[0;32m'
info()    { echo -e "${BLUE}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }

echo ""
echo -e "${BOLD}  EKX Live Feedback App${RESET}"
echo    "  ─────────────────────────────────────────────"
echo ""

# ── 1. Check Python version (3.9+) ───────────────────────────────────────────
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VER=$("$cmd" -c "import sys; print(sys.version_info >= (3,9))" 2>/dev/null)
        if [ "$VER" = "True" ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "  ERROR: Python 3.9 or higher is required but was not found."
    echo "  Download it from: https://www.python.org/downloads/"
    exit 1
fi

PY_VERSION=$("$PYTHON" --version)
success "Found $PY_VERSION"

# ── 2. Create virtual environment (if not already present) ───────────────────
VENV_DIR="$(dirname "$0")/venv"

if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtual environment at ./venv ..."
    "$PYTHON" -m venv "$VENV_DIR"
    success "Virtual environment created"
else
    info "Virtual environment already exists — skipping creation"
fi

# Activate it
if [ -f "$VENV_DIR/bin/activate" ]; then
    # macOS / Linux
    source "$VENV_DIR/bin/activate"
elif [ -f "$VENV_DIR/Scripts/activate" ]; then
    # Windows Git Bash / WSL
    source "$VENV_DIR/Scripts/activate"
else
    echo "  ERROR: Could not activate virtual environment."
    exit 1
fi

success "Virtual environment activated"

# ── 3. Install dependencies ───────────────────────────────────────────────────
info "Installing dependencies from requirements.txt ..."
pip install --quiet --upgrade pip
pip install --quiet -r "$(dirname "$0")/requirements.txt"
success "Dependencies installed"

# ── 4. Detect local IP for QR code ───────────────────────────────────────────
LOCAL_IP=$(python -c "
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    print(s.getsockname()[0])
    s.close()
except:
    print('localhost')
")

PORT=${PORT:-5000}

echo ""
echo -e "${BOLD}  ─────────────────────────────────────────────${RESET}"
echo -e "  Admin UI   →  ${BOLD}http://localhost:$PORT${RESET}"
echo -e "  On network →  ${BOLD}http://$LOCAL_IP:$PORT${RESET}  (use this for QR codes)"
echo -e "${BOLD}  ─────────────────────────────────────────────${RESET}"
echo ""
echo "  Press CTRL+C to stop the server."
echo ""

# ── 5. Start the app ──────────────────────────────────────────────────────────
cd "$(dirname "$0")"
python app.py
