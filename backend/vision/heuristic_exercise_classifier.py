# Fase A: clasificación por reglas sobre el vector 32D de FeatureEngine (sin ONNX).
"""Ver ``feature_engine.FeatureEngine.build_feature_vector`` para el orden de componentes."""

from __future__ import annotations

import math

import numpy as np

from app.models.schemas import ExerciseClassifierConfig
from vision.types import ClassificationResult

# Índices alineados con FeatureEngine.build_feature_vector (ver docs/spec/feature-vector-32d.md)
IDX_MEAN_L = 0
IDX_MEAN_R = 1
IDX_ASYM = 12
IDX_ROM_L = 13
IDX_ROM_R = 14
IDX_PERIODICITY = 15
IDX_TRUNK_MEAN = 21
IDX_BASE_RATIO = 23
IDX_WRIST_L = 27
IDX_WRIST_R = 28
IDX_KNEE_SPEED_MEAN = 29
IDX_KNEE_SPEED_MAX = 30
IDX_ELBOW_SPEED_MAX = 31

# Umbral de aislamiento codo vs rodilla: curl sentado/de pie (no squat, no push-up).
# Enter / hold: en la extensión del curl unilateral la velocidad de codo cae; el hold
# evita soltar la etiqueta a mitad de serie.
CURL_ISOLATION_MIN = 0.55
CURL_ISOLATION_HOLD = 0.38


def _sigmoid(x: float) -> float:
    try:
        return float(1.0 / (1.0 + math.exp(-x)))
    except OverflowError:
        return 1.0 if x > 0 else 0.0


def curl_isolation_score(features: np.ndarray) -> float:
    """
    Puntuación 0–1 de curl de bíceps (de pie o sentado).

    Señal: codo rápido (F5), rodillas casi estáticas (ROM/velocidad bajas), tronco
    erguido (no push-up) y muñecas en rango torso–hombro (no press overhead).
    Un curl sentado deja las rodillas ~90° fijas: sin este score el ONNX lo confunde
    con squat porque los índices 0–20 están dominados por flexión de rodilla.
    """
    if features.size < 32:
        return 0.0
    rom_mean = 0.5 * (float(features[IDX_ROM_L]) + float(features[IDX_ROM_R]))
    trunk = float(features[IDX_TRUNK_MEAN])
    wrist = max(float(features[IDX_WRIST_L]), float(features[IDX_WRIST_R]))
    knee_spd = max(float(features[IDX_KNEE_SPEED_MEAN]), float(features[IDX_KNEE_SPEED_MAX]))
    elbow_spd = float(features[IDX_ELBOW_SPEED_MAX])

    s_elbow = _sigmoid((elbow_spd - 22.0) / 20.0)
    s_knee_still = _sigmoid((16.0 - rom_mean) / 8.0)
    s_knee_slow = _sigmoid((28.0 - knee_spd) / 12.0)
    # Compuerta de tronco: push-up/plancha (F1 alto) no es curl aunque el codo se mueva.
    s_trunk_gate = _sigmoid((35.0 - trunk) / 8.0) if trunk > 0.0 else 0.70
    # Muñeca relativa: 0 = cadera, 1 = hombro. Curl a un brazo: usar el lado más alto.
    s_wrist = _sigmoid((wrist - 0.12) / 0.12) * _sigmoid((1.20 - wrist) / 0.14)
    s_elbow_vs_knee = _sigmoid((elbow_spd - knee_spd - 15.0) / 18.0)
    base = (
        0.34 * s_elbow
        + 0.22 * s_knee_still
        + 0.16 * s_knee_slow
        + 0.16 * s_wrist
        + 0.12 * s_elbow_vs_knee
    )
    return float(base * s_trunk_gate)


