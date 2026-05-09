#!/usr/bin/env python3
"""YT Strip — YouTube Audio Extractor. Entry point."""

import argparse

from yt_strip import __version__


def build_parser():
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(description="YT Strip — YouTube Audio Extractor")
    parser.add_argument(
        "--version",
        action="version",
        version=f"yt-strip {__version__}",
    )
    return parser


def main(argv=None):
    build_parser().parse_args(argv)

    # Bootstrap cached yt-dlp BEFORE anything imports it.
    from yt_strip.updater import bootstrap
    bootstrap()

    from yt_strip.app import App
    app = App()
    app.run()


if __name__ == "__main__":
    main()
