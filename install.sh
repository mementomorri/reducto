#!/bin/bash
set -e

INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
PYTHON_CMD="${PYTHON_CMD:-python3}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

if ! command -v "$PYTHON_CMD" &>/dev/null; then
  error "Python 3.14+ required. Install python3 and retry."
fi

PY_VER=$("$PYTHON_CMD" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if ! "$PYTHON_CMD" -c "import sys; sys.exit(0 if sys.version_info >= (3, 14) else 1)"; then
  error "Python $PY_VER found; 3.14+ required."
fi

info "Installing reducto with $PYTHON_CMD..."
if command -v uv &>/dev/null; then
  uv pip install --system -e ".[embeddings]" || uv pip install -e ".[embeddings]"
else
  "$PYTHON_CMD" -m pip install --user -e ".[embeddings]"
fi

if command -v reducto &>/dev/null; then
  info "Installed: $(reducto version)"
else
  warn "Add $HOME/.local/bin to PATH if 'reducto' is not found."
fi

info "Done."
