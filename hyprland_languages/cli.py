"""
Command-line interface for hyprland-languages.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, List

from . import __version__
from .cache import get_cached_locales_and_layouts, save_cached_data
from .layouts import (
    add_layout,
    cycle_layout,
    get_active_layout_info,
    get_configured_layouts,
    load_all_layouts,
    remove_layout,
    search_layouts,
    switch_layout,
)
from .locales import (
    generate_locale,
    get_active_locale,
    get_generated_locales,
    load_all_locales,
    search_locales,
    set_system_locale,
    set_user_locale,
)

# Terminal ANSI styling helpers
USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ

def color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text

def bold(text: str) -> str:
    return color(text, "1")

def green(text: str) -> str:
    return color(text, "32")

def yellow(text: str) -> str:
    return color(text, "33")

def blue(text: str) -> str:
    return color(text, "34")

def cyan(text: str) -> str:
    return color(text, "36")

def dim(text: str) -> str:
    return color(text, "2")


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_locales_list(args: argparse.Namespace) -> None:
    locales, _ = get_cached_locales_and_layouts(force_refresh=args.refresh)
    if args.generated:
        locales = [l for l in locales if l.generated]

    if args.json:
        print_json([l.to_dict() for l in locales])
        return

    print(bold(f"\nAvailable Locales ({len(locales)} total):"))
    print(dim("-" * 65))
    for l in locales:
        gen_badge = green("✔ generated") if l.generated else dim("○ available")
        act_badge = cyan(" [ACTIVE]") if l.active else ""
        print(f" {l.flag}  {bold(l.code):<22} {l.display_name_es:<32} {gen_badge}{act_badge}")
    print()


def cmd_locales_search(args: argparse.Namespace) -> None:
    locales, _ = get_cached_locales_and_layouts(force_refresh=args.refresh)
    results = search_locales(
        args.query,
        locales=locales,
        limit=args.limit,
        only_generated=args.generated,
        only_utf8=not args.all_charsets,
    )

    if args.json:
        print_json([l.to_dict() for l in results])
        return

    print(bold(f"\nSearch results for '{args.query}' ({len(results)} matches):"))
    print(dim("-" * 65))
    if not results:
        print(yellow("  No matching locales found."))
    else:
        for l in results:
            gen_badge = green("✔ generated") if l.generated else dim("○ available")
            act_badge = cyan(" [ACTIVE]") if l.active else ""
            print(f" {l.flag}  {bold(l.code):<22} {l.display_name_es:<32} {gen_badge}{act_badge}")
    print()


def cmd_locales_current(args: argparse.Namespace) -> None:
    curr = get_active_locale()
    gen = get_generated_locales()
    is_gen = curr in gen or curr.replace(".utf8", ".UTF-8") in gen
    info = {
        "current_locale": curr,
        "is_generated": is_gen,
    }

    if args.json:
        print_json(info)
        return

    status_str = green("Generated") if is_gen else yellow("Not compiled in locale archive")
    print(f"\nCurrent User Locale: {bold(cyan(curr))} ({status_str})")


def cmd_locales_generate(args: argparse.Namespace) -> None:
    success, msg = generate_locale(args.locale)
    if args.json:
        print_json({"success": success, "message": msg, "locale": args.locale})
    else:
        if success:
            print(green(f"✔ {msg}"))
        else:
            print(yellow(f"✘ {msg}"), file=sys.stderr)
            sys.exit(1)


def cmd_locales_set(args: argparse.Namespace) -> None:
    # Ensure locale is generated first
    success_gen, gen_msg = generate_locale(args.locale)
    if not success_gen:
        if args.json:
            print_json({"success": False, "error": f"Failed to generate locale: {gen_msg}"})
        else:
            print(yellow(f"✘ Warning: {gen_msg}"), file=sys.stderr)

    if args.system:
        success, msg = set_system_locale(args.locale)
    else:
        success, msg = set_user_locale(args.locale)

    if args.json:
        print_json({"success": success, "message": msg, "locale": args.locale})
    else:
        if success:
            print(green(f"✔ {msg}"))
        else:
            print(yellow(f"✘ {msg}"), file=sys.stderr)
            sys.exit(1)


def cmd_layouts_list(args: argparse.Namespace) -> None:
    _, layouts = get_cached_locales_and_layouts(force_refresh=args.refresh)
    configured = get_configured_layouts()

    if args.json:
        print_json([l.to_dict() for l in layouts])
        return

    print(bold(f"\nAvailable Keyboard Layouts ({len(layouts)} total):"))
    print(dim("-" * 65))
    for l in layouts:
        is_cfg = cyan(" [CONFIGURED]") if l.code in configured else ""
        print(f" {l.flag}  {bold(l.code):<10} {l.description:<35}{is_cfg}")
    print()


def cmd_layouts_search(args: argparse.Namespace) -> None:
    _, layouts = get_cached_locales_and_layouts(force_refresh=args.refresh)
    results = search_layouts(args.query, layouts=layouts, limit=args.limit)
    configured = get_configured_layouts()

    if args.json:
        print_json([l.to_dict() for l in results])
        return

    print(bold(f"\nSearch results for '{args.query}' ({len(results)} matches):"))
    print(dim("-" * 65))
    if not results:
        print(yellow("  No matching layouts found."))
    else:
        for l in results:
            is_cfg = cyan(" [CONFIGURED]") if l.code in configured else ""
            var_count = f"({len(l.variants)} variants)" if l.variants else ""
            print(f" {l.flag}  {bold(l.code):<8} {l.description:<35} {dim(var_count)}{is_cfg}")
    print()


def cmd_layouts_active(args: argparse.Namespace) -> None:
    info = get_active_layout_info()
    if args.json:
        print_json(info)
        return

    print(bold("\nActive Keyboard Layout:"))
    print(f"  Flag:        {info['flag']}")
    print(f"  Code:        {cyan(info['code'])}")
    print(f"  Name:        {info['name']}")
    print(f"  Index:       {info['index']}")
    print(f"  Configured:  {', '.join(info['configured_layouts'])}\n")


def cmd_layouts_switch(args: argparse.Namespace) -> None:
    res = switch_layout(args.target)
    if args.json:
        print_json(res)
    else:
        print(green(f"✔ Switched keyboard layout to {res['flag']} {res['code']} ({res['name']})"))


def cmd_layouts_next(args: argparse.Namespace) -> None:
    res = cycle_layout(direction=1)
    if args.json:
        print_json(res)
    else:
        print(green(f"✔ Switched to next layout: {res['flag']} {res['code']} ({res['name']})"))


def cmd_layouts_prev(args: argparse.Namespace) -> None:
    res = cycle_layout(direction=-1)
    if args.json:
        print_json(res)
    else:
        print(green(f"✔ Switched to previous layout: {res['flag']} {res['code']} ({res['name']})"))


def cmd_layouts_add(args: argparse.Namespace) -> None:
    success = add_layout(args.code)
    configured = get_configured_layouts()
    if args.json:
        print_json({"success": success, "configured_layouts": configured})
    else:
        if success:
            print(green(f"✔ Added layout '{args.code}'. Active list: {', '.join(configured)}"))
        else:
            print(yellow(f"✘ Failed to add layout '{args.code}'"), file=sys.stderr)


def cmd_layouts_remove(args: argparse.Namespace) -> None:
    success = remove_layout(args.code)
    configured = get_configured_layouts()
    if args.json:
        print_json({"success": success, "configured_layouts": configured})
    else:
        if success:
            print(green(f"✔ Removed layout '{args.code}'. Active list: {', '.join(configured)}"))
        else:
            print(yellow(f"✘ Cannot remove layout '{args.code}' (at least one layout required)"), file=sys.stderr)


def cmd_status(args: argparse.Namespace) -> None:
    active_loc = get_active_locale()
    active_lay = get_active_layout_info()

    data = {
        "locale": {
            "current": active_loc,
            "generated": active_loc in get_generated_locales(),
        },
        "keyboard": active_lay,
    }

    if args.json:
        print_json(data)
        return

    print(bold("\n=== Hyprland Language & Keyboard Status ==="))
    print(f"System/User Locale: {cyan(active_loc)}")
    print(f"Active Keyboard:    {active_lay['flag']} {cyan(active_lay['code'].upper())} ({active_lay['name']})")
    print(f"Configured Layouts: {', '.join(active_lay['configured_layouts'])}")
    print()


def cmd_cache_update(args: argparse.Namespace) -> None:
    locales = load_all_locales()
    layouts = load_all_layouts()
    save_cached_data(locales, layouts)
    if args.json:
        print_json({"locales_count": len(locales), "layouts_count": len(layouts)})
    else:
        print(green(f"✔ Cache updated: {len(locales)} locales, {len(layouts)} layouts indexed."))


def main() -> None:
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    common_parser.add_argument("--refresh", action="store_true", help="Bypass cache and force refresh")

    parser = argparse.ArgumentParser(
        prog="hyprland-languages",
        description="High-performance locale and keyboard layout manager for Hyprland.",
        parents=[common_parser],
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    # Locales parser
    p_locales = subparsers.add_parser("locales", help="Manage system and user locales", parents=[common_parser])
    loc_sub = p_locales.add_subparsers(dest="locales_action", help="Locales action")

    # locales list
    p_loc_list = loc_sub.add_parser("list", help="List all available locales", parents=[common_parser])
    p_loc_list.add_argument("--generated", action="store_true", help="Only show generated locales")

    # locales search
    p_loc_search = loc_sub.add_parser("search", help="Search locales by query", parents=[common_parser])
    p_loc_search.add_argument("query", help="Search term (language, country, code)")
    p_loc_search.add_argument("--limit", type=int, default=50, help="Max results to return")
    p_loc_search.add_argument("--generated", action="store_true", help="Only search generated locales")
    p_loc_search.add_argument("--all-charsets", action="store_true", help="Include non-UTF8 charsets")

    # locales current
    loc_sub.add_parser("current", help="Get current active locale", parents=[common_parser])

    # locales generate
    p_loc_gen = loc_sub.add_parser("generate", help="Generate a locale in /etc/locale.gen", parents=[common_parser])
    p_loc_gen.add_argument("locale", help="Locale code to generate (e.g. es_ES.UTF-8)")

    # locales set
    p_loc_set = loc_sub.add_parser("set", help="Set active locale", parents=[common_parser])
    p_loc_set.add_argument("locale", help="Locale code (e.g. es_ES.UTF-8)")
    p_loc_set.add_argument("--system", action="store_true", help="Set system-wide locale via localectl")

    # Layouts parser
    p_layouts = subparsers.add_parser("layouts", help="Manage keyboard layouts", parents=[common_parser])
    lay_sub = p_layouts.add_subparsers(dest="layouts_action", help="Layouts action")

    # layouts list
    lay_sub.add_parser("list", help="List all available keyboard layouts", parents=[common_parser])

    # layouts search
    p_lay_search = lay_sub.add_parser("search", help="Search layouts by query", parents=[common_parser])
    p_lay_search.add_argument("query", help="Search term (language, country, layout code)")
    p_lay_search.add_argument("--limit", type=int, default=50, help="Max results")

    # layouts active
    lay_sub.add_parser("active", help="Get active keyboard layout", parents=[common_parser])

    # layouts switch
    p_lay_switch = lay_sub.add_parser("switch", help="Switch keyboard layout by index or code", parents=[common_parser])
    p_lay_switch.add_argument("target", help="Index (0, 1, ...) or layout code (es, us, de)")

    # layouts next / prev
    lay_sub.add_parser("next", help="Cycle to next keyboard layout", parents=[common_parser])
    lay_sub.add_parser("prev", help="Cycle to previous keyboard layout", parents=[common_parser])

    # layouts add / remove
    p_lay_add = lay_sub.add_parser("add", help="Add layout to active configuration", parents=[common_parser])
    p_lay_add.add_argument("code", help="Layout code (e.g. de, fr)")

    p_lay_rm = lay_sub.add_parser("remove", help="Remove layout from active configuration", parents=[common_parser])
    p_lay_rm.add_argument("code", help="Layout code (e.g. de, fr)")

    # status parser
    subparsers.add_parser("status", help="Show full language and keyboard layout status", parents=[common_parser])

    # cache parser
    p_cache = subparsers.add_parser("cache", help="Manage cache", parents=[common_parser])
    cache_sub = p_cache.add_subparsers(dest="cache_action")
    cache_sub.add_parser("update", help="Update pre-parsed cache", parents=[common_parser])

    args = parser.parse_args()

    if not args.subcommand:
        cmd_status(args)
        return

    if args.subcommand == "status":
        cmd_status(args)
    elif args.subcommand == "locales":
        if args.locales_action == "list":
            cmd_locales_list(args)
        elif args.locales_action == "search":
            cmd_locales_search(args)
        elif args.locales_action == "current":
            cmd_locales_current(args)
        elif args.locales_action == "generate":
            cmd_locales_generate(args)
        elif args.locales_action == "set":
            cmd_locales_set(args)
        else:
            p_locales.print_help()
    elif args.subcommand == "layouts":
        if args.layouts_action == "list":
            cmd_layouts_list(args)
        elif args.layouts_action == "search":
            cmd_layouts_search(args)
        elif args.layouts_action == "active":
            cmd_layouts_active(args)
        elif args.layouts_action == "switch":
            cmd_layouts_switch(args)
        elif args.layouts_action == "next":
            cmd_layouts_next(args)
        elif args.layouts_action == "prev":
            cmd_layouts_prev(args)
        elif args.layouts_action == "add":
            cmd_layouts_add(args)
        elif args.layouts_action == "remove":
            cmd_layouts_remove(args)
        else:
            p_layouts.print_help()
    elif args.subcommand == "cache":
        if getattr(args, "cache_action", None) == "update":
            cmd_cache_update(args)
        else:
            p_cache.print_help()


if __name__ == "__main__":
    main()
