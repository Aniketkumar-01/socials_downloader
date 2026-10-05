import os
from pathlib import Path
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


def test_get_format_resolution_orientation_neutral():
    """Verify that resolution is calculated as shorter side for both portrait and landscape."""
    from app.downloader import get_format_resolution

    # Landscape 1080p
    assert get_format_resolution({"width": 1920, "height": 1080}) == 1080
    # Portrait 1080p (Shorts / Reels)
    assert get_format_resolution({"width": 1080, "height": 1920}) == 1080
    # Landscape 720p
    assert get_format_resolution({"width": 1280, "height": 720}) == 720
    # Portrait 720p
    assert get_format_resolution({"width": 720, "height": 1280}) == 720
    # Single dimension
    assert get_format_resolution({"height": 480}) == 480
    assert get_format_resolution({"width": 640}) == 640


def test_estimate_quality_sizes_distinct_sizes():
    """Verify that videos with multiple qualities produce distinct estimated sizes and do not duplicate sizes."""
    from app.downloader import estimate_quality_sizes

    mock_info = {
        "duration": 100,
        "formats": [
            # Audio
            {"vcodec": "none", "acodec": "mp4a", "filesize": 1_000_000, "abr": 128},
            # 480p video
            {"vcodec": "avc1", "acodec": "none", "height": 480, "width": 854, "filesize": 5_000_000, "tbr": 1000},
            # 720p video
            {"vcodec": "avc1", "acodec": "none", "height": 720, "width": 1280, "filesize": 15_000_000, "tbr": 2500},
            # 1080p video
            {"vcodec": "avc1", "acodec": "none", "height": 1080, "width": 1920, "filesize": 35_000_000, "tbr": 5000},
        ]
    }

    quality_sizes, quality_sizes_formatted, available_qualities = estimate_quality_sizes(mock_info)

    assert "best" in available_qualities
    assert "1080p" in available_qualities
    assert "720p" in available_qualities
    assert "480p" in available_qualities
    assert "audio_mp3" in available_qualities

    # Sizes must be strictly descending: 1080p > 720p > 480p > audio
    size_1080 = quality_sizes["1080p"]
    size_720 = quality_sizes["720p"]
    size_480 = quality_sizes["480p"]
    size_audio = quality_sizes["audio_mp3"]

    assert size_1080 is not None and size_720 is not None and size_480 is not None
    assert size_1080 > size_720 > size_480 > size_audio, (
        f"Expected descending sizes, got: 1080p={size_1080}, 720p={size_720}, 480p={size_480}, audio={size_audio}"
    )


def test_available_qualities_filters_unavailable_tiers():
    """If a video maxes out at 480p, 1080p and 720p must NOT be present in available_qualities."""
    from app.downloader import estimate_quality_sizes

    mock_info = {
        "duration": 60,
        "formats": [
            {"vcodec": "none", "acodec": "mp4a", "filesize": 500_000},
            {"vcodec": "avc1", "acodec": "none", "height": 480, "width": 854, "filesize": 3_000_000},
            {"vcodec": "avc1", "acodec": "none", "height": 360, "width": 640, "filesize": 1_500_000},
        ]
    }

    quality_sizes, quality_sizes_formatted, available_qualities = estimate_quality_sizes(mock_info)

    # 1080p and 720p should not be offered for a 480p max video
    assert "1080p" not in available_qualities
    assert "720p" not in available_qualities
    assert "480p" in available_qualities
    assert "best" in available_qualities
    assert "audio_mp3" in available_qualities


def test_quality_options_2160p_and_360p_format_generation():
    """Verify that 2160p and 360p qualities generate proper format strings."""
    opts_4k = build_ydl_download_options(
        quality="2160p",
        output_dir=DOWNLOADS_DIR,
        is_playlist=False,
        platform="youtube"
    )
    assert "2160" in opts_4k.get("format", "")
    assert "res:2160" in opts_4k.get("format_sort", [])

    opts_360 = build_ydl_download_options(
        quality="360p",
        output_dir=DOWNLOADS_DIR,
        is_playlist=False,
        platform="youtube"
    )
    assert "360" in opts_360.get("format", "")
    assert "res:360" in opts_360.get("format_sort", [])

