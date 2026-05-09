"""Unit tests for top-level yt_strip.py helpers."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest


_MODULE_PATH = Path(__file__).resolve().parents[1] / "yt_strip.py"
_SPEC = importlib.util.spec_from_file_location("yt_strip_script", _MODULE_PATH)
yt_strip_script = importlib.util.module_from_spec(_SPEC)

# yt_strip.py imports yt_dlp for downloader functions, but these tests only cover
# sanitize_filename. Keep this unit test independent of optional third-party deps.
_original_yt_dlp = sys.modules.get("yt_dlp")
sys.modules.setdefault("yt_dlp", types.SimpleNamespace())
try:
    _SPEC.loader.exec_module(yt_strip_script)
finally:
    if _original_yt_dlp is None:
        sys.modules.pop("yt_dlp", None)
    else:
        sys.modules["yt_dlp"] = _original_yt_dlp


class TestSanitizeFilename(unittest.TestCase):
    def test_each_invalid_character_is_removed(self):
        for char in '<>:"/\\|?*':
            with self.subTest(char=char):
                self.assertEqual(yt_strip_script.sanitize_filename(f"a{char}b"), "ab")

    def test_strips_leading_and_trailing_whitespace_and_dots(self):
        self.assertEqual(
            yt_strip_script.sanitize_filename("  ...example name...  "), "example name"
        )

    def test_normal_filename_passes_through_unchanged(self):
        self.assertEqual(yt_strip_script.sanitize_filename("My Song - Artist"), "My Song - Artist")

    def test_filesystem_safe_unicode_is_preserved(self):
        self.assertEqual(yt_strip_script.sanitize_filename("café 日本語"), "café 日本語")

    def test_all_invalid_input_returns_empty_string(self):
        self.assertEqual(yt_strip_script.sanitize_filename("<>?"), "")


if __name__ == "__main__":
    unittest.main()
