"""Resolución de stream YouTube / URL sin descarga (OpenCV no invocado)."""

from __future__ import annotations

import pytest

from app.services.video.downloader import (
    is_youtube_page_url,
    normalize_youtube_url,
    pick_stream_url_from_info,
    resolve_playable_stream,
)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("https://youtu.be/dQw4w9WgXcQ", True),
        ("https://youtu.be/96O5mvyblQM?si=to9dWrS_aaNu0iVD", True),
        ("https://m.youtube.com/watch?v=abc", True),
        ("https://youtube.com/shorts/xyz", True),
        ("rtsp://192.168.1.10/stream", False),
        ("https://example.com/clip.mp4", False),
        ("", False),
    ],
)
def test_is_youtube_page_url(url: str, expected: bool) -> None:
    assert is_youtube_page_url(url) is expected


def test_pick_stream_url_prefers_video_format() -> None:
    info = {
        "url": "https://cdn.example/audio-only.m4a",
        "vcodec": "none",
        "requested_formats": [
            {"url": "https://cdn.example/audio.m4a", "vcodec": "none"},
            {
                "url": "https://cdn.example/video.mp4",
                "vcodec": "avc1.64001F",
                "http_headers": {"User-Agent": "yt-dlp", "Referer": "https://www.youtube.com/"},
            },
        ],
    }
    url, headers = pick_stream_url_from_info(info)
    assert url == "https://cdn.example/video.mp4"
    assert headers is not None
    assert headers["User-Agent"] == "yt-dlp"


def test_pick_stream_url_direct_when_video() -> None:
    info = {"url": "https://cdn.example/direct.mp4", "vcodec": "avc1.42E01E"}
    url, headers = pick_stream_url_from_info(info)
    assert url == "https://cdn.example/direct.mp4"
    assert headers is None


def test_normalize_youtube_share_si_param() -> None:
    out = normalize_youtube_url("https://youtu.be/96O5mvyblQM?si=to9dWrS_aaNu0iVD")
    assert out == "https://www.youtube.com/watch?v=96O5mvyblQM"


def test_normalize_youtube_shorts() -> None:
    assert (
        normalize_youtube_url("https://www.youtube.com/shorts/abcdefghijk")
        == "https://www.youtube.com/watch?v=abcdefghijk"
    )


def test_resolve_playable_stream_passthrough_rtsp() -> None:
    out = resolve_playable_stream("rtsp://cam.local/live")
    assert out.url == "rtsp://cam.local/live"
    assert out.finite is False
    assert out.is_live is False
    assert out.http_headers is None


def test_resolve_playable_stream_empty() -> None:
    with pytest.raises(ValueError, match="stream_url"):
        resolve_playable_stream("  ")
