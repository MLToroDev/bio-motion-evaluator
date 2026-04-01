# ARCH-T12: RepTracker concreto — sentadilla (rodilla); máquina de estados simple.
from __future__ import annotations

import math
from typing import Literal

from vision.rep_tracker_abc import RepTracker
from vision.types import FeatureFrame, RepPhase, RepState

Phase = Literal["idle", "eccentric", "concentric", "hold"]

# Flexión alta ≈ fondo de sentadilla; baja ≈ extensión (valores según biomechanics.py)


class SquatRepTracker(RepTracker):
    """
    Heurística de rep: transición extendido → flexión profunda → extendido.
    Usa promedio bilateral de flexión de rodilla cuando ambas existen.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._phase: Phase = "idle"
        self._rep_count = 0
        self._flex_peak = 0.0
        self._flags: list[str] = []

    def _avg_flex(self, frame: FeatureFrame) -> float | None:
        k = frame.pose.knees
        if not k:
            return None
        try:
            l = k.get("left_knee_flexion_angle_deg")
            r = k.get("right_knee_flexion_angle_deg")
            vals = [float(v) for v in (l, r) if v is not None and not math.isnan(float(v))]
            if not vals:
                return None
            return sum(vals) / len(vals)
        except (TypeError, ValueError):
            return None

    def update(self, frame: FeatureFrame) -> RepState:
        self._flags = []
        flex = self._avg_flex(frame)
        if flex is None or not frame.pose.ok:
            self._phase = "idle"
            return RepState(rep_phase="idle", rep_count=self._rep_count, quality_flags=list(self._flags))

        # Asimetría
        k = frame.pose.knees or {}
        try:
            l = float(k.get("left_knee_flexion_angle_deg", float("nan")))
            r = float(k.get("right_knee_flexion_angle_deg", float("nan")))
            if not math.isnan(l) and not math.isnan(r):
                asym = abs(l - r) / max(l, r, 1.0) * 100.0
                if asym > 18.0:
                    self._flags.append("asymmetry_high")
        except (TypeError, ValueError):
            pass

        down_enter = 55.0  # entrar en bajada
        up_exit = 35.0  # vuelta a extendido
        bottom = 75.0  # mínimo flex para contar rep

        if self._phase in ("idle", "hold"):
            if flex >= down_enter:
                self._phase = "eccentric"
                self._flex_peak = flex
        elif self._phase == "eccentric":
            self._flex_peak = max(self._flex_peak, flex)
            if self._flex_peak >= bottom and flex < self._flex_peak - 8.0:
                self._phase = "concentric"
        elif self._phase == "concentric":
            if flex <= up_exit:
                self._rep_count += 1
                self._phase = "idle"

        rpc: RepPhase = self._phase if self._phase != "hold" else "hold"

        # ROM bajo si nunca llegamos a fondo en la fase actual
        if self._phase == "eccentric" and self._flex_peak < bottom - 10.0:
            self._flags.append("rom_low")

        return RepState(rep_phase=rpc, rep_count=self._rep_count, quality_flags=list(self._flags))

