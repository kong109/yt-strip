#!/usr/bin/env python3
"""YT Strip — YouTube Audio Extractor. Entry point."""

import argparse

from yt_strip import __version__


def main():
    parser = argparse.ArgumentParser(description="YT Strip — YouTube Audio Extractor")
    parser.add_argument(
        "--version",
        action="version",
        version=f"yt-strip {__version__}",
    )
    parser.parse_args()

    # Bootstrap cached yt-dlp BEFORE anything imports it.
    from yt_strip.updater import bootstrap
    bootstrap()

    from yt_strip.app import App

    app = App()
    app.run()


if __name__ == "__main__":
    main()
