# ARCH-3: exercise_classifier.py — Capa 3 + ExerciseClassifierConfig (ver docs/bio_motion_plan_v2.md §2.4)
"""Clasificación de ejercicio con umbral, histéresis y suavizado EMA (Fase 3 / ARCH-T14)."""

from __future__ import annotations

import logging
from typing import Protocol

import numpy as np

from app.models.schemas import ExerciseClassifierConfig
from vision.model_registry import ExerciseModelManifest, ModelRegistry
from vision.scalar_kalman import ScalarKalman1D
from vision.types import ClassificationResult

log = logging.getLogger(__name__)


class ExerciseClassifier(Protocol):
    """Interfaz del clasificador (stub u ONNX)."""

    def classify(self, features: np.ndarray, window_full: bool) -> ClassificationResult: ...


class NopExerciseClassifier:
    """Fase 1: siempre ``unknown`` con confianza 0."""

    def __init__(self, cfg: ExerciseClassifierConfig) -> None:
        self._cfg = cfg

    def classify(self, features: np.ndarray, window_full: bool) -> ClassificationResult:
        return ClassificationResult(label=self._cfg.unknown_label, confidence=0.0, raw_scores=None)


class HysteresisClassifier:
    """Envuelve un clasificador base: umbral mínimo + frames estables para cambiar etiqueta."""

    def __init__(self, inner: ExerciseClassifier, cfg: ExerciseClassifierConfig) -> None:
        self._inner = inner
        self._cfg = cfg
        self._stable_label = cfg.unknown_label
        self._candidate: str | None = None
        self._candidate_frames = 0
        self._ema_confidence = 0.0
        self._kalman = ScalarKalman1D(cfg.kalman_process_noise, cfg.kalman_measurement_noise)

    def reset(self) -> None:
        self._stable_label = self._cfg.unknown_label
        self._candidate = None
        self._candidate_frames = 0
        self._ema_confidence = 0.0
        self._kalman.reset()

    def classify(self, features: np.ndarray, window_full: bool) -> ClassificationResult:
        raw = self._inner.classify(features, window_full)
        conf = float(raw.confidence)
        if self._cfg.confidence_filter == "kalman":
            eff_conf = self._kalman.update(conf)
        else:
            alpha = self._cfg.confidence_ema_alpha
            self._ema_confidence = alpha * conf + (1.0 - alpha) * self._ema_confidence
            eff_conf = self._ema_confidence

        label = raw.label

        if not window_full:
            return ClassificationResult(label=self._cfg.unknown_label, confidence=eff_conf, raw_scores=raw.raw_scores)

        if eff_conf < self._cfg.min_confidence or label == self._cfg.unknown_label:
            new_label = self._cfg.unknown_label
        else:
            new_label = label

        if new_label == self._stable_label:
            self._candidate = None
            self._candidate_frames = 0
        else:
            if self._candidate != new_label:
                self._candidate = new_label
                self._candidate_frames = 1
            else:
                self._candidate_frames += 1
            if self._candidate_frames >= self._cfg.hysteresis_frames:
                self._stable_label = new_label
                self._candidate = None
                self._candidate_frames = 0

        out_label = self._stable_label
        if out_label == self._cfg.unknown_label:
            return ClassificationResult(label=out_label, confidence=eff_conf, raw_scores=raw.raw_scores)
        return ClassificationResult(label=out_label, confidence=eff_conf, raw_scores=raw.raw_scores)


def build_classifier(
    cfg: ExerciseClassifierConfig,
    registry: ModelRegistry,
) -> HysteresisClassifier:
    """Construye clasificador según manifest; sin ONNX válido usa :class:`NopExerciseClassifier`."""
    from app.config import settings

    inner: ExerciseClassifier = NopExerciseClassifier(cfg)
    flags = settings.feature_flags()
    if flags.get("enable_onnx_classifier", True):
        try:
            manifest = registry.load_active_manifest()
            if manifest is not None:
                onnx = _try_onnx_classifier(manifest, cfg)
                if onnx is not None:
                    inner = onnx
        except Exception as exc:  # noqa: BLE001
            log.warning("Clasificador ONNX no disponible, usando stub: %s", exc)
    return HysteresisClassifier(inner, cfg)


def _try_onnx_classifier(manifest: ExerciseModelManifest, cfg: ExerciseClassifierConfig) -> ExerciseClassifier | None:
    try:
        import onnxruntime as ort  # type: ignore[import-untyped]
    except ImportError:
        log.info("onnxruntime no instalado; clasificador permanece en stub")
        return None

    from pathlib import Path

    path = Path(manifest.path)
    if not path.is_file():
        log.warning("Modelo ONNX no encontrado: %s", path)
        return None

    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    classes = list(manifest.classes) or [cfg.unknown_label]

    class _OnnxCls:
        def __init__(self) -> None:
            self._session = session
            self._input_name = input_name
            self._classes = classes

        def classify(self, features: np.ndarray, window_full: bool) -> ClassificationResult:
            x = features.astype(np.float32).reshape(1, -1)
            out = self._session.run(None, {self._input_name: x})
            logits = np.asarray(out[0]).reshape(-1)
            if logits.size == 0:
                return ClassificationResult(label=cfg.unknown_label, confidence=0.0)
            exp = np.exp(logits - np.max(logits))
            prob = exp / (np.sum(exp) + 1e-9)
            idx = int(np.argmax(prob))
            label = self._classes[idx] if idx < len(self._classes) else cfg.unknown_label
            confidence = float(prob[idx])
            raw = {self._classes[i]: float(prob[i]) for i in range(min(len(self._classes), prob.size))}
            return ClassificationResult(label=label, confidence=confidence, raw_scores=raw)

    return _OnnxCls()

