"""
Keyboard layout management module for hyprland-languages.
Parses /usr/share/X11/xkb/rules/base.lst, queries Hyprland devices and options,
handles multi-keyboard synchronous layout switching, cycle next/prev, add, and remove.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .data import COUNTRIES, LANGUAGES, get_flag_emoji
from .locales import normalize_text

LAYOUT_FLAG_OVERRIDES = {
    "us": "🇺🇸",
    "en": "🇺🇸",
    "gb": "🇬🇧",
    "uk": "🇬🇧",
    "es": "🇪🇸",
    "latam": "🌎",
    "de": "🇩🇪",
    "fr": "🇫🇷",
    "it": "🇮🇹",
    "pt": "🇵🇹",
    "br": "🇧🇷",
    "ru": "🇷🇺",
    "cn": "🇨🇳",
    "jp": "🇯🇵",
    "kr": "🇰🇷",
    "ara": "🇸🇦",
    "ar": "🇸🇦",
    "dz": "🇩🇿",
    "ma": "🇲🇦",
    "eg": "🇪🇬",
    "iq": "🇮🇶",
    "sy": "🇸🇾",
    "il": "🇮🇱",
    "in": "🇮🇳",
    "ca": "🇨🇦",
    "mx": "🇲🇽",
    "ch": "🇨🇭",
    "at": "🇦🇹",
    "be": "🇧🇪",
    "nl": "🇳🇱",
    "se": "🇸🇪",
    "no": "🇳🇴",
    "dk": "🇩🇰",
    "fi": "🇫🇮",
    "pl": "🇵🇱",
    "cz": "🇨🇿",
    "sk": "🇸🇰",
    "hu": "🇭🇺",
    "ro": "🇷🇴",
    "bg": "🇧🇬",
    "gr": "🇬🇷",
    "tr": "🇹🇷",
    "ua": "🇺🇦",
    "by": "🇧🇾",
    "kz": "🇰🇿",
    "ge": "🇬🇪",
    "am": "🇦🇲",
    "az": "🇦🇿",
    "th": "🇹🇭",
    "vn": "🇻🇳",
    "id": "🇮🇩",
    "ph": "🇵🇭",
    "ie": "🇮🇪",
    "is": "🇮🇸",
    "ee": "🇪🇪",
    "lv": "🇱🇻",
    "lt": "🇱🇹",
    "hr": "🇭🇷",
    "rs": "🇷🇸",
    "ba": "🇧🇦",
    "si": "🇸🇮",
    "mk": "🇲🇰",
    "al": "🇦🇱",
    "epo": "🟢",
    "brai": "⠃",
    "custom": "⌨️",
}


def get_layout_flag(code: str) -> str:
    """Get the flag emoji for an XKB layout code."""
    c = code.lower()
    if c in LAYOUT_FLAG_OVERRIDES:
        return LAYOUT_FLAG_OVERRIDES[c]
    if len(c) == 2:
        return get_flag_emoji(c)
    return "🌐"


@dataclass
class LayoutVariant:
    name: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LayoutInfo:
    code: str
    description: str
    flag: str
    variants: List[LayoutVariant] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "description": self.description,
            "flag": self.flag,
            "variants": [v.to_dict() for v in self.variants],
        }


XKB_CANDIDATE_PATHS = [
    Path("/usr/share/X11/xkb/rules/base.lst"),
    Path("/usr/share/X11/xkb/rules/evdev.lst"),
    Path("/run/current-system/sw/share/X11/xkb/rules/base.lst"),
    Path("/run/current-system/sw/share/X11/xkb/rules/evdev.lst"),
    Path("/etc/X11/xkb/rules/base.lst"),
]


def load_all_layouts(base_lst_path: Optional[str] = None) -> List[LayoutInfo]:
    """Parse XKB rules (base.lst / evdev.lst) to load all available layouts across distributions."""
    path: Optional[Path] = None
    if base_lst_path:
        p = Path(base_lst_path)
        if p.exists():
            path = p

    if path is None:
        for candidate in XKB_CANDIDATE_PATHS:
            if candidate.exists():
                path = candidate
                break

    if path is None or not path.exists():
        return []

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    layouts: Dict[str, LayoutInfo] = {}
    current_section = None

    for line in content.splitlines():
        line_strip = line.strip()
        if not line_strip:
            continue

        if line_strip.startswith("!"):
            current_section = line_strip.split()[1] if len(line_strip.split()) > 1 else None
            continue

        if current_section == "layout":
            parts = line_strip.split(None, 1)
            if len(parts) >= 2:
                code = parts[0].strip()
                desc = parts[1].strip()
                flag = get_layout_flag(code)
                layouts[code] = LayoutInfo(code=code, description=desc, flag=flag, variants=[])
        elif current_section == "variant":
            parts = line_strip.split(None, 1)
            if len(parts) >= 2:
                var_name = parts[0].strip()
                rest = parts[1].strip()
                if ":" in rest:
                    layout_code, var_desc = rest.split(":", 1)
                    layout_code = layout_code.strip()
                    var_desc = var_desc.strip()
                    if layout_code in layouts:
                        layouts[layout_code].variants.append(
                            LayoutVariant(name=var_name, description=var_desc)
                        )

    return list(layouts.values())


def search_layouts(
    query: str, layouts: Optional[List[LayoutInfo]] = None, limit: int = 50
) -> List[LayoutInfo]:
    """Search layouts by code, description, or variant description."""
    if layouts is None:
        layouts = load_all_layouts()

    query_norm = normalize_text(query)
    if not query_norm:
        # Sort common layouts first, then alphabetical
        priority_codes = {"us": 0, "es": 1, "latam": 2, "de": 3, "fr": 4, "it": 5, "pt": 6, "br": 7, "ru": 8, "jp": 9}
        return sorted(layouts, key=lambda l: (priority_codes.get(l.code, 99), l.description))[:limit]

    scored: List[Tuple[int, LayoutInfo]] = []
    for l in layouts:
        code_norm = normalize_text(l.code)
        desc_norm = normalize_text(l.description)
        score = 0

        if query_norm == code_norm:
            score += 200
        elif query_norm == desc_norm:
            score += 150
        elif code_norm.startswith(query_norm):
            score += 110
        elif desc_norm.startswith(query_norm):
            score += 90
        elif any(part.startswith(query_norm) for part in desc_norm.split()):
            score += 75
        elif query_norm in code_norm:
            score += 60
        elif query_norm in desc_norm:
            score += 50
        elif any(query_norm in normalize_text(v.description) for v in l.variants):
            score += 30

        if score > 0:
            scored.append((score, l))

    scored.sort(key=lambda item: (-item[0], item[1].description))
    return [item[1] for item in scored[:limit]]


# Hyprland IPC & Device queries


def get_hyprctl_devices() -> Dict[str, Any]:
    """Retrieve connected devices via `hyprctl devices -j`."""
    try:
        res = subprocess.run(["hyprctl", "devices", "-j"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            return json.loads(res.stdout)
    except Exception:
        pass
    return {}


def get_hyprctl_option(option_name: str) -> Optional[str]:
    """Retrieve an option string from `hyprctl getoption <name> -j`."""
    try:
        res = subprocess.run(
            ["hyprctl", "getoption", option_name, "-j"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0:
            data = json.loads(res.stdout)
            return data.get("str")
    except Exception:
        pass
    return None


def get_primary_keyboard(devices: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Determine the primary physical keyboard."""
    if devices is None:
        devices = get_hyprctl_devices()

    keyboards = devices.get("keyboards", [])
    if not keyboards:
        return None

    # Filter out virtual/media control handles
    real_kbs = [
        k for k in keyboards
        if not any(
            x in k.get("name", "").lower()
            for x in ["consumer", "system-control", "video-bus", "button", "stream-deck"]
        )
    ]
    if not real_kbs:
        real_kbs = keyboards

    # Priority 1: explicitly marked as main
    main_kb = next((k for k in real_kbs if k.get("main")), None)
    if main_kb:
        return main_kb

    # Priority 2: Wooting, Asus, AT translated keyboard
    for pattern in ["wooting", "asus", "at-translated-set-2"]:
        match = next((k for k in real_kbs if pattern in k.get("name", "").lower()), None)
        if match:
            return match

    # Priority 3: first keyboard with layout set
    with_layout = next((k for k in real_kbs if k.get("layout")), None)
    return with_layout or real_kbs[0]


