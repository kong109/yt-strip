"""Tests for the main CLI entry point."""

import pytest

import main
from yt_strip import __version__


def test_version_flag_prints_version_and_exits_without_starting_gui(capsys, monkeypatch):
    def fail_if_app_imported(name, *args, **kwargs):
        if name == "yt_strip.app":
            raise AssertionError("GUI module should not be imported for --version")
        return real_import(name, *args, **kwargs)

    real_import = __import__
    monkeypatch.setattr("builtins.__import__", fail_if_app_imported)

    with pytest.raises(SystemExit) as exc_info:
        main.main(["--version"])

    assert exc_info.value.code == 0
    assert capsys.readouterr().out == f"yt-strip {__version__}\n"


def test_default_behavior_bootstraps_and_runs_gui(monkeypatch):
    calls = []

    monkeypatch.setattr("yt_strip.updater.bootstrap", lambda: calls.append("bootstrap"))

    class FakeApp:
        def __init__(self):
            calls.append("app")

        def run(self):
            calls.append("run")

    monkeypatch.setattr("yt_strip.app.App", FakeApp)

    main.main([])

    assert calls == ["bootstrap", "app", "run"]
