"""
Fast disk caching layer for hyprland-languages.
Stores parsed locales and layouts in ~/.cache/hyprland-languages/cache.json
with mtime invalidation for instant sub-millisecond startups.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .layouts import LayoutInfo, LayoutVariant, load_all_layouts
from .locales import LocaleInfo, load_all_locales

CACHE_DIR = Path.home() / ".cache" / "hyprland-languages"
CACHE_FILE = CACHE_DIR / "cache.json"

LOCALE_GEN_PATH = Path("/etc/locale.gen")
BASE_LST_PATH = Path("/usr/share/X11/xkb/rules/base.lst")


def get_source_mtimes() -> Dict[str, float]:
    """Get modification timestamps of system source files."""
    mtimes = {}
    if LOCALE_GEN_PATH.exists():
        mtimes["locale_gen"] = LOCALE_GEN_PATH.stat().st_mtime
    if BASE_LST_PATH.exists():
        mtimes["base_lst"] = BASE_LST_PATH.stat().st_mtime
    return mtimes


def load_cached_data() -> Optional[Dict[str, Any]]:
    """Load cached data if valid and fresh."""
    if not CACHE_FILE.exists():
        return None

    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        cached_mtimes = data.get("mtimes", {})
        current_mtimes = get_source_mtimes()

        # Check if source files have changed
        for k, v in current_mtimes.items():
            if cached_mtimes.get(k) != v:
                return None

        return data
    except Exception:
        return None


def save_cached_data(locales: List[LocaleInfo], layouts: List[LayoutInfo]) -> None:
    """Save parsed locales and layouts to cache."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": time.time(),
            "mtimes": get_source_mtimes(),
            "locales": [l.to_dict() for l in locales],
            "layouts": [l.to_dict() for l in layouts],
        }
        CACHE_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def get_cached_locales_and_layouts(force_refresh: bool = False) -> Tuple[List[LocaleInfo], List[LayoutInfo]]:
    """Retrieve locales and layouts, using cache if available."""
    if not force_refresh:
        cached = load_cached_data()
        if cached:
            try:
                locales = [LocaleInfo(**item) for item in cached["locales"]]
                layouts = [
                    LayoutInfo(
                        code=item["code"],
                        description=item["description"],
                        flag=item["flag"],
                        variants=[LayoutVariant(**v) for v in item.get("variants", [])],
                    )
                    for item in cached["layouts"]
                ]
                return locales, layouts
            except Exception:
                pass

    # Rebuild from scratch
    locales = load_all_locales()
    layouts = load_all_layouts()
    save_cached_data(locales, layouts)
    return locales, layouts