def get_configured_layouts() -> List[str]:
    """Get the list of configured layout codes (e.g. ['us', 'es'])."""
    opt = get_hyprctl_option("input:kb_layout")
    if opt:
        return [c.strip().lower() for c in opt.split(",") if c.strip()]

    # Fallback to primary keyboard
    primary = get_primary_keyboard()
    if primary and primary.get("layout"):
        return [c.strip().lower() for c in primary["layout"].split(",") if c.strip()]

    return ["us"]


def get_active_layout_info() -> Dict[str, Any]:
    """Get the currently active keyboard layout info."""
    devices = get_hyprctl_devices()
    primary = get_primary_keyboard(devices)
    configured = get_configured_layouts()

    active_idx = primary.get("active_layout_index", 0) if primary else 0
    active_keymap = primary.get("active_keymap", "English (US)") if primary else "English (US)"

    active_code = "us"
    if 0 <= active_idx < len(configured):
        active_code = configured[active_idx]
    else:
        # Try inferring from active_keymap
        km_lower = active_keymap.lower()
        if "spanish" in km_lower:
            active_code = "es"
        elif "german" in km_lower:
            active_code = "de"
        elif "french" in km_lower:
            active_code = "fr"
        elif "russian" in km_lower:
            active_code = "ru"

    flag = get_layout_flag(active_code)

    return {
        "code": active_code,
        "name": active_keymap,
        "index": active_idx,
        "flag": flag,
        "configured_layouts": configured,
    }


