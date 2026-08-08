"""Curl sentado vs squat: aislamiento de codo sobre el vector 32D."""

from __future__ import annotations

import numpy as np

from app.models.schemas import ExerciseClassifierConfig
from vision.heuristic_exercise_classifier import (
    CURL_ISOLATION_MIN,
    IDLE_STILL_MIN,
    HeuristicExerciseClassifier,
    curl_isolation_score,
    idle_still_score,
)


def _vec(**kwargs: float) -> np.ndarray:
    x = np.zeros(32, dtype=np.float64)
    for i, v in kwargs.items():
        x[int(i[1:])] = float(v)
    return x


def test_seated_curl_isolation_high() -> None:
    # Rodillas ~90° fijas, codo rápido, tronco erguido, muñeca a media altura.
    f = _vec(
        i0=88.0,
        i1=90.0,
        i13=6.0,
        i14=7.0,
        i15=0.22,
        i21=8.0,
        i27=0.55,
        i28=0.52,
        i29=8.0,
        i30=12.0,
        i31=95.0,
    )
    assert curl_isolation_score(f) >= CURL_ISOLATION_MIN
    out = HeuristicExerciseClassifier(ExerciseClassifierConfig()).classify(f, True)
    assert out.label == "curl"
    assert out.confidence >= 0.72


def test_squat_not_rescued_as_curl() -> None:
    f = _vec(
        i0=70.0,
        i1=68.0,
        i13=48.0,
        i14=50.0,
        i15=0.20,
        i21=18.0,
        i27=0.25,
        i28=0.24,
        i29=70.0,
        i30=95.0,
        i31=18.0,
    )
    assert curl_isolation_score(f) < CURL_ISOLATION_MIN
    out = HeuristicExerciseClassifier(ExerciseClassifierConfig()).classify(f, True)
    assert out.label == "squat"


def test_unilateral_curl_uses_active_wrist() -> None:
    # Un brazo en curl (muñeca alta + codo rápido), el otro colgando.
    f = _vec(
        i0=88.0,
        i1=90.0,
        i13=5.0,
        i14=6.0,
        i15=0.18,
        i21=7.0,
        i27=0.70,
        i28=0.08,
        i29=7.0,
        i30=10.0,
        i31=70.0,
    )
    assert curl_isolation_score(f) >= CURL_ISOLATION_MIN
    out = HeuristicExerciseClassifier(ExerciseClassifierConfig()).classify(f, True)
    assert out.label == "curl"


def test_pushup_not_curl_high_trunk() -> None:
    f = _vec(
        i0=18.0,
        i1=16.0,
        i13=8.0,
        i14=7.0,
        i15=0.25,
        i21=78.0,
        i27=0.20,
        i28=0.18,
        i29=12.0,
        i30=18.0,
        i31=90.0,
    )
    assert curl_isolation_score(f) < CURL_ISOLATION_MIN


def test_standing_still_is_idle_not_deadlift_like() -> None:
    # De pie quieto: rodillas extendidas, ROM/velocidad bajas, tronco erguido, brazos colgando.
    f = _vec(
        i0=12.0,
        i1=14.0,
        i12=4.0,
        i13=3.0,
        i14=4.0,
        i15=0.02,
        i21=6.0,
        i27=0.08,
        i28=0.07,
        i29=4.0,
        i30=6.0,
        i31=8.0,
    )
    assert idle_still_score(f) >= IDLE_STILL_MIN
    assert idle_still_score(f) > curl_isolation_score(f)
    out = HeuristicExerciseClassifier(ExerciseClassifierConfig()).classify(f, True)
    assert out.label == "idle"


def test_standing_curl_not_idle() -> None:
    # Curl de pie: rodillas extendidas pero codo rápido.
    f = _vec(
        i0=14.0,
        i1=16.0,
        i13=5.0,
        i14=6.0,
        i15=0.18,
        i21=7.0,
        i27=0.55,
        i28=0.50,
        i29=6.0,
        i30=9.0,
        i31=90.0,
    )
    assert idle_still_score(f) < IDLE_STILL_MIN
    assert curl_isolation_score(f) >= CURL_ISOLATION_MIN
    out = HeuristicExerciseClassifier(ExerciseClassifierConfig()).classify(f, True)
    assert out.label == "curl"


def test_squat_not_idle_rescue() -> None:
    f = _vec(
        i0=70.0,
        i1=68.0,
        i13=48.0,
        i14=50.0,
        i15=0.20,
        i21=18.0,
        i27=0.25,
        i28=0.24,
        i29=70.0,
        i30=95.0,
        i31=18.0,
    )
    assert idle_still_score(f) < IDLE_STILL_MIN
