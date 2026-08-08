# RepTracker de peso muerto (deadlift/hip-hinge) sobre la FSM genérica ThresholdCycleTracker.
from __future__ import annotations

from vision.rep_trackers.threshold_cycle import (
    ThresholdCycleTracker,
    bilateral_hip_flexion,
    hip_flexion_pair,
)


class DeadliftRepTracker(ThresholdCycleTracker):
    """
    Rep de peso muerto: erguido → bisagra de cadera profunda → erguido, sobre el
    promedio bilateral de flexión de cadera (F3). Igual que en squat, la señal sube
    durante la bajada de la barra (excéntrica) y baja durante el levantamiento
    (concéntrica).

    Umbrales (grados de flexión de cadera, primera estimación heurística — pendiente
    de calibrar con vídeos gold): entrar en bisagra 25, fondo mínimo 65, retroceso de
    pico 8, vuelta a erguido 15. La flexión de rodilla moderada (vs. squat, donde
    domina) no se usa aquí; el clasificador de ejercicio distingue ambos por el peso
    relativo de F3 (cadera) frente a la flexión de rodilla del vector base.
    """

    def __init__(self) -> None:
        super().__init__(
            signal_fn=bilateral_hip_flexion,
            enter_threshold=25.0,
            bottom_threshold=65.0,
            peak_drop=8.0,
            exit_threshold=15.0,
            rising_phase="eccentric",
            falling_phase="concentric",
            pair_fn=hip_flexion_pair,
            asymmetry_flag_pct=18.0,
            rom_low_margin=8.0,
        )
