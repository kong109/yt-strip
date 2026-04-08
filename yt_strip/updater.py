"""yt-dlp auto-updater for bundled YT Strip app.

Downloads the latest yt-dlp wheel from PyPI into a user-writable cache
directory.  On startup, bootstrap() prepends that cache to sys.path so
the fresh version is used instead of the (potentially stale) bundled one.
"""

import json
import os
import shutil
import ssl
import sys
import zipfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

PYPI_URL = "https://pypi.org/pypi/yt-dlp/json"
APP_NAME = "YT Strip"


# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

def get_cache_dir():
    """Platform-appropriate directory for the updated yt-dlp package."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APP_NAME / "packages"


# ------------------------------------------------------------------
# SSL helper (needed inside PyInstaller bundles)
# ------------------------------------------------------------------

def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


# ------------------------------------------------------------------
# Version queries
# ------------------------------------------------------------------

def get_installed_version():
    """Return the currently-loaded yt-dlp version string."""
    try:
        import yt_dlp
        return yt_dlp.version.__version__
    except Exception:
        return "0.0.0"


def get_latest_version_info():
    """Query PyPI for the latest yt-dlp version and its wheel URL.

    Returns (version_str, wheel_url) or raises on network error.
    """
    req = Request(PYPI_URL, headers={"Accept": "application/json"})
    ctx = _ssl_context()
    with urlopen(req, timeout=15, context=ctx) as resp:
        data = json.loads(resp.read().decode())

    version = data["info"]["version"]

    wheel_url = None
    for f in data["urls"]:
        if f["filename"].endswith("-py3-none-any.whl"):
            wheel_url = f["url"]
            break

    return version, wheel_url


def needs_update():
    """Check whether a newer yt-dlp exists on PyPI.

    Returns (update_available: bool, current: str, latest: str).
    Never raises — returns (False, ...) on network errors.
    """
    try:
        latest, _ = get_latest_version_info()
        current = get_installed_version()
        return (latest != current), current, latest
    except Exception:
        return False, get_installed_version(), "unknown"


# ------------------------------------------------------------------
# Update
# ------------------------------------------------------------------

def update_ytdlp(progress_callback=None):
    """Download the newest yt-dlp wheel from PyPI and extract it.

    Args:
        progress_callback: optional callable(str) for status messages.

    Returns the new version string.
    """
    latest, wheel_url = get_latest_version_info()

    if not wheel_url:
        raise RuntimeError(f"No pure-Python wheel found for yt-dlp {latest}")

    cache_dir = get_cache_dir()

    # Wipe previous cached version
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    if progress_callback:
        progress_callback(f"Downloading yt-dlp {latest}...")

    wheel_path = cache_dir / "yt_dlp.whl"
    ctx = _ssl_context()
    req = Request(wheel_url)
    with urlopen(req, timeout=120, context=ctx) as resp:
        wheel_path.write_bytes(resp.read())

    if progress_callback:
        progress_callback("Installing...")

    with zipfile.ZipFile(wheel_path) as zf:
        zf.extractall(cache_dir)

    wheel_path.unlink()

    # Make sure future imports in this process see the new version
    bootstrap()

    if progress_callback:
        progress_callback(f"Updated to yt-dlp {latest} — restart app to use it")

    return latest


# ------------------------------------------------------------------
# Bootstrap (called once at startup, before yt_dlp is imported)
# ------------------------------------------------------------------

def bootstrap():
    """Prepend the cache dir to sys.path if it holds an updated yt-dlp."""
    cache_dir = get_cache_dir()
    if (cache_dir / "yt_dlp").is_dir():
        cache_str = str(cache_dir)
        if cache_str not in sys.path:
            sys.path.insert(0, cache_str)
