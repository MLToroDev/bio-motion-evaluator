# ARCH-3: exercise_classifier.py — Capa 3 + ExerciseClassifierConfig (ver docs/planificacion/bio_motion_plan_v2.md §2.4)
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
        self._unknown_streak = 0
        # Un curl unilateral en extensión o un squat en lockout parece idle 1–2 s.
        self._unknown_hold = max(24, int(cfg.hysteresis_frames) * 3)
        self._ema_confidence = 0.0
        self._kalman = ScalarKalman1D(cfg.kalman_process_noise, cfg.kalman_measurement_noise)

    def reset(self) -> None:
        self._stable_label = self._cfg.unknown_label
        self._candidate = None
        self._candidate_frames = 0
        self._unknown_streak = 0
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
            self._unknown_streak = 0
        elif new_label == self._cfg.unknown_label and self._stable_label != self._cfg.unknown_label:
            self._candidate = None
            self._candidate_frames = 0
            self._unknown_streak += 1
            if self._unknown_streak >= self._unknown_hold:
                self._stable_label = self._cfg.unknown_label
                self._unknown_streak = 0
        else:
            self._unknown_streak = 0
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
    """
    Por defecto: :class:`HeuristicExerciseClassifier` (Fase A, reglas sobre vector 32D).
    Si hay manifest activo y archivo ONNX válido y ``enable_onnx_classifier`` es True,
    se usa ONNX. Flag ``use_nop_classifier: true`` en feature_flags fuerza stub ``unknown``.
    """
    from app.config import settings

    from vision.heuristic_exercise_classifier import HeuristicExerciseClassifier

    flags = settings.feature_flags()
    if flags.get("use_nop_classifier", False):
        inner: ExerciseClassifier = NopExerciseClassifier(cfg)
    else:
        inner: ExerciseClassifier = HeuristicExerciseClassifier(cfg)
    if flags.get("enable_onnx_classifier", True):
        try:
            manifest = registry.load_active_manifest()
            if manifest is not None:
                onnx = _try_onnx_classifier(manifest, cfg)
                if onnx is not None:
                    inner = onnx
        except Exception as exc:  # noqa: BLE001
            log.warning("Clasificador ONNX no disponible, usando heurístico: %s", exc)
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
            outs = self._session.run(None, {self._input_name: x})

            # skl2onnx (zipmap=False) emite [output_label int64, output_probability float];
            # el stub de logits emite un único tensor float [1, n_classes]. Elegir el tensor
            # float con tantas columnas como clases; usar out[0] a ciegas confunde la etiqueta
            # entera con logits (argmax de 1 elemento => siempre clase 0).
            prob: np.ndarray | None = None
            label_idx: int | None = None
            for o in outs:
                arr = np.asarray(o)
                flat = arr.reshape(-1)
                if arr.dtype.kind == "f" and flat.size == len(self._classes) and prob is None:
                    if flat.min() >= 0.0 and abs(float(flat.sum()) - 1.0) < 1e-3:
                        prob = flat.astype(np.float64)
                    else:
                        exp = np.exp(flat - np.max(flat))
                        prob = exp / (np.sum(exp) + 1e-9)
                elif arr.dtype.kind in ("i", "u") and flat.size >= 1 and label_idx is None:
                    label_idx = int(flat[0])

            if prob is not None:
                idx = int(np.argmax(prob))
                confidence = float(prob[idx])
                raw = {self._classes[i]: float(prob[i]) for i in range(min(len(self._classes), prob.size))}
            elif label_idx is not None:
                idx = label_idx
                confidence = 1.0
                raw = None
            else:
                return ClassificationResult(label=cfg.unknown_label, confidence=0.0)

            label = self._classes[idx] if 0 <= idx < len(self._classes) else cfg.unknown_label
            return ClassificationResult(label=label, confidence=confidence, raw_scores=raw)

    return _OnnxWithCurlRescue(_OnnxCls(), cfg)


class _OnnxWithCurlRescue:
    """
    Rescate de curl (sentado / unilateral): el RF activo se entrenó con curls de pie
    bilaterales y el vector 32D está dominado por rodilla (0–20). Enter/hold evita
    soltar ``curl`` en la extensión (codo lento un instante).
    """

    def __init__(self, inner: ExerciseClassifier, cfg: ExerciseClassifierConfig) -> None:
        self._inner = inner
        self._cfg = cfg
        self._holding_curl = False

    def classify(self, features: np.ndarray, window_full: bool) -> ClassificationResult:
        from vision.heuristic_exercise_classifier import (
            CURL_ISOLATION_HOLD,
            CURL_ISOLATION_MIN,
            curl_isolation_score,
        )

        raw = self._inner.classify(features, window_full)
        if not window_full or features.size < 32:
            self._holding_curl = False
            return raw
        s_curl = curl_isolation_score(features)
        gate = CURL_ISOLATION_HOLD if self._holding_curl else CURL_ISOLATION_MIN
        if s_curl < gate:
            self._holding_curl = False
            return raw
        lab = (raw.label or self._cfg.unknown_label).strip().lower()
        conf = float(raw.confidence)
        if lab == "curl" and conf >= self._cfg.min_confidence:
            self._holding_curl = True
            return raw
        scores = dict(raw.raw_scores or {})
        scores["curl"] = max(float(scores.get("curl", 0.0)), s_curl)
        rescued_conf = max(conf, float(self._cfg.min_confidence), min(0.95, 0.55 + 0.45 * s_curl))
        self._holding_curl = True
        return ClassificationResult(label="curl", confidence=rescued_conf, raw_scores=scores or None)


