# ARCH-2: feature_engine.py — Capa 2, ventana temporal (ver docs/bio_motion_plan_v2.md §2.1)
"""Buffer deslizante y vector de features simple para el clasificador."""

from __future__ import annotations

import math
from collections import deque
import numpy as np

from app.models.schemas import ExerciseClassifierConfig
from vision.types import PoseFrame


def _knee_flex_pair(pose: PoseFrame) -> tuple[float, float]:
    if not pose.knees:
        return float("nan"), float("nan")
    lf = pose.knees.get("left_knee_flexion_angle_deg")
    rf = pose.knees.get("right_knee_flexion_angle_deg")
    try:
        l = float(lf) if lf is not None else float("nan")
    except (TypeError, ValueError):
        l = float("nan")
    try:
        r = float(rf) if rf is not None else float("nan")
    except (TypeError, ValueError):
        r = float("nan")
    return l, r


class FeatureEngine:
    """Mantiene una ventana de :class:`PoseFrame` y expone un vector numérico fijo."""

    def __init__(self, cfg: ExerciseClassifierConfig) -> None:
        self._cfg = cfg
        self._window: deque[PoseFrame] = deque(maxlen=max(2, cfg.window_size_frames))

    def push(self, pose: PoseFrame) -> None:
        self._window.append(pose)

    def reset(self) -> None:
        self._window.clear()

    def build_feature_vector(self) -> np.ndarray:
        """Vector 1D float32 para ONNX / modelos; usa rodillas y disponibilidad de pose."""
        if not self._window:
            return np.zeros(16, dtype=np.float32)

        poses = list(self._window)
        flex_l = np.array([_knee_flex_pair(p)[0] for p in poses], dtype=np.float64)
        flex_r = np.array([_knee_flex_pair(p)[1] for p in poses], dtype=np.float64)

        def _safe_stats(a: np.ndarray) -> tuple[float, float, float, float]:
            m = np.nanmean(a)
            if math.isnan(m):
                return 0.0, 0.0, 0.0, 0.0
            s = float(np.nanstd(a))
            mn = float(np.nanmin(a))
            mx = float(np.nanmax(a))
            return float(m), s, mn, mx

        ml, sl, min_l, max_l = _safe_stats(flex_l)
        mr, sr, min_r, max_r = _safe_stats(flex_r)
        pose_ok_ratio = float(sum(1 for p in poses if p.ok and p.landmarks) / len(poses))

        # último frame vs media (proxy de velocidad / tendencia)
        last_l, last_r = _knee_flex_pair(poses[-1])
        dl = 0.0 if math.isnan(last_l) or math.isnan(ml) else float(last_l - ml)
        dr = 0.0 if math.isnan(last_r) or math.isnan(mr) else float(last_r - mr)

        vec = np.array(
            [
                ml,
                mr,
                sl,
                sr,
                min_l,
                max_l,
                min_r,
                max_r,
                dl,
                dr,
                float(len(poses)),
                pose_ok_ratio,
                abs(ml - mr),
                max_l - min_l,
                max_r - min_r,
                0.0,  # reservado p. ej. periodicidad / FFT en Fase 3
            ],
            dtype=np.float32,
        )
        return vec

    def window_full(self) -> bool:
        return len(self._window) >= self._cfg.window_size_frames
