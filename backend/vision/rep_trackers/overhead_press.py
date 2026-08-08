# RepTracker de press de hombros (overhead press) sobre la FSM genérica ThresholdCycleTracker.
from __future__ import annotations

from vision.rep_trackers.threshold_cycle import (
    ThresholdCycleTracker,
    bilateral_wrist_height,
    wrist_height_pair,
)


class OverheadPressRepTracker(ThresholdCycleTracker):
    """
    Rep de press de hombros: muñecas a la altura de hombros → extendidas por encima
    de la cabeza → de vuelta a hombros, sobre el promedio bilateral de altura relativa
    de muñeca (F4; 0 = cadera, 1 = hombro, >1 = overhead). Igual que en curl, la fase
    de subida (empuje) es concéntrica y la de bajada excéntrica.

    Umbrales (altura relativa adimensional, primera estimación heurística — pendiente
    de calibrar con vídeos gold): entrar en subida 1.0, pico mínimo 1.5, retroceso de
    pico 0.15, vuelta a posición baja 0.85. Movimiento más lento y controlado que
    jumping_jack, que comparte la misma señal pero con umbrales/velocidad distintos.
    """

    def __init__(self) -> None:
        super().__init__(
            signal_fn=bilateral_wrist_height,
            enter_threshold=1.0,
            bottom_threshold=1.5,
            peak_drop=0.15,
            exit_threshold=0.85,
            rising_phase="concentric",
            falling_phase="eccentric",
            pair_fn=wrist_height_pair,
            asymmetry_flag_pct=25.0,
            rom_low_margin=0.15,
        )