def sync_all_keyboards(index_or_action: int | str) -> bool:
    """
    Synchronously switch all keyboards to the specified index or action ('next'/'prev')
    ensuring multi-device consistency (e.g. Wooting + laptop internal keyboard).
    """
    devs = get_hyprctl_devices()
    keyboards = devs.get("keyboards", [])
    if not keyboards:
        return False

    success = True
    for kb in keyboards:
        kb_name = kb.get("name")
        if not kb_name:
            continue
        cmd = ["hyprctl", "switchxkblayout", kb_name, str(index_or_action)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=1)
        if res.returncode != 0:
            success = False

    return success


def cycle_layout(direction: int = 1) -> Dict[str, Any]:
    """Cycle to next (direction=+1) or previous (direction=-1) configured layout."""
    configured = get_configured_layouts()
    if not configured:
        return get_active_layout_info()

    active_info = get_active_layout_info()
    current_idx = active_info["index"]

    next_idx = (current_idx + direction) % len(configured)
    sync_all_keyboards(next_idx)

    return get_active_layout_info()


def switch_layout(target: int | str) -> Dict[str, Any]:
    """Switch to a layout by index or code."""
    configured = get_configured_layouts()

    target_idx = -1
    if isinstance(target, int) or (isinstance(target, str) and target.isdigit()):
        target_idx = int(target)
    else:
        # Search by code
        target_code = str(target).strip().lower()
        for idx, code in enumerate(configured):
            if code == target_code:
                target_idx = idx
                break

    if target_idx != -1 and 0 <= target_idx < len(configured):
        sync_all_keyboards(target_idx)
    else:
        # If code not currently in configured layouts, add it and switch
        target_code = str(target).strip().lower()
        add_layout(target_code)
        configured_new = get_configured_layouts()
        try:
            new_idx = configured_new.index(target_code)
            sync_all_keyboards(new_idx)
        except ValueError:
            pass

    return get_active_layout_info()


def persist_hyprland_config(new_layouts_str: str) -> None:
    """Persist new layouts string to hyprland.lua and hyprland.conf files."""
    config_paths = [
        Path.home() / ".config/hypr/hyprland.lua",
        Path.home() / ".config/hypr/hyprland.conf",
        Path.home() / "hyprland/.config/hypr/hyprland.lua",
        Path.home() / "hyprland/.config/hypr/hyprland.conf",
    ]

    for p in config_paths:
        if not p.exists():
            continue
        try:
            content = p.read_text(encoding="utf-8")
            if p.suffix == ".lua":
                content = re.sub(r'kb_layout\s*=\s*"[^"]*"', f'kb_layout = "{new_layouts_str}"', content)
            else:
                content = re.sub(r'kb_layout\s*=\s*[^\n]*', f'kb_layout = {new_layouts_str}', content)
            p.write_text(content, encoding="utf-8")
        except Exception:
            pass


def add_layout(layout_code: str) -> bool:
    """Add a layout code to the active Hyprland configuration."""
    code = layout_code.strip().lower()
    configured = get_configured_layouts()
    if code in configured:
        return True

    configured.append(code)
    new_str = ",".join(configured)
    persist_hyprland_config(new_str)

    # Reload hyprland
    subprocess.run(["hyprctl", "reload"], capture_output=True, timeout=2)
    return True


def remove_layout(layout_code: str) -> bool:
    """Remove a layout code from the active Hyprland configuration."""
    code = layout_code.strip().lower()
    configured = get_configured_layouts()
    if code not in configured:
        return True

    if len(configured) <= 1:
        # Keep at least one layout
        return False

    configured.remove(code)
    new_str = ",".join(configured)
    persist_hyprland_config(new_str)

    # Reload hyprland
    subprocess.run(["hyprctl", "reload"], capture_output=True, timeout=2)
    return True
