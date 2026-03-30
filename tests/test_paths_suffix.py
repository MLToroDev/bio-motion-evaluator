"""Validación de extensiones en resolve_gold_standard_video."""

from __future__ import annotations

from pathlib import Path

import pytest

from vision.paths import resolve_gold_standard_video


def test_rejects_bad_suffix() -> None:
    base = Path(__file__).resolve().parent / "assets" / "videos"
    with pytest.raises(ValueError, match="Extensión"):
        resolve_gold_standard_video("not_a_video.txt", base)
