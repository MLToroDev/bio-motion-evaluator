"""Validación de extensiones en resolve_gold_standard_video."""

from __future__ import annotations

from pathlib import Path

import pytest

from vision.paths import list_gold_standard_video_filenames, resolve_gold_standard_video


def test_rejects_bad_suffix() -> None:
    base = Path(__file__).resolve().parent / "assets" / "videos"
    with pytest.raises(ValueError, match="Extensión"):
        resolve_gold_standard_video("not_a_video.txt", base)


def test_list_gold_standard_video_filenames_filters_and_sorts(tmp_path: Path) -> None:
    (tmp_path / "a.mp4").write_bytes(b"")
    (tmp_path / "B.MP4").write_bytes(b"")
    (tmp_path / "readme.txt").write_bytes(b"")
    (tmp_path / ".hidden.mp4").write_bytes(b"")
    names = list_gold_standard_video_filenames(tmp_path)
    assert names == ["a.mp4", "B.MP4"]


def test_list_gold_standard_missing_dir(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    assert list_gold_standard_video_filenames(missing) == []

