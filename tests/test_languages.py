"""
Unit tests for hyprland-languages.
"""

import json
import subprocess
import unittest
from pathlib import Path

from hyprland_languages.data import get_flag_emoji
from hyprland_languages.layouts import LayoutInfo, get_layout_flag, load_all_layouts, search_layouts
from hyprland_languages.locales import (
    LocaleInfo,
    load_all_locales,
    normalize_text,
    parse_locale_gen_line,
    score_locale_match,
    search_locales,
)


class TestFlagEmoji(unittest.TestCase):
    def test_flag_emoji_conversion(self):
        self.assertEqual(get_flag_emoji("ES"), "🇪🇸")
        self.assertEqual(get_flag_emoji("US"), "🇺🇸")
        self.assertEqual(get_flag_emoji("FR"), "🇫🇷")
        self.assertEqual(get_flag_emoji("DE"), "🇩🇪")
        self.assertEqual(get_flag_emoji("JP"), "🇯🇵")

    def test_flag_emoji_invalid(self):
        self.assertEqual(get_flag_emoji(""), "🌐")
        self.assertEqual(get_flag_emoji("XYZ"), "🌐")

    def test_layout_flag_overrides(self):
        self.assertEqual(get_layout_flag("latam"), "🌎")
        self.assertEqual(get_layout_flag("ara"), "🇸🇦")
        self.assertEqual(get_layout_flag("us"), "🇺🇸")


class TestNormalization(unittest.TestCase):
    def test_normalize_accents(self):
        self.assertEqual(normalize_text("Español"), "espanol")
        self.assertEqual(normalize_text("Čeština"), "cestina")
        self.assertEqual(normalize_text("Français"), "francais")
        self.assertEqual(normalize_text("Österreich"), "osterreich")


class TestLocaleParsing(unittest.TestCase):
    def test_parse_locale_gen_line(self):
        gen_set = {"es_ES.UTF-8"}
        active = "es_ES.UTF-8"

        # Uncommented
        info = parse_locale_gen_line("es_ES.UTF-8 UTF-8", gen_set, active)
        self.assertIsNotNone(info)
        self.assertEqual(info.code, "es_ES.UTF-8")
        self.assertEqual(info.lang, "es")
        self.assertEqual(info.country, "ES")
        self.assertEqual(info.flag, "🇪🇸")
        self.assertTrue(info.generated)
        self.assertTrue(info.active)

        # Commented
        info_commented = parse_locale_gen_line("#fr_FR.UTF-8 UTF-8", set(), active)
        self.assertIsNotNone(info_commented)
        self.assertEqual(info_commented.code, "fr_FR.UTF-8")
        self.assertFalse(info_commented.generated)
        self.assertFalse(info_commented.active)

    def test_locale_search(self):
        locales = load_all_locales()
        self.assertGreater(len(locales), 300)

        # Search 'espanol'
        results = search_locales("espanol", locales)
        self.assertTrue(any(l.code == "es_ES.UTF-8" for l in results))

        # Search 'japanese'
        jp_results = search_locales("japanese", locales)
        self.assertTrue(any("ja_JP" in l.code for l in jp_results))


class TestLayoutParsing(unittest.TestCase):
    def test_load_all_layouts(self):
        layouts = load_all_layouts()
        self.assertGreater(len(layouts), 50)
        codes = {l.code for l in layouts}
        self.assertIn("us", codes)
        self.assertIn("es", codes)
        self.assertIn("de", codes)

    def test_layout_search(self):
        layouts = load_all_layouts()
        results = search_layouts("spanish", layouts)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].code, "es")


class TestCLIExecution(unittest.TestCase):
    def setUp(self):
        self.bin_path = Path(__file__).resolve().parent.parent / "bin" / "hyprland-languages"

    def test_cli_version(self):
        res = subprocess.run([str(self.bin_path), "--version"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("hyprland-languages", res.stdout)

    def test_cli_locales_search_json(self):
        res = subprocess.run(
            [str(self.bin_path), "locales", "search", "es", "--limit", "3", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        self.assertIn("code", data[0])

    def test_cli_layouts_search_json(self):
        res = subprocess.run(
            [str(self.bin_path), "layouts", "search", "german", "--limit", "2", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        self.assertEqual(data[0]["code"], "de")

    def test_cli_status_json(self):
        res = subprocess.run(
            [str(self.bin_path), "status", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertIn("locale", data)
        self.assertIn("keyboard", data)


if __name__ == "__main__":
    unittest.main()
