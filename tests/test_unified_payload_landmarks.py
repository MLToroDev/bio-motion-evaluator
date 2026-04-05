"""Filtro de landmarks en payload API (solo puntos con visibility suficiente)."""

from __future__ import annotations

from vision.landmark_filter import landmarks_for_api_response


def test_landmarks_for_api_response_filters_by_visibility() -> None:
    lm = [
        {"index": 0, "x": 0.1, "y": 0.1, "z": 0.0, "visibility": 0.9},
        {"index": 1, "x": 0.2, "y": 0.2, "z": 0.0, "visibility": 0.2},
    ]
    wl = [
        {"index": 0, "x": 1.0, "y": 1.0, "z": 1.0, "visibility": None},
        {"index": 1, "x": 2.0, "y": 2.0, "z": 2.0, "visibility": None},
    ]
    out, wout = landmarks_for_api_response(lm, wl, 0.5)
    assert [p["index"] for p in (out or [])] == [0]
    assert wout is not None and [p["index"] for p in wout] == [0]


def test_landmarks_keeps_none_visibility() -> None:
    lm = [{"index": 5, "x": 0.5, "y": 0.5, "z": 0.0, "visibility": None}]
    out, wout = landmarks_for_api_response(lm, None, 0.5)
    assert out is not None and len(out) == 1
    assert wout is None


def test_landmarks_no_filter_when_min_zero() -> None:
    lm = [{"index": 0, "x": 0.1, "y": 0.1, "z": 0.0, "visibility": 0.1}]
    out, _ = landmarks_for_api_response(lm, None, 0.0)
    assert out is lm
