# RepTracker de flexión de pecho (push-up) sobre la FSM genérica ThresholdCycleTracker.
from __future__ import annotations

from vision.rep_trackers.threshold_cycle import (
    ThresholdCycleTracker,
    bilateral_elbow_flexion,
    elbow_flexion_pair,
)


class PushupRepTracker(ThresholdCycleTracker):
    """
    Rep de push-up: plancha alta (codo extendido) → flexión profunda (pecho cerca del
    suelo) → extendido, sobre el promedio bilateral de flexión de codo. A diferencia de
    curl, la fase de bajada (ida) es excéntrica y la de empuje (vuelta) concéntrica —
    misma semántica que squat, aplicada al tren superior.

    Umbrales (grados de flexión de codo, primera estimación heurística — pendiente
    de calibrar con vídeos gold): entrar en bajada 25, fondo mínimo 65,
    retroceso de pico 8, vuelta a extendido 20. El tronco casi horizontal (F1,
    ``trunk_incl_mean_deg``) es la señal que distingue push-up de curl en el
    clasificador de ejercicio; el tracker de repeticiones solo usa el codo.
    """

    def __init__(self) -> None:
        super().__init__(
            signal_fn=bilateral_elbow_flexion,
            enter_threshold=25.0,
            bottom_threshold=65.0,
            peak_drop=8.0,
            exit_threshold=20.0,
            rising_phase="eccentric",
            falling_phase="concentric",
            pair_fn=elbow_flexion_pair,
            asymmetry_flag_pct=18.0,
            rom_low_margin=8.0,
        )
