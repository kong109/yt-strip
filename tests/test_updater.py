"""Tests for yt_strip.updater — yt-dlp self-update mechanism."""

import json
import os
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from yt_strip import updater


# =====================================================================
# get_cache_dir
# =====================================================================

class TestGetCacheDir:
    def test_returns_path_object(self):
        result = updater.get_cache_dir()
        assert isinstance(result, Path)

    def test_ends_with_packages(self):
        result = updater.get_cache_dir()
        assert result.name == "packages"
        assert result.parent.name == "YT Strip"

    @patch("sys.platform", "darwin")
    def test_macos_uses_app_support(self):
        result = updater.get_cache_dir()
        assert "Application Support" in str(result) or "Library" in str(result)

    @patch("sys.platform", "win32")
    def test_windows_uses_appdata(self):
        result = updater.get_cache_dir()
        # Should use APPDATA or fallback
        assert isinstance(result, Path)


# =====================================================================
# get_installed_version
# =====================================================================

class TestGetInstalledVersion:
    def test_returns_string(self):
        ver = updater.get_installed_version()
        assert isinstance(ver, str)
        assert len(ver) > 0

    def test_looks_like_version(self):
        ver = updater.get_installed_version()
        parts = ver.split(".")
        assert len(parts) >= 3
        assert all(p.isdigit() for p in parts)


# =====================================================================
# get_latest_version_info (live PyPI)
# =====================================================================

class TestGetLatestVersionInfo:
    def test_returns_version_and_url(self):
        version, wheel_url = updater.get_latest_version_info()
        assert isinstance(version, str)
        assert len(version) > 0
        parts = version.split(".")
        assert len(parts) >= 3
        assert wheel_url is not None
        assert wheel_url.endswith(".whl")
        assert "yt" in wheel_url.lower()


# =====================================================================
# needs_update
# =====================================================================

class TestNeedsUpdate:
    def test_returns_three_tuple(self):
        result = updater.needs_update()
        assert isinstance(result, tuple)
        assert len(result) == 3
        available, current, latest = result
        assert isinstance(available, bool)
        assert isinstance(current, str)
        assert isinstance(latest, str)

    def test_no_crash_on_network_error(self):
        """Should return (False, ...) on failure, not raise."""
        with patch.object(updater, "get_latest_version_info",
                          side_effect=Exception("network down")):
            available, current, latest = updater.needs_update()
            assert available is False
            assert latest == "unknown"


# =====================================================================
# bootstrap
# =====================================================================

class TestBootstrap:
    def test_no_crash_when_cache_empty(self, tmp_path):
        """bootstrap() should be a no-op when cache dir doesn't exist."""
        with patch.object(updater, "get_cache_dir", return_value=tmp_path / "nope"):
            updater.bootstrap()  # should not raise

    def test_prepends_to_sys_path(self, tmp_path):
        """If cache dir contains yt_dlp/, it should be added to sys.path."""
        (tmp_path / "yt_dlp").mkdir()

        with patch.object(updater, "get_cache_dir", return_value=tmp_path):
            updater.bootstrap()
            assert str(tmp_path) in sys.path

        # Cleanup
        sys.path.remove(str(tmp_path))

    def test_idempotent(self, tmp_path):
        """Calling bootstrap twice should not duplicate the path entry."""
        (tmp_path / "yt_dlp").mkdir()

        with patch.object(updater, "get_cache_dir", return_value=tmp_path):
            updater.bootstrap()
            updater.bootstrap()
            count = sys.path.count(str(tmp_path))
            assert count == 1

        sys.path.remove(str(tmp_path))


# =====================================================================
# update_ytdlp (mocked — avoids downloading ~15MB in tests)
# =====================================================================

class TestUpdateYtdlp:
    def _make_fake_wheel(self, path):
        """Create a minimal fake yt-dlp wheel zip for testing."""
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("yt_dlp/__init__.py", "")
            zf.writestr("yt_dlp/version.py", "__version__ = '9999.01.01'")

    def test_update_downloads_and_extracts(self, tmp_path):
        """Verify update flow: download wheel → extract → yt_dlp dir exists."""
        fake_wheel_path = tmp_path / "fake.whl"
        self._make_fake_wheel(fake_wheel_path)

        progress_msgs = []

        # Mock the network calls to serve our fake wheel
        with patch.object(updater, "get_cache_dir", return_value=tmp_path / "cache"), \
             patch.object(updater, "get_latest_version_info",
                          return_value=("9999.01.01", "https://fake/yt_dlp.whl")), \
             patch("yt_strip.updater.urlopen") as mock_urlopen:

            # Make urlopen return the fake wheel bytes
            mock_resp = MagicMock()
            mock_resp.read.return_value = fake_wheel_path.read_bytes()
            mock_resp.__enter__ = lambda s: mock_resp
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = updater.update_ytdlp(progress_callback=progress_msgs.append)

        assert result == "9999.01.01"
        assert (tmp_path / "cache" / "yt_dlp").is_dir()
        assert len(progress_msgs) >= 2  # at least "Downloading..." and "Installing..."

    def test_update_raises_on_no_wheel(self):
        """Should raise if PyPI has no compatible wheel."""
        with patch.object(updater, "get_latest_version_info",
                          return_value=("9999.01.01", None)):
            with pytest.raises(RuntimeError, match="No pure-Python wheel"):
                updater.update_ytdlp()
