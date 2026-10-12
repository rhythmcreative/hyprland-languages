"""
Locale management module for hyprland-languages.
Parses /etc/locale.gen, provides sub-millisecond fuzzy search,
locale generation (locale-gen), and user/system locale configuration.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .data import COUNTRIES, LANGUAGES, get_flag_emoji


def normalize_text(text: str) -> str:
    """Normalize text to lowercase ASCII without diacritics for fast fuzzy matching."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


@dataclass
class LocaleInfo:
    code: str
    charset: str
    lang: str
    country: str
    lang_name: str
    lang_en: str
    lang_es: str
    country_name: str
    country_es: str
    flag: str
    generated: bool
    active: bool
    display_name: str
    display_name_es: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def get_active_locale() -> str:
    """Get the currently active user locale."""
    # Check user environment.d file first
    env_file = Path.home() / ".config" / "environment.d" / "10-locale.conf"
    if env_file.exists():
        try:
            content = env_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("LANG="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val
        except Exception:
            pass

    # Fallback to os.environ LANG
    val = os.environ.get("LANG", "")
    if val:
        return val

    # Fallback to localectl
    try:
        res = subprocess.run(["localectl", "status"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "System Locale: LANG=" in line or "LANG=" in line:
                    match = re.search(r"LANG=([^\s]+)", line)
                    if match:
                        return match.group(1)
    except Exception:
        pass

    return "en_US.UTF-8"


def get_generated_locales() -> Set[str]:
    """Retrieve all locales currently compiled into the locale archive via `locale -a`."""
    generated: Set[str] = set()
    try:
        res = subprocess.run(["locale", "-a"], capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                code = line.strip()
                if not code:
                    continue
                generated.add(code)
                # Normalize variations: es_ES.utf8 == es_ES.UTF-8
                if ".utf8" in code.lower():
                    clean_code = re.sub(r"\.utf8$", ".UTF-8", code, flags=re.IGNORECASE)
                    generated.add(clean_code)
    except Exception:
        pass
    return generated


def parse_locale_gen_line(raw_line: str, generated_set: Set[str], current_active: str) -> Optional[LocaleInfo]:
    """Parse a single line from /etc/locale.gen."""
    line = raw_line.strip()
    if not line:
        return None

    # Check if uncommented in file
    is_uncommented = not line.startswith("#")
    if line.startswith("#"):
        line = line.lstrip("#").strip()

    # Must contain at least locale and charset
    parts = line.split()
    if len(parts) < 2:
        return None

    code = parts[0]
    charset = parts[1]

    # Only process standard locales (skip comments or malformed lines)
    if not re.match(r"^[a-zA-Z]{2,3}(_[a-zA-Z0-9]+)?(\.[a-zA-Z0-9-]+)?(@[a-zA-Z0-9]+)?$", code):
        return None

    # Extract language, country, variant
    # e.g. es_ES.UTF-8 -> lang=es, country=ES
    # ca_ES@valencia.UTF-8 -> lang=ca, country=ES
    base = code.split(".")[0] if "." in code else code
    base = base.split("@")[0] if "@" in base else base

    lang = ""
    country = ""
    if "_" in base:
        p = base.split("_", 1)
        lang = p[0].lower()
        country = p[1].upper()
    else:
        lang = base.lower()
        country = ""

    # Flag
    flag = get_flag_emoji(country)

    # Language names
    lang_info = LANGUAGES.get(lang)
    if lang_info:
        lang_native, lang_en, lang_es = lang_info
    else:
        lang_native = lang
        lang_en = lang.capitalize()
        lang_es = lang.capitalize()

    # Country names
    country_info = COUNTRIES.get(country)
    if country_info:
        country_en, country_es = country_info
    else:
        country_en = country
        country_es = country

    # Generated status
    code_norm = re.sub(r"\.utf8$", ".UTF-8", code, flags=re.IGNORECASE)
    is_gen = is_uncommented or (code in generated_set) or (code_norm in generated_set)

    # Active status
    is_active = (current_active == code) or (current_active == code_norm) or (
        current_active.lower().replace("-", "").replace("_", "") == code.lower().replace("-", "").replace("_", "")
    )

    if country_en and country_en != country:
        display_name = f"{lang_en} ({country_en}) - {code}"
    else:
        display_name = f"{lang_en} - {code}"

    if country_es and country_es != country:
        display_name_es = f"{lang_es} ({country_es}) - {code}"
    else:
        display_name_es = f"{lang_es} - {code}"

    return LocaleInfo(
        code=code,
        charset=charset,
        lang=lang,
        country=country,
        lang_name=lang_native,
        lang_en=lang_en,
        lang_es=lang_es,
        country_name=country_en,
        country_es=country_es,
        flag=flag,
        generated=is_gen,
        active=is_active,
        display_name=display_name,
        display_name_es=display_name_es,
    )


LOCALE_CANDIDATE_PATHS = [
    Path("/etc/locale.gen"),
    Path("/usr/share/i18n/SUPPORTED"),
    Path("/etc/default/libc-locales"),
    Path("/run/current-system/sw/share/i18n/SUPPORTED"),
]


def load_all_locales(locale_gen_path: Optional[str] = None) -> List[LocaleInfo]:
    """
    Parse all locales available in the system across distributions:
    Arch/Debian/Ubuntu (/etc/locale.gen), Fedora/openSUSE (/usr/share/i18n/SUPPORTED, localectl),
    Void (/etc/default/libc-locales), NixOS (/run/current-system/sw/share/i18n/SUPPORTED).
    """
    generated_set = get_generated_locales()
    current_active = get_active_locale()

    path: Optional[Path] = None
    if locale_gen_path:
        p = Path(locale_gen_path)
        if p.exists():
            path = p

    if path is None:
        for candidate in LOCALE_CANDIDATE_PATHS:
            if candidate.exists():
                path = candidate
                break

    seen_codes: Set[str] = set()
    locales: List[LocaleInfo] = []

    if path and path.exists():
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            for raw_line in content.splitlines():
                info = parse_locale_gen_line(raw_line, generated_set, current_active)
                if info and info.code not in seen_codes:
                    seen_codes.add(info.code)
                    locales.append(info)
        except Exception:
            pass

    # Fallback to localectl list-locales if file was missing or empty (e.g. Fedora / RHEL)
    if not locales and shutil.which("localectl"):
        try:
            res = subprocess.run(["localectl", "list-locales"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    code = line.strip()
                    if not code:
                        continue
                    charset = "UTF-8" if "utf" in code.lower() else "ISO-8859-1"
                    info = parse_locale_gen_line(f"{code} {charset}", generated_set, current_active)
                    if info and info.code not in seen_codes:
                        seen_codes.add(info.code)
                        locales.append(info)
        except Exception:
            pass

    # Fallback to generated locales
    if not locales:
        for code in sorted(generated_set):
            info = parse_locale_gen_line(f"{code} UTF-8", generated_set, current_active)
            if info and info.code not in seen_codes:
                seen_codes.add(info.code)
                locales.append(info)

    # Ensure current_active is present if generated
    if current_active and current_active not in seen_codes:
        active_info = parse_locale_gen_line(f"{current_active} UTF-8", generated_set, current_active)
        if active_info:
            active_info.active = True
            locales.insert(0, active_info)

    return locales


def score_locale_match(query_norm: str, loc: LocaleInfo) -> int:
    """Calculate a relevance score for a search query against a locale."""
    code_norm = normalize_text(loc.code)
    lang_norm = normalize_text(loc.lang)
    country_norm = normalize_text(loc.country)
    lang_name_norm = normalize_text(loc.lang_name)
    lang_en_norm = normalize_text(loc.lang_en)
    lang_es_norm = normalize_text(loc.lang_es)
    country_en_norm = normalize_text(loc.country_name)
    country_es_norm = normalize_text(loc.country_es)

    score = 0

    # Exact matches
    if query_norm == code_norm or query_norm == lang_norm:
        score += 200
    elif query_norm in (lang_name_norm, lang_en_norm, lang_es_norm):
        score += 160
    elif query_norm == country_norm:
        score += 120
    elif query_norm in (country_en_norm, country_es_norm):
        score += 100

    # Prefix matches
    elif code_norm.startswith(query_norm) or lang_norm.startswith(query_norm):
        score += 95
    elif lang_name_norm.startswith(query_norm) or lang_es_norm.startswith(query_norm) or lang_en_norm.startswith(query_norm):
        score += 85
    elif country_norm.startswith(query_norm):
        score += 75
    elif country_en_norm.startswith(query_norm) or country_es_norm.startswith(query_norm):
        score += 70

    # Word boundary match (e.g. searching "espanol" matches "Espanol (Espana)")
    elif any(part.startswith(query_norm) for part in lang_name_norm.split()):
        score += 65
    elif any(part.startswith(query_norm) for part in lang_es_norm.split() + lang_en_norm.split()):
        score += 60
    elif any(part.startswith(query_norm) for part in country_es_norm.split() + country_en_norm.split()):
        score += 55

    # Substring matches
    elif query_norm in code_norm:
        score += 40
    elif query_norm in lang_name_norm or query_norm in lang_es_norm or query_norm in lang_en_norm:
        score += 35
    elif query_norm in country_es_norm or query_norm in country_en_norm:
        score += 30
    else:
        return 0

    # Boost generated & UTF-8 locales
    if loc.active:
        score += 30
    if loc.generated:
        score += 20
    if "utf-8" in loc.charset.lower():
        score += 15

    return score


def search_locales(
    query: str,
    locales: Optional[List[LocaleInfo]] = None,
    limit: int = 50,
    only_generated: bool = False,
    only_utf8: bool = True,
) -> List[LocaleInfo]:
    """Search locales with high-speed fuzzy matching and ranked scoring."""
    if locales is None:
        locales = load_all_locales()

    query_clean = query.strip()
    query_norm = normalize_text(query_clean)

    filtered = locales
    if only_utf8:
        filtered = [l for l in filtered if "utf-8" in l.charset.lower()]
    if only_generated:
        filtered = [l for l in filtered if l.generated]

    if not query_norm:
        # Return generated first, then active, then alphabetical
        return sorted(
            filtered,
            key=lambda l: (not l.active, not l.generated, l.lang_es, l.country_es, l.code),
        )[:limit]

    scored: List[tuple[int, LocaleInfo]] = []
    for loc in filtered:
        score = score_locale_match(query_norm, loc)
        if score > 0:
            scored.append((score, loc))

    scored.sort(
        key=lambda item: (-item[0], not item[1].active, not item[1].generated, item[1].code)
    )

    return [item[1] for item in scored[:limit]]


def generate_locale(locale_code: str, locale_gen_path: Optional[str] = None) -> tuple[bool, str]:
    """
    Generate requested locale across Linux distributions:
    - Arch / Debian / Ubuntu / Mint: uncomments in /etc/locale.gen and runs locale-gen
    - Fedora / RHEL / CentOS / openSUSE: compiles via `localedef -i <base> -f UTF-8 <locale>`
    - Void Linux: uncomments in /etc/default/libc-locales and runs xbps-reconfigure -f glibc-locales
    - Fallback: localectl
    """
    clean_code = re.sub(r"\.utf8$", ".UTF-8", locale_code, flags=re.IGNORECASE)
    gen_locales = get_generated_locales()
    if clean_code in gen_locales:
        return True, f"Locale {locale_code} is already generated."

    is_root = os.geteuid() == 0
    cmd_prefix = [] if is_root else ["sudo"]

    # 1. Arch Linux / Debian / Ubuntu (/etc/locale.gen and locale-gen)
    base_code = clean_code.split(".")[0].split("@")[0]
    variants = [re.escape(clean_code)]
    if base_code != clean_code:
        variants.append(re.escape(base_code))
    pat = "|".join(variants)

    target_file = Path(locale_gen_path or "/etc/locale.gen")
    if target_file.exists() and shutil.which("locale-gen"):
        sed_cmd = f"sed -i -E 's/^[#[:space:]]*({pat})([[:space:]]+.*)/\\1\\2/' {target_file}"
        full_script = f"{sed_cmd} && locale-gen"
        res = subprocess.run(cmd_prefix + ["bash", "-c", full_script], capture_output=True, text=True)
        if res.returncode == 0:
            return True, f"Locale {locale_code} successfully generated.\n{res.stdout}"

    # 2. Void Linux (/etc/default/libc-locales and xbps-reconfigure)
    void_file = Path("/etc/default/libc-locales")
    if void_file.exists() and shutil.which("xbps-reconfigure"):
        sed_cmd = f"sed -i -E 's/^[#[:space:]]*({pat})([[:space:]]+.*)/\\1\\2/' {void_file}"
        full_script = f"{sed_cmd} && xbps-reconfigure -f glibc-locales"
        res = subprocess.run(cmd_prefix + ["bash", "-c", full_script], capture_output=True, text=True)
        if res.returncode == 0:
            return True, f"Locale {locale_code} successfully generated via xbps-reconfigure."

    # 3. Fedora, RHEL, CentOS, openSUSE (localedef)
    if shutil.which("localedef"):
        base_name = clean_code.split(".")[0].split("@")[0]
        charset = "UTF-8" if "utf" in clean_code.lower() else "ISO-8859-1"
        cmd = cmd_prefix + ["localedef", "-i", base_name, "-f", charset, clean_code]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return True, f"Locale {locale_code} successfully generated via localedef."

    # 4. Fallback: localectl
    if shutil.which("localectl"):
        cmd = cmd_prefix + ["localectl", "set-locale", f"LANG={clean_code}"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return True, f"Locale {locale_code} configured via localectl."

    return False, f"Failed to generate locale {locale_code} on this distribution."


def set_user_locale(locale_code: str) -> tuple[bool, str]:
    """
    Set user locale across distributions:
    - ~/.config/environment.d/10-locale.conf (standard systemd XDG specification)
    - ~/.profile (login shell fallback)
    - systemctl --user import-environment
    """
    clean_code = re.sub(r"\.utf8$", ".UTF-8", locale_code, flags=re.IGNORECASE)
    env_dir = Path.home() / ".config" / "environment.d"
    env_file = env_dir / "10-locale.conf"

    try:
        env_dir.mkdir(parents=True, exist_ok=True)
        conf_content = (
            "# Generated by hyprland-languages\n"
            f"LANG={clean_code}\n"
            f"LC_ALL={clean_code}\n"
        )
        env_file.write_text(conf_content, encoding="utf-8")

        # Update ~/.profile fallback
        try:
            profile_file = Path.home() / ".profile"
            content = profile_file.read_text(encoding="utf-8") if profile_file.exists() else ""
            lines = [l for l in content.splitlines() if not l.startswith("export LANG=") and not l.startswith("export LC_ALL=")]
            lines.append(f'export LANG="{clean_code}"')
            lines.append(f'export LC_ALL="{clean_code}"')
            profile_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception:
            pass

        # Also update systemd user session if active
        if shutil.which("systemctl"):
            subprocess.run(
                ["systemctl", "--user", "import-environment", "LANG", "LC_ALL"],
                capture_output=True,
                text=True,
                timeout=2,
            )

        return True, f"User locale successfully set to {clean_code} in {env_file}"
    except Exception as e:
        return False, f"Failed to set user locale: {e}"


def set_system_locale(locale_code: str) -> tuple[bool, str]:
    """
    Set system-wide locale across distributions:
    - localectl set-locale (Arch, Fedora, Debian, Ubuntu, openSUSE)
    - /etc/locale.conf (Arch, Fedora, openSUSE, Void, Alpine)
    - /etc/default/locale (Debian, Ubuntu, Mint)
    """
    clean_code = re.sub(r"\.utf8$", ".UTF-8", locale_code, flags=re.IGNORECASE)
    is_root = os.geteuid() == 0
    cmd_prefix = [] if is_root else ["sudo"]

    # 1. localectl
    if shutil.which("localectl"):
        res = subprocess.run(cmd_prefix + ["localectl", "set-locale", f"LANG={clean_code}"], capture_output=True, text=True)
        if res.returncode == 0:
            return True, f"System locale successfully set to {clean_code} (localectl)"

    # 2. /etc/locale.conf or /etc/default/locale
    target_sys_conf = Path("/etc/default/locale") if Path("/etc/default/locale").exists() else Path("/etc/locale.conf")
    script = f"echo 'LANG={clean_code}' > {target_sys_conf}"
    res = subprocess.run(cmd_prefix + ["bash", "-c", script], capture_output=True, text=True)
    if res.returncode == 0:
        return True, f"System locale successfully set to {clean_code} in {target_sys_conf}"

    return False, f"Failed to set system locale: {res.stderr}"
