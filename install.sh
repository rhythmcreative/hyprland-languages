#!/usr/bin/env bash
set -e

# hyprland-languages installer
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_SRC="${SCRIPT_DIR}/bin/hyprland-languages"

echo "=== Installing hyprland-languages ==="

# Check python3
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required but not installed."
    if command -v pacman &>/dev/null; then
        echo "Install it with: sudo pacman -S python"
    elif command -v apt-get &>/dev/null; then
        echo "Install it with: sudo apt install python3"
    elif command -v dnf &>/dev/null; then
        echo "Install it with: sudo dnf install python3"
    elif command -v zypper &>/dev/null; then
        echo "Install it with: sudo zypper install python3"
    elif command -v apk &>/dev/null; then
        echo "Install it with: sudo apk add python3"
    elif command -v xbps-install &>/dev/null; then
        echo "Install it with: sudo xbps-install -S python3"
    fi
    exit 1
fi

# Determine target directory
if [[ $EUID -eq 0 ]]; then
    TARGET_DIR="/usr/local/bin"
else
    TARGET_DIR="${HOME}/.local/bin"
fi

mkdir -p "${TARGET_DIR}"

# Ensure executable permissions
chmod +x "${BIN_SRC}"

# Link binary
TARGET_BIN="${TARGET_DIR}/hyprland-languages"
echo "Creating symlink at ${TARGET_BIN} -> ${BIN_SRC}"
ln -sf "${BIN_SRC}" "${TARGET_BIN}"

# Link python library to user site-packages across distros
USER_SITE=$(python3 -c "import site; print(site.getusersitepackages())" 2>/dev/null || true)
if [[ -z "${USER_SITE}" ]]; then
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    USER_SITE="${HOME}/.local/lib/python${PY_VER}/site-packages"
fi
mkdir -p "${USER_SITE}"
ln -sf "${SCRIPT_DIR}/hyprland_languages" "${USER_SITE}/hyprland_languages"
echo "Linked library to ${USER_SITE}/hyprland_languages"

# Pre-warm cache
echo "Warming cache..."
"${TARGET_BIN}" cache update

echo ""
echo "hyprland-languages successfully installed."
echo "Run '${TARGET_BIN} status' or 'hyprland-languages --help' to get started."
