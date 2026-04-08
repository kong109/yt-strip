#!/usr/bin/env python3
"""YT Strip — YouTube Audio Extractor. Entry point."""

# Bootstrap cached yt-dlp BEFORE anything imports it.
from yt_strip.updater import bootstrap
bootstrap()

from yt_strip.app import App


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()
