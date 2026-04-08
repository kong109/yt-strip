"""Tests for yt_strip.downloader — core download and metadata logic."""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from yt_strip import downloader


# =====================================================================
# sanitize_filename
# =====================================================================

class TestSanitizeFilename:
    def test_removes_invalid_chars(self):
        assert downloader.sanitize_filename('a<b>c:d"e/f\\g|h?i*j') == "abcdefghij"

    def test_strips_dots_and_spaces(self):
        assert downloader.sanitize_filename("...hello...") == "hello"
        assert downloader.sanitize_filename("  hello  ") == "hello"

    def test_truncates_long_names(self):
        long = "a" * 300
        result = downloader.sanitize_filename(long)
        assert len(result) == 200

    def test_returns_untitled_for_empty(self):
        assert downloader.sanitize_filename("") == "untitled"
        assert downloader.sanitize_filename("***") == "untitled"

    def test_normal_name_unchanged(self):
        assert downloader.sanitize_filename("My Song - Artist") == "My Song - Artist"

    def test_preserves_unicode(self):
        assert downloader.sanitize_filename("Café Müsik 日本語") == "Café Müsik 日本語"


# =====================================================================
# get_ffmpeg_path
# =====================================================================

class TestGetFfmpegPath:
    def test_finds_ffmpeg_on_path(self):
        """ffmpeg should be discoverable (either on PATH or returns None gracefully)."""
        result = downloader.get_ffmpeg_path()
        # On CI or dev machines ffmpeg may or may not be installed;
        # the function should not raise regardless.
        assert result is None or os.path.basename(result).startswith("ffmpeg")

    @patch("shutil.which", return_value=None)
    def test_returns_none_when_missing(self, mock_which):
        result = downloader.get_ffmpeg_path()
        assert result is None

    @patch("shutil.which", return_value="/usr/local/bin/ffmpeg")
    def test_returns_system_ffmpeg(self, mock_which):
        result = downloader.get_ffmpeg_path()
        assert result == "/usr/local/bin/ffmpeg"


# =====================================================================
# fetch_info — single video
# =====================================================================

class TestFetchInfoSingleVideo:
    """Test fetch_info against a real YouTube URL (short, public, stable)."""

    # "Me at the zoo" — first YouTube video ever, unlikely to be removed
    TEST_VIDEO_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"

    def test_single_video_returns_correct_structure(self):
        info = downloader.fetch_info(self.TEST_VIDEO_URL)
        assert info["type"] == "video"
        assert isinstance(info["title"], str)
        assert len(info["title"]) > 0
        assert "url" in info
        assert "uploader" in info

    def test_single_video_url_preserved(self):
        info = downloader.fetch_info(self.TEST_VIDEO_URL)
        assert "jNQXAC9IVRw" in info["url"]

    def test_invalid_url_raises(self):
        with pytest.raises(Exception):
            downloader.fetch_info("https://www.youtube.com/watch?v=INVALID_ID_999999")


# =====================================================================
# fetch_info — playlist
# =====================================================================

class TestFetchInfoPlaylist:
    """Test fetch_info against a real public playlist."""

    # Coding Train "Coding Challenges" — large, stable, public playlist
    TEST_PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLRqwX-V7Uu6ZiZxtDDRCi6uhfTH4FilpH"

    def test_playlist_returns_correct_structure(self):
        info = downloader.fetch_info(self.TEST_PLAYLIST_URL)
        assert info["type"] == "playlist"
        assert isinstance(info["title"], str)
        assert len(info["title"]) > 0
        assert "entries" in info
        assert isinstance(info["entries"], list)
        assert len(info["entries"]) > 0

    def test_playlist_entries_have_required_fields(self):
        info = downloader.fetch_info(self.TEST_PLAYLIST_URL)
        assert len(info["entries"]) > 0
        entry = info["entries"][0]
        assert "index" in entry
        assert "title" in entry
        assert "url" in entry
        assert entry["url"].startswith("http")


# =====================================================================
# download_track — real download (small video)
# =====================================================================

