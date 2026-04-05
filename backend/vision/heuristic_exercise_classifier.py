# Fase A: clasificación por reglas sobre el vector 32D de FeatureEngine (sin ONNX).
"""Ver ``feature_engine.FeatureEngine.build_feature_vector`` para el orden de componentes."""

from __future__ import annotations

import math

import numpy as np

from app.models.schemas import ExerciseClassifierConfig
from vision.types import ClassificationResult

# Índices alineados con FeatureEngine.build_feature_vector (primer bloque antes del padding)
IDX_MEAN_L = 0
IDX_MEAN_R = 1
IDX_ASYM = 12
IDX_ROM_L = 13
IDX_ROM_R = 14
IDX_PERIODICITY = 15


def _sigmoid(x: float) -> float:
    try:
        return float(1.0 / (1.0 + math.exp(-x)))
    except OverflowError:
        return 1.0 if x > 0 else 0.0


class HeuristicExerciseClassifier:
    """
    Puntuaciones suaves por clase (idle / squat / lunge) y softmax como pseudo-confianza.
    Pensado para ventana llena; si ``window_full`` es False devuelve unknown.
    """

    def __init__(self, cfg: ExerciseClassifierConfig) -> None:
        self._cfg = cfg
        self._classes: tuple[str, ...] = ("idle", "squat", "lunge")

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

        knee_mean = 0.5 * (ml + mr)
        rom_mean = 0.5 * (rom_l + rom_r)

        # idle: poca flexión media, baja periodicidad, asimetría moderada
        idle_knee = _sigmoid((38.0 - knee_mean) / 10.0)
        idle_per = _sigmoid((0.13 - per) / 0.05)
        idle_asym = _sigmoid((24.0 - asym) / 7.0)
        s_idle = 0.45 * idle_knee + 0.35 * idle_per + 0.20 * idle_asym

        # squat: profundidad y/o ROM de ventana, periodicidad, relativamente bilateral
        sq_depth = _sigmoid((knee_mean - 48.0) / 14.0)
        sq_rom = _sigmoid((rom_mean - 22.0) / 18.0)
        sq_per = _sigmoid((per - 0.05) / 0.07)
        sq_sym = _sigmoid((30.0 - asym) / 12.0)
        s_squat = 0.30 * sq_depth + 0.25 * sq_rom + 0.30 * sq_per + 0.15 * sq_sym

        # lunge: alta asimetría + flexión moderada (patrón unilateral)
        lg_asym = _sigmoid((asym - 16.0) / 9.0)
        lg_depth = _sigmoid((knee_mean - 40.0) / 12.0)
        s_lunge = 0.58 * lg_asym + 0.42 * lg_depth

        raw = {"idle": s_idle, "squat": s_squat, "lunge": s_lunge}
        m = max(raw.values())
        exps = {k: math.exp(v - m) for k, v in raw.items()}
        z = sum(exps.values()) + 1e-9
        prob = {k: exps[k] / z for k in exps}
        best = max(prob, key=prob.get)
        confidence = float(prob[best])
        return ClassificationResult(
            label=best,
            confidence=confidence,
            raw_scores={k: float(prob[k]) for k in self._classes},
        )
