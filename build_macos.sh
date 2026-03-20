#!/usr/bin/env bash
# build_macos.sh — Build YT Strip as a standalone macOS .app
# Run this on a Mac (or in a macOS CI runner).
set -euo pipefail

echo "=== YT Strip macOS Build ==="

# --- Python ---
python3 --version || { echo "ERROR: Python 3 is required."; exit 1; }

# --- Virtual environment ---
if [ ! -d "build_env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv build_env
fi
source build_env/bin/activate

# --- Python deps ---
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# --- ffmpeg ---
if ! command -v ffmpeg &>/dev/null; then
    echo "ffmpeg not found. Installing via Homebrew..."
    if ! command -v brew &>/dev/null; then
        echo "ERROR: Homebrew is required to install ffmpeg."
        echo "       Install it from https://brew.sh and re-run this script."
        exit 1
    fi
    brew install ffmpeg
fi
echo "ffmpeg: $(which ffmpeg)"

# --- Build ---
echo "Running PyInstaller..."
pyinstaller yt_strip.spec --noconfirm

# --- Create DMG ---
APP_PATH="dist/YT Strip.app"
DMG_PATH="dist/YT-Strip.dmg"

if [ -d "$APP_PATH" ]; then
    echo "Creating DMG..."
    rm -f "$DMG_PATH"
    hdiutil create \
        -volname "YT Strip" \
        -srcfolder "$APP_PATH" \
        -ov -format UDZO \
        "$DMG_PATH"
    echo ""
    echo "=== Build complete! ==="
    echo "  App: $APP_PATH"
    echo "  DMG: $DMG_PATH"
else
    echo "ERROR: .app bundle not found at $APP_PATH"
    exit 1
fi
