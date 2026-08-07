# RepTracker de flexión de codo (curl) sobre la FSM genérica ThresholdCycleTracker.
from __future__ import annotations

from vision.rep_trackers.threshold_cycle import (
    ThresholdCycleTracker,
    bilateral_elbow_flexion,
    elbow_flexion_pair,
)


class ElbowCurlRepTracker(ThresholdCycleTracker):
    """
    Rep de curl de bíceps: extendido → flexión alta → extendido, sobre el promedio
    bilateral de flexión de codo. En curl la señal sube durante la subida de la carga,
    por lo que la fase de ida es concéntrica y la de vuelta excéntrica (inverso a squat).

    Umbrales (grados de flexión de codo): entrar en subida 40, pico mínimo 90,
    retroceso de pico 8, vuelta a extendido 30. Un press de hombro requiere FSM con
    señal invertida (extensión); pendiente como registro futuro.
    """

    def __init__(self) -> None:
        super().__init__(
            signal_fn=bilateral_elbow_flexion,
            enter_threshold=40.0,
            bottom_threshold=90.0,
            peak_drop=8.0,
            exit_threshold=30.0,
            rising_phase="concentric",
            falling_phase="eccentric",
            pair_fn=elbow_flexion_pair,
            asymmetry_flag_pct=18.0,
            rom_low_margin=8.0,
        )