class HeuristicExerciseClassifier:
    """
    Puntuaciones suaves por clase (idle / squat / lunge / curl) y softmax como pseudo-confianza.
    Pensado para ventana llena; si ``window_full`` es False devuelve unknown.
    """

    def __init__(self, cfg: ExerciseClassifierConfig) -> None:
        self._cfg = cfg
        self._classes: tuple[str, ...] = ("idle", "squat", "lunge", "curl")

    def classify(self, features: np.ndarray, window_full: bool) -> ClassificationResult:
        unk = self._cfg.unknown_label
        if not window_full or features.size < 16:
            return ClassificationResult(label=unk, confidence=0.0, raw_scores=None)

        ml = float(features[IDX_MEAN_L])
        mr = float(features[IDX_MEAN_R])
        asym = float(features[IDX_ASYM])
        rom_l = float(features[IDX_ROM_L])
        rom_r = float(features[IDX_ROM_R])
        per = float(features[IDX_PERIODICITY])
        trunk_mean = float(features[IDX_TRUNK_MEAN]) if features.size > IDX_TRUNK_MEAN else 0.0
        base_ratio = float(features[IDX_BASE_RATIO]) if features.size > IDX_BASE_RATIO else 0.0

        knee_mean = 0.5 * (ml + mr)
        rom_mean = 0.5 * (rom_l + rom_r)
        s_curl = curl_isolation_score(features) if features.size >= 32 else 0.0

        # idle: poca flexión media, baja periodicidad, asimetría moderada
        idle_knee = _sigmoid((38.0 - knee_mean) / 10.0)
        idle_per = _sigmoid((0.13 - per) / 0.05)
        idle_asym = _sigmoid((24.0 - asym) / 7.0)
        s_idle = 0.45 * idle_knee + 0.35 * idle_per + 0.20 * idle_asym
        # Sentado con brazos activos no es idle: la flexión de rodilla alta + codo rápido lo baja.
        s_idle *= 1.0 - 0.55 * s_curl

        # squat: profundidad Y ROM cíclico de rodilla. Rodillas fijas ~90° (sentado) no son squat.
        sq_depth = _sigmoid((knee_mean - 48.0) / 14.0)
        sq_rom = _sigmoid((rom_mean - 22.0) / 18.0)
        sq_per = _sigmoid((per - 0.05) / 0.07)
        sq_sym = _sigmoid((30.0 - asym) / 12.0)
        sq_trunk = _sigmoid((trunk_mean - 12.0) / 8.0) if trunk_mean > 0.0 else 0.5
        s_squat = (
            0.18 * sq_depth + 0.38 * sq_rom + 0.24 * sq_per + 0.12 * sq_sym + 0.08 * sq_trunk
        )
        s_squat *= sq_rom

        # lunge: alta asimetría + flexión moderada (patrón unilateral) + base de apoyo
        lg_asym = _sigmoid((asym - 16.0) / 9.0)
        lg_depth = _sigmoid((knee_mean - 40.0) / 12.0)
        lg_base = _sigmoid((base_ratio - 2.4) / 0.6) if base_ratio > 0.0 else 0.5
        s_lunge = 0.50 * lg_asym + 0.38 * lg_depth + 0.12 * lg_base
        s_lunge *= 1.0 - 0.45 * s_curl

        raw = {"idle": s_idle, "squat": s_squat, "lunge": s_lunge, "curl": s_curl}
        m = max(raw.values())
        exps = {k: math.exp(v - m) for k, v in raw.items()}
        z = sum(exps.values()) + 1e-9
        prob = {k: exps[k] / z for k in exps}
        best = max(prob, key=prob.get)
        confidence = float(prob[best])
        # Evitar que el softmax de 4 clases diluya un curl claro por debajo del umbral ONNX (0.72).
        if s_curl >= CURL_ISOLATION_MIN and s_curl >= max(s_idle, s_squat, s_lunge):
            best = "curl"
            confidence = max(
                confidence,
                float(self._cfg.min_confidence),
                min(0.95, 0.55 + 0.45 * s_curl),
            )
        return ClassificationResult(
            label=best,
            confidence=confidence,
            raw_scores={k: float(prob[k]) for k in self._classes},
        )
