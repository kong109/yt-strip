# YT Strip

YT Strip is a desktop app for downloading YouTube audio as MP3 files and editing basic track metadata before saving.

It accepts individual video and playlist URLs. For each track, you can edit the
title, artist, and album before saving the finished MP3.

## Requirements

- Python 3.12 (the version used by the project's build workflow)
- [ffmpeg](https://ffmpeg.org/download.html) for MP3 conversion
- Tkinter, which is included with the standard Python installers for macOS and
  Windows; some Linux distributions package it separately
- An internet connection

## Supported platforms

The GUI is designed to run from source on macOS, Windows, and Linux with Python
3.12. The repository's packaged build is macOS-only: `build_macos.sh` and
`yt_strip.spec` produce a `.app` and DMG. There are currently no packaged
Windows or Linux builds.

## Install

Clone the repository and enter its directory:

```sh
git clone https://github.com/kong109/yt-strip.git
cd yt-strip
```

Create a virtual environment and install the Python dependencies.

On macOS or Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Install ffmpeg

ffmpeg is not installed by `requirements.txt` or stored in this repository.
Install it separately before starting YT Strip.

macOS with [Homebrew](https://brew.sh/):

```sh
brew install ffmpeg
```

Windows with [WinGet](https://learn.microsoft.com/windows/package-manager/winget/):

```powershell
winget install --id Gyan.FFmpeg --exact
```

Ubuntu or Debian Linux:

```sh
sudo apt update
sudo apt install ffmpeg
```

For other Linux distributions, use the distribution's ffmpeg package or follow
the links on the [official ffmpeg download page](https://ffmpeg.org/download.html).

Open a new terminal after installation, then confirm that ffmpeg is on `PATH`:

```sh
ffmpeg -version
```

If that command prints version information, YT Strip can find ffmpeg.

## Run the app

Activate the virtual environment if it is not already active, then launch the
GUI:

```sh
python main.py
```

Paste a public YouTube video or playlist URL, select **Fetch**, review the track
metadata and output directory, and start the download.

The top-level `yt_strip.py` is a separate, older playlist-only command-line
workflow. It does not launch the GUI:

```sh
python yt_strip.py "<playlist-url>" ["<another-playlist-url>"]
```

New users should start with `main.py`.

### Build the macOS app

On macOS, the packaging script creates `dist/YT Strip.app` and
`dist/YT-Strip.dmg`:

```sh
bash build_macos.sh
```

The script installs the Python requirements into `build_env`, installs ffmpeg
with Homebrew if necessary, and bundles the ffmpeg tools found on `PATH`.

## Troubleshooting

### “ffmpeg not found” or conversion fails

Run `ffmpeg -version` in a new terminal. If the command is not found, install
ffmpeg using the platform instructions above and make sure its `bin` directory
is on `PATH`. Start YT Strip from that same terminal after ffmpeg is available.

### A private or age-restricted video cannot be fetched

YT Strip's GUI does not currently provide browser-cookie or account
authentication. Private videos and age-restricted videos that require sign-in
therefore cannot be downloaded. Confirm that the URL plays while signed out in
a browser, or try a public URL instead. YT Strip does not bypass YouTube access
controls.

### `No module named tkinter` on Linux

Install the Tkinter package for the Python version supplied by your
distribution. On Ubuntu or Debian:

```sh
sudo apt install python3-tk
```

Then reactivate the virtual environment and run `python main.py` again.

### YouTube extraction suddenly stops working

YouTube changes can require a newer yt-dlp release. Use **Check for updates** in
the GUI, or update the package in the active virtual environment:

```sh
python -m pip install --upgrade yt-dlp
```

See [QOL_REVIEW.md](QOL_REVIEW.md) for the remaining quality-of-life
recommendations.
