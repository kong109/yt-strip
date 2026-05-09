"""Tests for the main CLI entry point."""

import sys
from types import SimpleNamespace

import pytest

import main
from yt_strip import __version__


def test_version_flag_prints_version_and_exits(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "--version"])

    with pytest.raises(SystemExit) as exc_info:
        main.main()

    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"yt-strip {__version__}"


def test_no_args_runs_app(monkeypatch):
    calls = []

    class FakeApp:
        def run(self):
            calls.append("run")

    monkeypatch.setattr(sys, "argv", ["main.py"])
    monkeypatch.setitem(
        sys.modules,
        "yt_strip.updater",
        SimpleNamespace(bootstrap=lambda: calls.append("bootstrap")),
    )
    monkeypatch.setitem(sys.modules, "yt_strip.app", SimpleNamespace(App=FakeApp))

    main.main()

    assert calls == ["bootstrap", "run"]