class TestDownloadTrack:
    """Test actual download+conversion pipeline with a very short video."""

    TEST_VIDEO_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"

    @pytest.fixture
    def tmp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    def test_download_produces_mp3(self, tmp_dir):
        """Core pipeline: download, convert to MP3, return path."""
        if not downloader.get_ffmpeg_path():
            pytest.skip("ffmpeg not available")

        progress_values = []

        def on_progress(p):
            progress_values.append(p)

        path = downloader.download_track(
            self.TEST_VIDEO_URL,
            tmp_dir,
            "test_song",
            {"title": "Test", "artist": "Tester", "album": "TestAlbum"},
            on_progress,
        )

        assert path.endswith(".mp3")
        assert os.path.isfile(path)
        assert os.path.getsize(path) > 0
        # Progress should have been reported
        assert len(progress_values) > 0
        assert progress_values[-1] == 1.0

    def test_download_writes_metadata(self, tmp_dir):
        """Verify ID3 tags are written correctly."""
        if not downloader.get_ffmpeg_path():
            pytest.skip("ffmpeg not available")

        from mutagen.id3 import ID3

        meta = {
            "title": "Zoo Video",
            "artist": "jawed",
            "album": "First Videos",
            "track_number": 1,
        }

        path = downloader.download_track(
            self.TEST_VIDEO_URL, tmp_dir, "meta_test", meta
        )

        tags = ID3(path)
        assert str(tags.get("TIT2")) == "Zoo Video"
        assert str(tags.get("TPE1")) == "jawed"
        assert str(tags.get("TALB")) == "First Videos"
        assert str(tags.get("TRCK")) == "1"

    def test_sanitized_filename_used(self, tmp_dir):
        """Filenames with special chars should be sanitized."""
        if not downloader.get_ffmpeg_path():
            pytest.skip("ffmpeg not available")

        path = downloader.download_track(
            self.TEST_VIDEO_URL, tmp_dir, 'bad:file/name"test', {}
        )

        basename = os.path.basename(path)
        assert ":" not in basename
        assert "/" not in basename
        assert '"' not in basename


# =====================================================================
# _apply_metadata (unit test with a real mp3 stub)
# =====================================================================

class TestApplyMetadata:
    """Test metadata writing in isolation."""

    def test_writes_all_tags(self, tmp_path):
        """Create a minimal valid MP3 and apply tags."""
        from mutagen.id3 import ID3, TIT2

        # Create a minimal MP3-like file with an ID3 header
        mp3_file = tmp_path / "test.mp3"
        # Write minimal MP3 frame header + silence
        # (Mutagen needs at least a recognizable file)
        mp3_file.write_bytes(
            b"\xff\xfb\x90\x00" + b"\x00" * 417  # minimal MPEG frame
        )

        meta = {
            "title": "My Title",
            "artist": "My Artist",
            "album": "My Album",
            "track_number": 5,
        }
        downloader._apply_metadata(str(mp3_file), meta)

        tags = ID3(str(mp3_file))
        assert str(tags["TIT2"]) == "My Title"
        assert str(tags["TPE1"]) == "My Artist"
        assert str(tags["TALB"]) == "My Album"
        assert str(tags["TRCK"]) == "5"

    def test_partial_metadata(self, tmp_path):
        """Only supplied fields should be written."""
        mp3_file = tmp_path / "test.mp3"
        mp3_file.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 417)

        downloader._apply_metadata(str(mp3_file), {"title": "Only Title"})

        from mutagen.id3 import ID3
        tags = ID3(str(mp3_file))
        assert str(tags["TIT2"]) == "Only Title"
        assert tags.get("TPE1") is None
        assert tags.get("TALB") is None

    def test_empty_metadata_no_crash(self, tmp_path):
        """Empty metadata dict should not raise."""
        mp3_file = tmp_path / "test.mp3"
        mp3_file.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 417)
        downloader._apply_metadata(str(mp3_file), {})


# =====================================================================
# URL resolution logic (from app.py)
# =====================================================================

class TestResolveUrl:
    """Test the URL classification logic used by the app."""

    def test_plain_video_url(self):
        from urllib.parse import urlparse, parse_qs
        url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        assert "v" in params
        assert "list" not in params

    def test_plain_playlist_url(self):
        from urllib.parse import urlparse, parse_qs
        url = "https://www.youtube.com/playlist?list=PLtest123"
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        assert "list" in params
        assert "v" not in params

    def test_combined_url_has_both(self):
        from urllib.parse import urlparse, parse_qs
        url = "https://www.youtube.com/watch?v=abc123&list=PLtest123"
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        assert "v" in params
        assert "list" in params


# =====================================================================
# yt-dlp compatibility diagnostic
# =====================================================================

class TestYtdlpHealth:
    """Canary tests — if these fail, yt-dlp needs updating."""

    def test_ytdlp_can_extract_video_info(self):
        """yt-dlp can still talk to YouTube (the #1 reason for 'no longer working')."""
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(
                "https://www.youtube.com/watch?v=jNQXAC9IVRw", download=False
            )
        assert info is not None
        assert info.get("title")

    def test_ytdlp_version_not_ancient(self):
        """Warn if yt-dlp is more than ~6 months old (YouTube breaks old versions)."""
        import yt_dlp
        version = yt_dlp.version.__version__  # e.g. "2026.03.13"
        parts = version.split(".")
        year = int(parts[0])
        # If the yt-dlp release year is more than 1 behind, it's likely broken
        assert year >= 2025, (
            f"yt-dlp version {version} is very old — YouTube extraction "
            f"will likely fail. Run: pip install -U yt-dlp"
        )
