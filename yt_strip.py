import sys
import os
import re
import shutil
import glob
import yt_dlp

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DELAY_BETWEEN_VIDEOS = 3  # seconds between downloads to avoid throttling


def sanitize_filename(name):
    """Remove characters that are invalid in file/folder names."""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    return name.strip('. ')


def find_aria2c():
    """Find aria2c — check bundled copy first, then PATH."""
    bundled = os.path.join(SCRIPT_DIR, "aria2-1.37.0-win-64bit-build1", "aria2c.exe")
    if os.path.isfile(bundled):
        return bundled
    if shutil.which("aria2c"):
        return "aria2c"
    return None


def get_playlist_info(url):
    """Extract playlist title and entry count without downloading."""
    with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
        info = ydl.extract_info(url, download=False)
    title = sanitize_filename(info.get("title", "Unknown Playlist"))
    entries = info.get("entries", [])
    return title, entries


def playlist_already_downloaded(playlist_dir, expected_count):
    """Check if folder exists and has all MP3s."""
    if not os.path.isdir(playlist_dir):
        return False
    existing = glob.glob(os.path.join(playlist_dir, "*.mp3"))
    return len(existing) >= expected_count


def download_playlist(url, output_root=".", aria2c_path=None):
    title, entries = get_playlist_info(url)
    entry_count = len(entries)

    if entry_count == 0:
        print(f"  No videos found — skipping", flush=True)
        return title, 0, "empty"

    playlist_dir = os.path.join(output_root, title)

    if playlist_already_downloaded(playlist_dir, entry_count):
        print(f"  Already have {entry_count} MP3(s) — skipping", flush=True)
        return title, entry_count, "skipped"

    os.makedirs(playlist_dir, exist_ok=True)

    # Use playlist_index for track numbering: "01 - Title.mp3"
    # Zero-pad based on playlist size
    pad = len(str(entry_count))
    outtmpl = os.path.join(
        playlist_dir,
        f"%(playlist_index|)0{pad}d - %(title)s.%(ext)s"
    )

    opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "outtmpl": outtmpl,
        "ignoreerrors": True,
        "quiet": False,
        "no_warnings": True,
        "sleep_interval": DELAY_BETWEEN_VIDEOS,
        "max_sleep_interval": DELAY_BETWEEN_VIDEOS + 2,
        "download_archive": os.path.join(playlist_dir, ".downloaded.txt"),
    }

    if aria2c_path:
        opts["external_downloader"] = aria2c_path
        opts["external_downloader_args"] = {
            "default": ["-x", "16", "-k", "1M", "-s", "16", "--console-log-level=warn"]
        }

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    return title, entry_count, "done"


def main():
    if len(sys.argv) < 2:
        print("Usage: python yt_strip.py <playlist_url> [playlist_url ...]")
        sys.exit(1)

    urls = sys.argv[1:]
    total = len(urls)
    aria2c_path = find_aria2c()

    print(f"\n{'='*60}", flush=True)
    print(f"  YT-STRIP — {total} playlists queued", flush=True)
    if aria2c_path:
        print(f"  Using aria2c: {aria2c_path}", flush=True)
    else:
        print(f"  aria2c not found — using default downloader", flush=True)
    print(f"{'='*60}\n", flush=True)

    results = []

    for i, url in enumerate(urls, 1):
        pct = (i - 1) / total * 100
        print(f"\n[{i}/{total}] ({pct:.0f}%) Fetching playlist info...", flush=True)
        print(f"  URL: {url}", flush=True)

        try:
            title, count, status = download_playlist(url, ".", aria2c_path)
            results.append((title, count, status))
            print(f"  => {status.upper()}: \"{title}\" ({count} tracks)", flush=True)
        except Exception as e:
            print(f"  => ERROR: {e}", flush=True)
            results.append(("???", 0, "error"))

    # Final summary
    print(f"\n\n{'='*60}", flush=True)
    print(f"  COMPLETE — {total} playlists processed", flush=True)
    print(f"{'='*60}", flush=True)
    done = sum(1 for _, _, s in results if s == "done")
    skipped = sum(1 for _, _, s in results if s == "skipped")
    errors = sum(1 for _, _, s in results if s in ("error", "empty"))
    print(f"  Downloaded: {done}  |  Skipped: {skipped}  |  Errors: {errors}", flush=True)
    print(flush=True)
    for title, count, status in results:
        icon = {"done": "+", "skipped": "=", "error": "!", "empty": "!"}[status]
        print(f"  [{icon}] {title} ({count} tracks) — {status}", flush=True)
    print(flush=True)


if __name__ == "__main__":
    main()
