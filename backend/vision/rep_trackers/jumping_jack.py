# RepTracker de salto de tijera (jumping jack) sobre la FSM genérica ThresholdCycleTracker.
from __future__ import annotations

from vision.rep_trackers.threshold_cycle import (
    ThresholdCycleTracker,
    bilateral_wrist_height,
    wrist_height_pair,
)


class JumpingJackRepTracker(ThresholdCycleTracker):
    """
    Rep de jumping jack: brazos abajo → extendidos por encima de la cabeza (salto con
    piernas abiertas) → abajo, sobre el promedio bilateral de altura relativa de
    muñeca (F4; misma señal que overhead_press, movimiento mucho más rápido y con
    menor rango de asimetría tolerada por ser bilateral y simétrico).

    Umbrales (altura relativa adimensional, primera estimación heurística — pendiente
    de calibrar con vídeos gold): entrar en subida 0.9, pico mínimo 1.4, retroceso de
    pico 0.15, vuelta a posición baja 0.7. La alta velocidad angular resultante (F5)
    es lo que distingue este patrón de overhead_press en el clasificador de ejercicio.
    """

    def __init__(self) -> None:
        super().__init__(
            signal_fn=bilateral_wrist_height,
            enter_threshold=0.9,
            bottom_threshold=1.4,
            peak_drop=0.15,
            exit_threshold=0.7,
            rising_phase="concentric",
            falling_phase="eccentric",
            pair_fn=wrist_height_pair,
            asymmetry_flag_pct=15.0,
            rom_low_margin=0.15,
        )
