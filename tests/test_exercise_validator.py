"""Pruebas sintéticas del validador / teacher de ejercicio."""

from __future__ import annotations

import numpy as np

from vision.exercise_validator import ExerciseValidator, build_exercise_validator
from vision.types import ClassificationResult


def _vec() -> np.ndarray:
    return np.zeros(32, dtype=np.float64)


def test_build_disabled_returns_none() -> None:
    assert build_exercise_validator(
        enabled=False,
        unknown_label="unknown",
        min_confidence=0.65,
        min_margin=0.12,
        teacher_mode="margin",
    ) is None


def test_uncertain_when_window_incomplete() -> None:
    v = ExerciseValidator(teacher_mode="margin", min_confidence=0.5, min_margin=0.1)
    out = v.validate(
        _vec(),
        window_full=False,
        primary=ClassificationResult(label="squat", confidence=0.9, raw_scores={"squat": 0.9, "idle": 0.1}),
    )
    assert out.verdict == "uncertain"
    assert out.reason == "window_incomplete"


def test_confirm_by_margin() -> None:
    v = build_exercise_validator(
        enabled=True,
        unknown_label="unknown",
        min_confidence=0.6,
        min_margin=0.15,
        teacher_mode="margin",
        change_hold_frames=2,
    )
    assert v is not None
    out = v.validate(
        _vec(),
        window_full=True,
        primary=ClassificationResult(
            label="squat",
            confidence=0.85,
            raw_scores={"squat": 0.8, "idle": 0.15, "lunge": 0.05},
        ),
    )
    assert out.verdict == "confirm"
    assert out.primary_label == "squat"


def test_changed_on_label_transition() -> None:
    v = ExerciseValidator(
        teacher_mode="margin",
        min_confidence=0.5,
        min_margin=0.05,
        change_hold_frames=3,
        teacher=None,
    )
    # Forzar teacher margen via build
    v = build_exercise_validator(
        enabled=True,
        unknown_label="unknown",
        min_confidence=0.5,
        min_margin=0.05,
        teacher_mode="margin",
        change_hold_frames=3,
    )
    assert v is not None
    a = v.validate(
        _vec(),
        window_full=True,
        primary=ClassificationResult(
            label="squat",
            confidence=0.9,
            raw_scores={"squat": 0.85, "lunge": 0.1, "idle": 0.05},
        ),
    )
    assert a.verdict == "confirm"
    b = v.validate(
        _vec(),
        window_full=True,
        primary=ClassificationResult(
            label="lunge",
            confidence=0.9,
            raw_scores={"lunge": 0.85, "squat": 0.1, "idle": 0.05},
        ),
    )
    assert b.verdict == "changed"
    assert b.previous_label == "squat"
    assert "lunge" in b.reason


def test_reject_when_teacher_disagrees() -> None:
    class _StubTeacher:
        def classify(self, features: np.ndarray, window_full: bool) -> ClassificationResult:
            return ClassificationResult(
                label="lunge",
                confidence=0.92,
                raw_scores={"lunge": 0.92, "squat": 0.08},
            )

    v = ExerciseValidator(
        unknown_label="unknown",
        min_confidence=0.6,
        min_margin=0.05,
        teacher_mode="heuristic",
        teacher=_StubTeacher(),
        change_hold_frames=1,
    )
    out = v.validate(
        _vec(),
        window_full=True,
        primary=ClassificationResult(
            label="squat",
            confidence=0.8,
            raw_scores={"squat": 0.7, "lunge": 0.3},
        ),
    )
    assert out.verdict == "reject"
    assert out.validator_label == "lunge"


def test_as_dict_keys() -> None:
    v = build_exercise_validator(
        enabled=True,
        unknown_label="unknown",
        min_confidence=0.5,
        min_margin=0.1,
        teacher_mode="margin",
    )
    assert v is not None
    d = v.validate(
        _vec(),
        window_full=True,
        primary=ClassificationResult(label="idle", confidence=0.7, raw_scores={"idle": 0.7, "squat": 0.3}),
    ).as_dict()
    for k in ("verdict", "primary_label", "validator_label", "confidence", "score_margin", "reason", "teacher_mode"):
        assert k in d


def test_auto_without_onnx_falls_back_to_heuristic() -> None:
    from pathlib import Path

    missing = Path("/tmp/bio_motion_missing_exercise_validator.onnx")
    if missing.exists():
        missing.unlink()
    v = build_exercise_validator(
        enabled=True,
        unknown_label="unknown",
        min_confidence=0.5,
        min_margin=0.1,
        teacher_mode="auto",
        onnx_path=missing,
    )
    assert v is not None
    assert v._teacher_mode == "heuristic"


def test_onnx_teacher_smoke_if_artifact_present() -> None:
    from pathlib import Path

    from app.paths import backend_root

    path = backend_root() / "vision" / "models" / "exercise_validator.onnx"
    if not path.is_file():
        return  # skip soft: artefacto se genera con scripts/train_exercise_validator.py
    v = build_exercise_validator(
        enabled=True,
        unknown_label="unknown",
        min_confidence=0.5,
        min_margin=0.05,
        teacher_mode="onnx",
        onnx_path=path,
    )
    assert v is not None
    assert v._teacher_mode == "onnx"
    out = v.validate(
        _vec(),
        window_full=True,
        primary=ClassificationResult(
            label="squat",
            confidence=0.9,
            raw_scores={"squat": 0.8, "idle": 0.1, "lunge": 0.1},
        ),
    )
    d = out.as_dict()
    assert d["verdict"] in ("confirm", "reject", "changed", "uncertain")
    assert d["teacher_mode"] == "onnx"
    assert "primary_label" in d
