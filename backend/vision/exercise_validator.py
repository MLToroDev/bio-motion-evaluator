"""Validador / teacher ligero sobre el vector 32D (confirm / reject / changed).

Complementa el clasificador primario (ONNX + histéresis) sin dependencias pesadas:
usa margen de scores del primario, opcionalmente un teacher heuristico independiente,
y deteccion de cambio de ejercicio por etiqueta estable previa.

Pensado para gatear AUTO_COLLECT y senalizar calidad de etiqueta en el payload WS.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

import numpy as np

from app.models.schemas import ExerciseClassifierConfig
from vision.types import ClassificationResult

log = logging.getLogger(__name__)

ExerciseVerdict = Literal["confirm", "reject", "changed", "uncertain"]
TeacherMode = Literal["margin", "heuristic", "onnx", "auto"]


@dataclass(frozen=True)
class ExerciseValidationResult:
    """Salida del validador por fotograma."""

    verdict: ExerciseVerdict
    primary_label: str
    validator_label: str | None
    confidence: float
    score_margin: float
    reason: str
    previous_label: str | None = None
    teacher_mode: str = "margin"

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "primary_label": self.primary_label,
            "validator_label": self.validator_label,
            "confidence": float(self.confidence),
            "score_margin": float(self.score_margin),
            "reason": self.reason,
            "previous_label": self.previous_label,
            "teacher_mode": self.teacher_mode,
        }


class _Teacher(Protocol):
    def classify(self, features: np.ndarray, window_full: bool) -> ClassificationResult: ...


def _score_margin(raw_scores: dict[str, float] | None) -> float:
    if not raw_scores:
        return 0.0
    vals = sorted((float(v) for v in raw_scores.values()), reverse=True)
    if not vals:
        return 0.0
    if len(vals) == 1:
        return float(vals[0])
    return float(vals[0] - vals[1])


def _argmax_label(raw_scores: dict[str, float] | None) -> str | None:
    if not raw_scores:
        return None
    return max(raw_scores.items(), key=lambda kv: float(kv[1]))[0]


class _MarginTeacher:
    """Teacher degenerado: la etiqueta valida es el argmax del primario si el margen es alto."""

    def __init__(self, min_margin: float, unknown: str) -> None:
        self._min_margin = float(min_margin)
        self._unknown = unknown
        self._last_primary: ClassificationResult | None = None

    def bind_primary(self, primary: ClassificationResult) -> None:
        self._last_primary = primary

    def classify(self, features: np.ndarray, window_full: bool) -> ClassificationResult:
        p = self._last_primary
        if p is None or not window_full:
            return ClassificationResult(label=self._unknown, confidence=0.0, raw_scores=None)
        margin = _score_margin(p.raw_scores)
        lab = (p.label or self._unknown).strip().lower()
        if lab == self._unknown or margin < self._min_margin:
            return ClassificationResult(label=self._unknown, confidence=float(p.confidence), raw_scores=p.raw_scores)
        return ClassificationResult(label=lab, confidence=float(p.confidence), raw_scores=p.raw_scores)


class ExerciseValidator:
    """
    Segunda etapa stateful: compara etiqueta primaria vs teacher y detecta cambios.

    Prioridad de veredicto:
    1. ``changed`` — la etiqueta estable paso de un ejercicio real a otro distinto.
    2. ``confirm`` — teacher y primario coinciden con margen/confianza suficientes.
    3. ``reject`` — teacher discrepa con confianza suficiente.
    4. ``uncertain`` — resto (ventana incompleta, unknown, margen bajo, etc.).
    """

    def __init__(
        self,
        *,
        unknown_label: str = "unknown",
        min_confidence: float = 0.65,
        min_margin: float = 0.12,
        teacher_mode: TeacherMode = "heuristic",
        teacher: _Teacher | None = None,
        change_hold_frames: int = 8,
    ) -> None:
        self._unknown = (unknown_label or "unknown").strip().lower()
        self._min_confidence = float(min_confidence)
        self._min_margin = float(min_margin)
        self._teacher_mode: TeacherMode = teacher_mode
        self._teacher = teacher
        self._change_hold_frames = max(1, int(change_hold_frames))
        self._prev_stable: str | None = None
        self._change_frames_left = 0
        self._change_from: str | None = None

    def reset(self) -> None:
        self._prev_stable = None
        self._change_frames_left = 0
        self._change_from = None

    def validate(
        self,
        features: np.ndarray,
        *,
        window_full: bool,
        primary: ClassificationResult,
    ) -> ExerciseValidationResult:
        primary_label = (primary.label or self._unknown).strip().lower()
        margin = _score_margin(primary.raw_scores)
        instant = _argmax_label(primary.raw_scores)
        teacher_label: str | None = None
        teacher_conf = 0.0

        if not window_full:
            return ExerciseValidationResult(
                verdict="uncertain",
                primary_label=primary_label,
                validator_label=None,
                confidence=float(primary.confidence),
                score_margin=margin,
                reason="window_incomplete",
                previous_label=self._prev_stable,
                teacher_mode=self._teacher_mode,
            )

        # Deteccion de cambio sobre la etiqueta estable del primario (post-histeresis).
        changed_now = False
        if (
            primary_label != self._unknown
            and self._prev_stable is not None
            and self._prev_stable != self._unknown
            and primary_label != self._prev_stable
        ):
            self._change_frames_left = self._change_hold_frames
            self._change_from = self._prev_stable
            changed_now = True

        if primary_label != self._unknown:
            self._prev_stable = primary_label

        teacher_result = self._run_teacher(features, window_full, primary)
        if teacher_result is not None:
            teacher_label = (teacher_result.label or self._unknown).strip().lower()
            teacher_conf = float(teacher_result.confidence)
            if teacher_label == self._unknown:
                teacher_label = None

        if self._change_frames_left > 0:
            self._change_frames_left -= 1
            prev = self._change_from
            if changed_now or self._change_frames_left >= 0:
                return ExerciseValidationResult(
                    verdict="changed",
                    primary_label=primary_label,
                    validator_label=teacher_label or instant,
                    confidence=max(float(primary.confidence), teacher_conf),
                    score_margin=margin,
                    reason=f"label_transition:{prev}->{primary_label}",
                    previous_label=prev,
                    teacher_mode=self._teacher_mode,
                )

        if primary_label == self._unknown:
            return ExerciseValidationResult(
                verdict="uncertain",
                primary_label=primary_label,
                validator_label=teacher_label,
                confidence=float(primary.confidence),
                score_margin=margin,
                reason="primary_unknown",
                previous_label=self._prev_stable,
                teacher_mode=self._teacher_mode,
            )

        primary_ok = float(primary.confidence) >= self._min_confidence and margin >= self._min_margin

        if teacher_label is not None and teacher_label == primary_label and primary_ok:
            if teacher_conf >= self._min_confidence or self._teacher_mode == "margin":
                return ExerciseValidationResult(
                    verdict="confirm",
                    primary_label=primary_label,
                    validator_label=teacher_label,
                    confidence=max(float(primary.confidence), teacher_conf),
                    score_margin=margin,
                    reason="teacher_agrees",
                    previous_label=self._change_from or self._prev_stable,
                    teacher_mode=self._teacher_mode,
                )

        if (
            teacher_label is not None
            and teacher_label != primary_label
            and teacher_conf >= self._min_confidence
            and float(primary.confidence) >= self._min_confidence * 0.85
        ):
            return ExerciseValidationResult(
                verdict="reject",
                primary_label=primary_label,
                validator_label=teacher_label,
                confidence=teacher_conf,
                score_margin=margin,
                reason="teacher_disagrees",
                previous_label=self._prev_stable,
                teacher_mode=self._teacher_mode,
            )

        # Fallback: sin teacher util, confirmar solo por margen del primario.
        if primary_ok and (teacher_label is None or self._teacher_mode == "margin"):
            return ExerciseValidationResult(
                verdict="confirm",
                primary_label=primary_label,
                validator_label=instant or primary_label,
                confidence=float(primary.confidence),
                score_margin=margin,
                reason="margin_ok",
                previous_label=self._prev_stable,
                teacher_mode=self._teacher_mode,
            )

        return ExerciseValidationResult(
            verdict="uncertain",
            primary_label=primary_label,
            validator_label=teacher_label or instant,
            confidence=float(primary.confidence),
            score_margin=margin,
            reason="low_margin_or_confidence",
            previous_label=self._prev_stable,
            teacher_mode=self._teacher_mode,
        )

    def _run_teacher(
        self,
        features: np.ndarray,
        window_full: bool,
        primary: ClassificationResult,
    ) -> ClassificationResult | None:
        t = self._teacher
        if t is None:
            return None
        if isinstance(t, _MarginTeacher):
            t.bind_primary(primary)
        try:
            return t.classify(features, window_full)
        except Exception:  # noqa: BLE001
            log.exception("exercise_validator: fallo del teacher")
            return None


def _try_onnx_teacher(path: Path, cfg: ExerciseClassifierConfig, classes: list[str] | None) -> _Teacher | None:
    try:
        import onnxruntime as ort  # type: ignore[import-untyped]
    except ImportError:
        log.info("onnxruntime no disponible para teacher ONNX")
        return None
    if not path.is_file():
        return None
    try:
        session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo cargar teacher ONNX %s: %s", path, exc)
        return None
    input_name = session.get_inputs()[0].name
    class_list = list(classes) if classes else []

    class _OnnxTeacher:
        def classify(self, features: np.ndarray, window_full: bool) -> ClassificationResult:
            if not window_full:
                return ClassificationResult(label=cfg.unknown_label, confidence=0.0)
            x = features.astype(np.float32).reshape(1, -1)
            outs = session.run(None, {input_name: x})
            prob: np.ndarray | None = None
            label_idx: int | None = None
            for o in outs:
                arr = np.asarray(o)
                flat = arr.reshape(-1)
                if arr.dtype.kind == "f" and flat.size >= 2 and prob is None:
                    if flat.min() >= 0.0 and abs(float(flat.sum()) - 1.0) < 1e-3:
                        prob = flat.astype(np.float64)
                    else:
                        exp = np.exp(flat - np.max(flat))
                        prob = exp / (np.sum(exp) + 1e-9)
                elif arr.dtype.kind in ("i", "u") and flat.size >= 1 and label_idx is None:
                    label_idx = int(flat[0])
            if prob is not None:
                n = len(class_list) if class_list else int(prob.size)
                idx = int(np.argmax(prob[:n]))
                conf = float(prob[idx])
                label = class_list[idx] if class_list and 0 <= idx < len(class_list) else str(idx)
                raw = {
                    (class_list[i] if class_list and i < len(class_list) else str(i)): float(prob[i])
                    for i in range(min(n, prob.size))
                }
                return ClassificationResult(label=label, confidence=conf, raw_scores=raw)
            if label_idx is not None and class_list and 0 <= label_idx < len(class_list):
                return ClassificationResult(label=class_list[label_idx], confidence=1.0)
            return ClassificationResult(label=cfg.unknown_label, confidence=0.0)

    return _OnnxTeacher()


def _resolve_onnx_teacher_path(onnx_path: Path | None) -> Path:
    if onnx_path is not None:
        return Path(onnx_path)
    try:
        from app.paths import backend_root
        from vision.exercise_validator_train import resolve_validator_onnx_path

        return resolve_validator_onnx_path(backend_root())
    except Exception:  # noqa: BLE001
        return Path(__file__).resolve().parent / "models" / "exercise_validator.onnx"


def _resolve_onnx_classes(
    onnx_classes: list[str] | None,
    path: Path,
) -> list[str] | None:
    if onnx_classes:
        return list(onnx_classes)
    try:
        from app.paths import backend_root
        from vision.exercise_validator_train import load_validator_classes

        return load_validator_classes(backend_root(), onnx_path=path)
    except Exception:  # noqa: BLE001
        return None


def build_exercise_validator(
    *,
    enabled: bool,
    unknown_label: str,
    min_confidence: float,
    min_margin: float,
    teacher_mode: str,
    change_hold_frames: int = 8,
    classifier_cfg: ExerciseClassifierConfig | None = None,
    onnx_path: Path | None = None,
    onnx_classes: list[str] | None = None,
) -> ExerciseValidator | None:
    """Factory: ``None`` si el flag esta desactivado.

    ``teacher_mode=auto``: usa ONNX si el artefacto existe; si no, heuristica.
    ``teacher_mode=onnx``: intenta ONNX y cae a heuristica si falta.
    """
    if not enabled:
        return None
    mode_raw = (teacher_mode or "auto").strip().lower()
    if mode_raw not in ("margin", "heuristic", "onnx", "auto"):
        mode_raw = "auto"
    mode: TeacherMode = mode_raw  # type: ignore[assignment]
    cfg = classifier_cfg or ExerciseClassifierConfig(unknown_label=unknown_label)
    teacher: _Teacher | None = None

    path = _resolve_onnx_teacher_path(onnx_path)
    want_onnx = mode in ("onnx", "auto")
    if want_onnx:
        classes = _resolve_onnx_classes(onnx_classes, path)
        if path.is_file():
            teacher = _try_onnx_teacher(path, cfg, classes)
            if teacher is not None:
                mode = "onnx"
                log.info("Teacher ONNX activo: %s (classes=%s)", path, classes)
            else:
                log.warning("Teacher ONNX no cargo (%s); cayendo a heuristic", path)
                mode = "heuristic"
        else:
            if mode_raw == "onnx":
                log.warning("Teacher ONNX no encontrado en %s; cayendo a heuristic", path)
            mode = "heuristic"

    if mode == "heuristic":
        from vision.heuristic_exercise_classifier import HeuristicExerciseClassifier

        teacher = HeuristicExerciseClassifier(cfg)
    elif mode == "margin":
        teacher = _MarginTeacher(min_margin=min_margin, unknown=unknown_label)

    return ExerciseValidator(
        unknown_label=unknown_label,
        min_confidence=min_confidence,
        min_margin=min_margin,
        teacher_mode=mode if mode != "auto" else "heuristic",
        teacher=teacher,
        change_hold_frames=change_hold_frames,
    )
