"""Backend logic for downloading YouTube audio and applying metadata."""

import os
import re
import shutil
import sys
from pathlib import Path

import yt_dlp
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, ID3NoHeaderError


def get_ffmpeg_path():
    """Find ffmpeg binary — checks bundled location first, then system PATH."""
    if getattr(sys, 'frozen', False):
        app_dir = Path(sys.executable).parent
        if sys.platform == 'darwin':
            # macOS .app bundle: check Contents/MacOS and Contents/Frameworks
            for candidate in [app_dir / 'ffmpeg', app_dir.parent / 'Resources' / 'ffmpeg']:
                if candidate.exists():
                    return str(candidate)
        else:
            bundled = app_dir / 'ffmpeg'
            if bundled.exists():
                return str(bundled)
            bundled_exe = app_dir / 'ffmpeg.exe'
            if bundled_exe.exists():
                return str(bundled_exe)

    return shutil.which('ffmpeg')


def sanitize_filename(name):
    """Remove characters that are invalid in filenames on macOS/Windows."""
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    sanitized = sanitized.strip('. ')
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    return sanitized or 'untitled'


def fetch_info(url):
    """
    Fetch video or playlist metadata without downloading.

    Returns a dict:
      type: 'video' | 'playlist'
      title: str
      entries: list[dict] (playlist only)
      url: str (single video only)
      uploader: str (single video only)
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',
        'ignoreerrors': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if info is None:
        raise ValueError("Could not fetch info. Check that the URL is valid and accessible.")

    # --- Playlist ---
    if info.get('_type') == 'playlist' or 'entries' in info:
        entries = []
        for i, entry in enumerate(info.get('entries', []), 1):
            if entry is None:
                continue
            video_url = entry.get('webpage_url') or entry.get('url', '')
            if video_url and not video_url.startswith('http'):
                video_url = f"https://www.youtube.com/watch?v={video_url}"
            if not video_url:
                vid = entry.get('id', '')
                if vid:
                    video_url = f"https://www.youtube.com/watch?v={vid}"
            entries.append({
                'index': i,
                'title': entry.get('title', f'Track {i}'),
                'url': video_url,
            })
        return {
            'type': 'playlist',
            'title': info.get('title', 'Unknown Playlist'),
            'entries': entries,
        }

    # --- Single video ---
    return {
        'type': 'video',
        'title': info.get('title', 'Unknown'),
        'url': info.get('webpage_url', url),
        'uploader': info.get('uploader', info.get('channel', '')),
    }


def download_track(url, output_dir, filename, metadata, progress_callback=None):
    """
    Download a single track as MP3 and write ID3 tags.

    Args:
        url:               YouTube video URL
        output_dir:        Folder to save the MP3
        filename:          Desired stem (no extension)
        metadata:          dict with keys title, artist, album, track_number (all optional)
        progress_callback: callable(float) with value 0.0–1.0

    Returns:
        Absolute path to the saved .mp3 file.
    """
    os.makedirs(output_dir, exist_ok=True)

    safe = sanitize_filename(filename)
    out_template = os.path.join(output_dir, f"{safe}.%(ext)s")
    mp3_path = os.path.join(output_dir, f"{safe}.mp3")

    ffmpeg = get_ffmpeg_path()

    def _hook(d):
        if not progress_callback:
            return
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            done = d.get('downloaded_bytes', 0)
            if total > 0:
                progress_callback(0.8 * done / total)
        elif d['status'] == 'finished':
            progress_callback(0.9)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'progress_hooks': [_hook],
        'quiet': True,
        'no_warnings': True,
        'overwrites': True,
    }

    if ffmpeg:
        ffmpeg_dir = os.path.dirname(ffmpeg)
        if ffmpeg_dir:
            ydl_opts['ffmpeg_location'] = ffmpeg_dir

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Write ID3 metadata
    if os.path.exists(mp3_path):
        _apply_metadata(mp3_path, metadata)

    if progress_callback:
        progress_callback(1.0)

    return mp3_path


def _apply_metadata(filepath, metadata):
    """Write ID3v2 tags to an MP3 file."""
    try:
        try:
            tags = ID3(filepath)
        except ID3NoHeaderError:
            tags = ID3()

        if metadata.get('title'):
            tags.delall('TIT2')
            tags.add(TIT2(encoding=3, text=metadata['title']))
        if metadata.get('artist'):
            tags.delall('TPE1')
            tags.add(TPE1(encoding=3, text=metadata['artist']))
        if metadata.get('album'):
            tags.delall('TALB')
            tags.add(TALB(encoding=3, text=metadata['album']))
        if metadata.get('track_number'):
            tags.delall('TRCK')
            tags.add(TRCK(encoding=3, text=str(metadata['track_number'])))

        tags.save(filepath)
    except Exception as e:
        print(f"Warning: could not write metadata to {filepath}: {e}")
