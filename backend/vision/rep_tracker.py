# ARCH-4: rep_tracker.py — Registro de trackers por etiqueta (ver docs/planificacion/bio_motion_plan_v2.md §2.3)
"""
Router de trackers por etiqueta de ejercicio; la ABC vive en ``rep_tracker_abc``.

Agregar un ejercicio nuevo = crear su clase (idealmente configurando
``ThresholdCycleTracker``) y registrarla en ``DEFAULT_TRACKER_FACTORIES``,
sin modificar el router.
"""

from __future__ import annotations

from collections.abc import Callable

from vision.rep_tracker_abc import RepTracker
from vision.rep_trackers.deadlift import DeadliftRepTracker
from vision.rep_trackers.elbow_curl import ElbowCurlRepTracker
from vision.rep_trackers.jumping_jack import JumpingJackRepTracker
from vision.rep_trackers.overhead_press import OverheadPressRepTracker
from vision.rep_trackers.pushup import PushupRepTracker
from vision.rep_trackers.squat import SquatRepTracker
from vision.rep_trackers.unknown import UnknownRepTracker
from vision.types import FeatureFrame, RepState

# Etiquetas sin factory dedicada caen en UnknownRepTracker (sin conteo).
# plank y mountain_climber quedan sin tracker dedicado (ver docs/spec/exercise-catalog-external.md).
DEFAULT_TRACKER_FACTORIES: dict[str, Callable[[], RepTracker]] = {
    "squat": SquatRepTracker,
    "curl": ElbowCurlRepTracker,
    "pushup": PushupRepTracker,
    "deadlift": DeadliftRepTracker,
    "overhead_press": OverheadPressRepTracker,
    "jumping_jack": JumpingJackRepTracker,
}


def _norm_label(label: str, unknown: str) -> str:
    t = (label or "").strip().lower()
    return t if t else unknown


class RepTrackerRouter:
    """Delega en el tracker concreto según ``exercise_label``; reinicia al cambiar de etiqueta."""

    def __init__(
        self,
        unknown_label: str = "unknown",
        factories: dict[str, Callable[[], RepTracker]] | None = None,
    ) -> None:
        self._unknown_label = unknown_label
        self._factories = dict(DEFAULT_TRACKER_FACTORIES if factories is None else factories)
        self._last_effective: str | None = None
        # Instancias perezosas por etiqueta; etiquetas sin factory comparten el unknown.
        self._trackers: dict[str, RepTracker] = {unknown_label: UnknownRepTracker()}

    def reset_all(self) -> None:
        self._last_effective = None
        for t in self._trackers.values():
            t.reset()

    def _tracker_for(self, effective: str) -> RepTracker:
        tracker = self._trackers.get(effective)
        if tracker is None:
            tracker = self._factories[effective]()
            self._trackers[effective] = tracker
        return tracker

    def update(self, frame: FeatureFrame) -> RepState:
        label = _norm_label(frame.exercise_label, self._unknown_label)
        effective = label if label in self._factories else self._unknown_label

        if self._last_effective is not None and self._last_effective != effective:
            # Al cambiar de ejercicio, limpiar estado del tracker anterior.
            prev = self._trackers.get(self._last_effective)
            if prev is not None:
                prev.reset()
        self._last_effective = effective

        return self._tracker_for(effective).update(frame)
