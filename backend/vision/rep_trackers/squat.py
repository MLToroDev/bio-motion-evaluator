# ARCH-T12: RepTracker concreto — sentadilla, ahora como configuración de ThresholdCycleTracker.
from __future__ import annotations

from vision.rep_trackers.threshold_cycle import (
    ThresholdCycleTracker,
    bilateral_knee_flexion,
    knee_flexion_pair,
)


class SquatRepTracker(ThresholdCycleTracker):
    """
    Rep de sentadilla: extendido → flexión profunda → extendido, sobre el promedio
    bilateral de flexión de rodilla. En squat la señal sube durante la bajada,
    por lo que la fase de ida es excéntrica y la de vuelta concéntrica.

    Umbrales (grados de flexión): entrar en bajada 55, fondo mínimo 80 (alineado con
    Wan Izzul & Kumaresan 2026, JIWE: flexión ~80–100° «buena»; ver vision/biomechanics.py),
    retroceso de pico 8, vuelta a extendido 35. Flags: ``asymmetry_high`` (>18 %),
    ``rom_low`` (pico < fondo − 8).
    """

    def __init__(self) -> None:
        super().__init__(
            signal_fn=bilateral_knee_flexion,
            enter_threshold=55.0,
            bottom_threshold=80.0,
            peak_drop=8.0,
            exit_threshold=35.0,
            rising_phase="eccentric",
            falling_phase="concentric",
            pair_fn=knee_flexion_pair,
            asymmetry_flag_pct=18.0,
            rom_low_margin=8.0,
        )
