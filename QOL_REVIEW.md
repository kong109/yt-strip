# YT Strip Quality-of-Life Review

## Summary

YT Strip already has a focused GUI, playlist support, metadata editing, a macOS build workflow, and regression tests for the downloader/updater. The highest-impact QOL work now is to make first-run setup and failed downloads easier for non-developers to understand and recover from.

## Recommended next improvements

1. **Replace the placeholder README with user-facing docs**
   - The current `readme.MD` describes a different app.
   - Add install/run instructions, supported platforms, ffmpeg setup, common errors, and screenshots/GIFs of the fetch/edit/download flow.

2. **Surface actionable download errors in the GUI**
   - Download failures currently bubble up as raw exception text.
   - Normalize common cases like missing/private videos, age restrictions, network failures, ffmpeg conversion errors, and invalid URLs into friendly messages with a suggested fix.

3. **Persist user preferences between launches**
   - Save the last output directory, preferred artist/album defaults, and window size in a small config file under the app data directory.
   - This removes repetitive setup for users downloading multiple sessions.

4. **Add a lightweight download history / overwrite warning**
   - `download_track` overwrites existing MP3s with the same sanitized filename.
   - Warn before replacing files, or auto-suffix duplicates, and optionally show recently downloaded tracks with their saved locations.

5. **Improve playlist editing controls**
   - Add per-track selection checkboxes, select all/none, and remove unavailable/private entries before downloading.
   - Add bulk operations for prefix numbering, artist/album copy-down, and title cleanup.

6. **Separate legacy CLI code from the packaged app path**
   - The top-level `yt_strip.py` duplicates some downloader behavior and uses different filename semantics than `yt_strip/downloader.py`.
   - Either document it as a supported batch CLI or move it under a clear `legacy/` or `scripts/` path to reduce contributor confusion.

7. **Make CI faster and more deterministic**
   - Several tests hit live YouTube/PyPI and can fail because of network or upstream changes.
   - Keep one optional smoke suite for live integrations, but make the default CI path rely on mocked downloader/updater tests.

## Suggested order

Start with the README and friendly error handling because those reduce support burden immediately. Then add preference persistence and overwrite safeguards, which improve everyday use without changing the core download pipeline.
