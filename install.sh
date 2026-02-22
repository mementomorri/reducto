#!/bin/bash
set -e

REPO="alexkarsten/reducto"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/reducto"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

detect_platform() {
    OS="$(uname -s)"
    ARCH="$(uname -m)"
    
    case "$OS" in
        Linux*)  OS="Linux" ;;
        Darwin*) OS="Darwin" ;;
        MINGW*|MSYS*|CYGWIN*) OS="Windows" ;;
        *) error "Unsupported OS: $OS" ;;
    esac
    
    case "$ARCH" in
        x86_64|amd64) ARCH="x86_64" ;;
        arm64|aarch64) ARCH="arm64" ;;
        *) error "Unsupported architecture: $ARCH" ;;
    esac
    
    echo "${OS}_${ARCH}"
}

get_latest_version() {
    if command -v curl &> /dev/null; then
        curl -sSL "https://api.github.com/repos/${REPO}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/'
    elif command -v wget &> /dev/null; then
        wget -qO- "https://api.github.com/repos/${REPO}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/'
    else
        error "Neither curl nor wget is available"
    fi
}

check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        warn "Python 3.10+ not found. The AI sidecar requires Python."
        warn "Please install Python 3.10 or later and run: pip install -r \$DATA_DIR/sidecar/pyproject.toml"
        return 1
    fi
    
    PY_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if [[ $(echo "$PY_VERSION < 3.10" | bc -l) -eq 1 ]]; then
        warn "Python $PY_VERSION found, but 3.10+ is required"
        return 1
    fi
    
    info "Found Python $PY_VERSION"
    return 0
}

download_release() {
    local version="$1"
    local platform="$2"
    local archive_name="reducto_${platform}.tar.gz"
    local download_url="https://github.com/${REPO}/releases/download/${version}/${archive_name}"
    
    info "Downloading reducto ${version} for ${platform}..."
    
    TMP_DIR=$(mktemp -d)
    trap "rm -rf $TMP_DIR" EXIT
    
    ARCHIVE_PATH="${TMP_DIR}/${archive_name}"
    
    if command -v curl &> /dev/null; then
        curl -fSL "$download_url" -o "$ARCHIVE_PATH" || error "Failed to download ${archive_name}"
    elif command -v wget &> /dev/null; then
        wget -q "$download_url" -O "$ARCHIVE_PATH" || error "Failed to download ${archive_name}"
    fi
    
    info "Extracting..."
    tar -xzf "$ARCHIVE_PATH" -C "$TMP_DIR"
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$DATA_DIR"
    
    mv "${TMP_DIR}/reducto" "${INSTALL_DIR}/reducto"
    chmod +x "${INSTALL_DIR}/reducto"
    
    if [ -d "${TMP_DIR}/python" ]; then
        info "Installing Python sidecar..."
        rm -rf "${DATA_DIR}/sidecar"
        mv "${TMP_DIR}/python" "${DATA_DIR}/sidecar"
    fi
    
    info "Installed reducto to ${INSTALL_DIR}/reducto"
}

install_python_deps() {
    if [ ! -d "${DATA_DIR}/sidecar" ]; then
        warn "Python sidecar not found at ${DATA_DIR}/sidecar"
        return 1
    fi
    
    if ! check_python; then
        return 1
    fi
    
    info "Installing Python dependencies..."
    
    if command -v uv &> /dev/null; then
        info "Using uv for faster installation..."
        uv pip install --system "${DATA_DIR}/sidecar" 2>/dev/null || \
        uv pip install "${DATA_DIR}/sidecar" --python "$PYTHON_CMD" || \
        warn "uv install failed, falling back to pip"
        return $?
    fi
    
    if command -v pip &> /dev/null; then
        pip install "${DATA_DIR}/sidecar" || \
        $PYTHON_CMD -m pip install "${DATA_DIR}/sidecar" || \
        warn "pip install failed"
        return $?
    fi
    
    warn "Neither uv nor pip found. Please install dependencies manually:"
    warn "  cd ${DATA_DIR}/sidecar && pip install ."
}

update_path() {
    if [[ ":$PATH:" != *":${INSTALL_DIR}:"* ]]; then
        echo ""
        info "Add ${INSTALL_DIR} to your PATH:"
        echo ""
        echo "  export PATH=\"\${PATH}:${INSTALL_DIR}\""
        echo ""
        echo "Add to your shell profile (~/.bashrc, ~/.zshrc, etc.) for persistence."
    fi
}

main() {
    echo ""
    echo "  ____                  _           _    _          "
    echo " |  _ \\ ___  ___ _ __  | |    ___  | | _(_)_ __ ___ "
    echo " | |_) / _ \\/ __| '_ \\ | |   / _ \\ | |/ / | '_ \` _ \\"
    echo " |  _ <  __/\\__ \\ |_) || |__|  __/ |   <| | | | | | |"
    echo " |_| \\_\\___||___/ .__/ |_____\\___| |_|\\_\\_|_| |_| |_|"
    echo "                |_|                                  "
    echo ""
    
    VERSION="${VERSION:-$(get_latest_version)}"
    PLATFORM=$(detect_platform)
    
    info "Installing reducto ${VERSION} for ${PLATFORM}"
    
    download_release "$VERSION" "$PLATFORM"
    install_python_deps || true
    update_path
    
    echo ""
    info "Installation complete!"
    info "Run 'reducto --help' to get started."
}

main "$@"