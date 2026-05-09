"""Unit tests for the legacy yt_strip.py helpers."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path


# yt_strip.py imports yt_dlp at module import time, but sanitize_filename does
# not use it. Provide a lightweight stub so these unit tests stay isolated.
sys.modules.setdefault("yt_dlp", types.SimpleNamespace())

_MODULE_PATH = Path(__file__).resolve().parents[1] / "yt_strip.py"
_SPEC = importlib.util.spec_from_file_location("yt_strip_script", _MODULE_PATH)
yt_strip_script = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(yt_strip_script)


class TestSanitizeFilename(unittest.TestCase):
    def test_each_invalid_character_is_removed(self):
        for char in '<>:"/\\|?*':
            with self.subTest(char=char):
                self.assertEqual(yt_strip_script.sanitize_filename(f"a{char}b"), "ab")

    def test_leading_trailing_whitespace_and_dots_are_stripped(self):
        self.assertEqual(yt_strip_script.sanitize_filename("  ...example name...  "), "example name")

    def test_normal_filename_passes_through_unchanged(self):
        self.assertEqual(yt_strip_script.sanitize_filename("My Song - Artist"), "My Song - Artist")

    def test_safe_unicode_characters_are_preserved(self):
        self.assertEqual(yt_strip_script.sanitize_filename("café 日本語"), "café 日本語")

    def test_all_invalid_input_returns_empty_string(self):
        self.assertEqual(yt_strip_script.sanitize_filename("<>?"), "")


if __name__ == "__main__":
    unittest.main()
