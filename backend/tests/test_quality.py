import os
from pathlib import Path
import pytest
from app.downloader import build_ydl_download_options, get_ffmpeg_path, get_base_ydl_opts
from app.config import DOWNLOADS_DIR

def test_ffmpeg_path_detection():
    """Verify that FFmpeg binary is discovered from system PATH or bundled imageio-ffmpeg."""
    ffmpeg_path = get_ffmpeg_path()
    assert ffmpeg_path is not None, "FFmpeg path should not be None (bundled or system FFmpeg must be discovered)"
    assert Path(ffmpeg_path).exists(), f"Discovered FFmpeg path {ffmpeg_path} does not exist on disk"
    # Verify FFmpeg directory is in os.environ["PATH"]
    ffmpeg_dir = str(Path(ffmpeg_path).parent.resolve())
    assert ffmpeg_dir in os.environ.get("PATH", ""), f"FFmpeg directory {ffmpeg_dir} should be in process PATH"


def test_base_ydl_opts_no_player_client_restriction():
    """Base options for YouTube must not override player_client with restrictive mobile-only clients."""
    opts = get_base_ydl_opts("youtube")
    extractor_args = opts.get("extractor_args", {})
    yt_args = extractor_args.get("youtube", {})
    # Should not force player_client which restricts YouTube to 360p mobile stream
    assert "player_client" not in yt_args, "player_client must not be overridden in base options"


def test_quality_1080p_format_generation():
    """1080p quality must target 1080p with valid vcodec format sorting and no 360p downgrade."""
    opts = build_ydl_download_options(
        quality="1080p",
        output_dir=DOWNLOADS_DIR,
        is_playlist=False,
        platform="youtube"
    )
    fmt = opts.get("format", "")
    assert "1080" in fmt
    assert "[ext=mp4]" not in fmt, "Format string should not filter video stream with [ext=mp4]"
    assert opts.get("merge_output_format") == "mp4"
    sort_list = opts.get("format_sort", [])
    assert "res:1080" in sort_list
    assert any("vcodec" in s for s in sort_list), "format_sort should sort by vcodec"


def test_quality_best_format_generation():
    """Best quality must download bestvideo+bestaudio and merge to MP4 without restricting to MP4 video."""
    opts = build_ydl_download_options(
        quality="best",
        output_dir=DOWNLOADS_DIR,
        is_playlist=False,
        platform="youtube"
    )
    fmt = opts.get("format", "")
    assert "bestvideo+bestaudio" in fmt
    assert "[ext=mp4]" not in fmt
    assert opts.get("merge_output_format") == "mp4"
    sort_list = opts.get("format_sort", [])
    assert "res" in sort_list
    assert any("vcodec" in s for s in sort_list), "format_sort should sort by vcodec"


def test_quality_720p_format_generation():
    """720p quality must target 720p resolution without dropping to 360p."""
    opts = build_ydl_download_options(
        quality="720p",
        output_dir=DOWNLOADS_DIR,
        is_playlist=False,
        platform="youtube"
    )
    fmt = opts.get("format", "")
    assert "720" in fmt
    assert "[ext=mp4]" not in fmt
    assert opts.get("merge_output_format") == "mp4"
    sort_list = opts.get("format_sort", [])
    assert "res:720" in sort_list
    assert any("vcodec" in s for s in sort_list)


def test_quality_480p_format_generation():
    """480p quality must target 480p resolution."""
    opts = build_ydl_download_options(
        quality="480p",
        output_dir=DOWNLOADS_DIR,
        is_playlist=False,
        platform="youtube"
    )
    fmt = opts.get("format", "")
    assert "480" in fmt
    assert "[ext=mp4]" not in fmt
    assert opts.get("merge_output_format") == "mp4"
    sort_list = opts.get("format_sort", [])
    assert "res:480" in sort_list
    assert any("vcodec" in s for s in sort_list)


def test_quality_audio_mp3_format_generation():
    """audio_mp3 quality must select audio and configure FFmpegExtractAudio postprocessor."""
    opts = build_ydl_download_options(
        quality="audio_mp3",
        output_dir=DOWNLOADS_DIR,
        is_playlist=False,
        platform="youtube"
    )
    assert opts.get("format") == "bestaudio/best"
    postprocessors = opts.get("postprocessors", [])
    assert any(pp.get("key") == "FFmpegExtractAudio" for pp in postprocessors)
    mp3_pp = next(pp for pp in postprocessors if pp.get("key") == "FFmpegExtractAudio")
    assert mp3_pp.get("preferredcodec") == "mp3"
