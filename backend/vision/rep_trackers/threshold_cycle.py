# FSM genérica de repeticiones por umbrales sobre una señal escalar (generaliza ARCH-T12).
"""
Ciclo: señal sube >= ``enter_threshold`` (fase de ida) → pico >= ``bottom_threshold``
y retrocede ``peak_drop`` (fase de vuelta) → señal <= ``exit_threshold`` (+1 rep).

La semántica concéntrica/excéntrica depende del ejercicio: en sentadilla la señal
(flexión de rodilla) sube durante la bajada (excéntrica); en curl la flexión de codo
sube durante la subida (concéntrica). Por eso las fases de ida/vuelta son parámetros.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Literal

from vision.rep_tracker_abc import RepTracker
from vision.types import FeatureFrame, RepPhase, RepState

_InternalPhase = Literal["idle", "rising", "falling", "hold"]

# Señal escalar del frame (None si no computable) y par L/R opcional para flag de asimetría.
SignalFn = Callable[[FeatureFrame], float | None]
PairFn = Callable[[FeatureFrame], tuple[float, float] | None]


class ThresholdCycleTracker(RepTracker):
    """FSM de 3 umbrales + retroceso de pico, parametrizable por señal y fases."""

    def __init__(
        self,
        *,
        signal_fn: SignalFn,
        enter_threshold: float,
        bottom_threshold: float,
        peak_drop: float,
        exit_threshold: float,
        rising_phase: RepPhase = "eccentric",
        falling_phase: RepPhase = "concentric",
        pair_fn: PairFn | None = None,
        asymmetry_flag_pct: float = 18.0,
        rom_low_margin: float = 8.0,
    ) -> None:
        self._signal_fn = signal_fn
        self._enter = float(enter_threshold)
        self._bottom = float(bottom_threshold)
        self._drop = float(peak_drop)
        self._exit = float(exit_threshold)
        self._rising_phase = rising_phase
        self._falling_phase = falling_phase
        self._pair_fn = pair_fn
        self._asym_pct = float(asymmetry_flag_pct)
        self._rom_low_margin = float(rom_low_margin)
        self.reset()

    def reset(self) -> None:
        self._phase: _InternalPhase = "idle"
        self._rep_count = 0
        self._peak = 0.0
        self._flags: list[str] = []

    def _public_phase(self) -> RepPhase:
        if self._phase == "rising":
            return self._rising_phase
        if self._phase == "falling":
            return self._falling_phase
        return "hold" if self._phase == "hold" else "idle"

    def update(self, frame: FeatureFrame) -> RepState:
        self._flags = []
        sig = self._signal_fn(frame)
        if sig is None or not frame.pose.ok:
            self._phase = "idle"
            return RepState(rep_phase="idle", rep_count=self._rep_count, quality_flags=list(self._flags))

        if self._pair_fn is not None:
            pair = self._pair_fn(frame)
            if pair is not None:
                l, r = pair
                if not math.isnan(l) and not math.isnan(r):
                    asym = abs(l - r) / max(l, r, 1.0) * 100.0
                    if asym > self._asym_pct:
                        self._flags.append("asymmetry_high")

        if self._phase in ("idle", "hold"):
            if sig >= self._enter:
                self._phase = "rising"
                self._peak = sig
        elif self._phase == "rising":
            self._peak = max(self._peak, sig)
            if self._peak >= self._bottom and sig < self._peak - self._drop:
                self._phase = "falling"
        elif self._phase == "falling":
            if sig <= self._exit:
                self._rep_count += 1
                self._phase = "idle"

        if self._phase == "rising" and self._peak < self._bottom - self._rom_low_margin:
            self._flags.append("rom_low")

        return RepState(
            rep_phase=self._public_phase(),
            rep_count=self._rep_count,
            quality_flags=list(self._flags),
        )


def bilateral_knee_flexion(frame: FeatureFrame) -> float | None:
    """Promedio bilateral de flexión de rodilla (grados) desde ``pose.knees``."""
    k = frame.pose.knees
    if not k:
        return None
    try:
        vals = [
            float(v)
            for v in (k.get("left_knee_flexion_angle_deg"), k.get("right_knee_flexion_angle_deg"))
            if v is not None and not math.isnan(float(v))
        ]
    except (TypeError, ValueError):
        return None
    return sum(vals) / len(vals) if vals else None


def knee_flexion_pair(frame: FeatureFrame) -> tuple[float, float] | None:
    k = frame.pose.knees or {}
    try:
        l = float(k.get("left_knee_flexion_angle_deg", float("nan")))
        r = float(k.get("right_knee_flexion_angle_deg", float("nan")))
    except (TypeError, ValueError):
        return None
    return (l, r)


def bilateral_elbow_flexion(frame: FeatureFrame) -> float | None:
    """Promedio bilateral de flexión de codo (grados) calculado desde landmarks."""
    pair = elbow_flexion_pair(frame)
    if pair is None:
        return None
    vals = [v for v in pair if not math.isnan(v)]
    return sum(vals) / len(vals) if vals else None


def dominant_elbow_flexion(frame: FeatureFrame) -> float | None:
    """
    Flexión del codo más activo (máximo L/R).

    Un curl unilateral (mancuerna sentado, un brazo a la vez) diluye el promedio
    bilateral: el brazo quieto ~0° anula el que flexiona y la FSM no cierra reps.
    """
    pair = elbow_flexion_pair(frame)
    if pair is None:
        return None
    vals = [v for v in pair if not math.isnan(v)]
    return max(vals) if vals else None


def elbow_flexion_pair(frame: FeatureFrame) -> tuple[float, float] | None:
    if not frame.pose.landmarks:
        return None
    from vision.biomechanics import elbow_flex_angles_from_landmarks

    angles = elbow_flex_angles_from_landmarks(frame.pose.landmarks)
    try:
        return (
            float(angles.get("left_elbow_flexion_angle_deg", float("nan"))),
            float(angles.get("right_elbow_flexion_angle_deg", float("nan"))),
        )
    except (TypeError, ValueError):
        return None


def hip_flexion_pair(frame: FeatureFrame) -> tuple[float, float] | None:
    """Flexión de cadera L/R (grados) desde landmarks, para trackers tipo hip-hinge (F3)."""
    if not frame.pose.landmarks:
        return None
    from vision.biomechanics import hip_flexion_angles_from_landmarks

    angles = hip_flexion_angles_from_landmarks(frame.pose.landmarks)
    try:
        return (
            float(angles.get("left_hip_flexion_angle_deg", float("nan"))),
            float(angles.get("right_hip_flexion_angle_deg", float("nan"))),
        )
    except (TypeError, ValueError):
        return None


def bilateral_hip_flexion(frame: FeatureFrame) -> float | None:
    """Promedio bilateral de flexión de cadera (grados), señal de bisagra de cadera (deadlift)."""
    pair = hip_flexion_pair(frame)
    if pair is None:
        return None
    vals = [v for v in pair if not math.isnan(v)]
    return sum(vals) / len(vals) if vals else None


def wrist_height_pair(frame: FeatureFrame) -> tuple[float, float] | None:
    """Altura de muñeca L/R relativa al torso (F4), para trackers de brazos por encima de hombros."""
    if not frame.pose.landmarks:
        return None
    from vision.biomechanics import wrist_relative_heights

    heights = wrist_relative_heights(frame.pose.landmarks)
    try:
        return (
            float(heights.get("left_wrist_relative_height", float("nan"))),
            float(heights.get("right_wrist_relative_height", float("nan"))),
        )
    except (TypeError, ValueError):
        return None


def bilateral_wrist_height(frame: FeatureFrame) -> float | None:
    """Promedio bilateral de altura relativa de muñecas (0 = cadera, 1 = hombro, >1 = overhead)."""
    pair = wrist_height_pair(frame)
    if pair is None:
        return None
    vals = [v for v in pair if not math.isnan(v)]
    return sum(vals) / len(vals) if vals else None
