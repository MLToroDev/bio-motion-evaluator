# RepTracker de flexión de codo (curl) sobre la FSM genérica ThresholdCycleTracker.
from __future__ import annotations

from vision.rep_trackers.threshold_cycle import (
    ThresholdCycleTracker,
    dominant_elbow_flexion,
    elbow_flexion_pair,
)


class ElbowCurlRepTracker(ThresholdCycleTracker):
    """
    Rep de curl de bíceps: extendido → flexión alta → extendido, sobre el codo
    **dominante** (máximo L/R). En curl unilateral el brazo quieto no diluye la señal.
    La fase de ida es concéntrica y la de vuelta excéntrica (inverso a squat).

    Umbrales (grados de flexión de codo): entrar en subida 40, pico mínimo 90,
    retroceso de pico 8, vuelta a extendido 30. Asimetría L/R no marca fallo en
    curl a un brazo (umbral alto). Un press de hombro requiere FSM con señal invertida.
    """

    def __init__(self) -> None:
        super().__init__(
            signal_fn=dominant_elbow_flexion,
            enter_threshold=40.0,
            bottom_threshold=90.0,
            peak_drop=8.0,
            exit_threshold=30.0,
            rising_phase="concentric",
            falling_phase="eccentric",
            pair_fn=elbow_flexion_pair,
            asymmetry_flag_pct=80.0,
            rom_low_margin=8.0,
        )
