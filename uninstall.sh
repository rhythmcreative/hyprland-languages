#!/usr/bin/env bash
set -e

echo "=== Uninstalling hyprland-languages ==="

# Remove binaries
rm -f "${HOME}/.local/bin/hyprland-languages"
if [[ -w "/usr/local/bin/hyprland-languages" ]]; then
    rm -f "/usr/local/bin/hyprland-languages"
elif [[ -f "/usr/local/bin/hyprland-languages" ]]; then
    sudo rm -f "/usr/local/bin/hyprland-languages"
fi

# Remove python site-packages links
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "3.12")
rm -f "${HOME}/.local/lib/python${PY_VER}/site-packages/hyprland_languages"

# Remove cache
rm -rf "${HOME}/.cache/hyprland-languages"

echo "hyprland-languages has been uninstalled."
