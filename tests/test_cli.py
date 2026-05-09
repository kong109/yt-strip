"""Tests for the YT Strip CLI entry point."""

import subprocess
import sys
import types
from pathlib import Path

import main as cli
from yt_strip import __version__


ROOT = Path(__file__).resolve().parents[1]


def test_version_flag_prints_version_and_exits_cleanly():
    result = subprocess.run(
        [sys.executable, "main.py", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == f"yt-strip {__version__}"
    assert result.stderr == ""


def test_main_still_bootstraps_and_runs_gui_by_default(monkeypatch):
    calls = []

    def fake_bootstrap():
        calls.append("bootstrap")

    class FakeApp:
        def __init__(self):
            calls.append("app")

        def run(self):
            calls.append("run")

    monkeypatch.setattr(cli, "parse_args", lambda: None)
    monkeypatch.setitem(
        sys.modules,
        "yt_strip.updater",
        types.SimpleNamespace(bootstrap=fake_bootstrap),
    )
    monkeypatch.setitem(
        sys.modules,
        "yt_strip.app",
        types.SimpleNamespace(App=FakeApp),
    )

    cli.main()

    assert calls == ["bootstrap", "app", "run"]
