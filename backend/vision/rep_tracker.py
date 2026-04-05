# ARCH-4: rep_tracker.py — Interfaz base RepTracker (ver docs/planificacion/bio_motion_plan_v2.md §2.3)
"""Router de trackers por etiqueta de ejercicio; la ABC vive en ``rep_tracker_abc``."""

from __future__ import annotations

from vision.rep_tracker_abc import RepTracker
from vision.rep_trackers.squat import SquatRepTracker
from vision.rep_trackers.unknown import UnknownRepTracker
from vision.types import FeatureFrame, RepState


def _norm_label(label: str, unknown: str) -> str:
    t = (label or "").strip().lower()
    return t if t else unknown


class RepTrackerRouter:
    """Delega en el tracker concreto según ``exercise_label``; reinicia al cambiar de etiqueta."""

    def __init__(self, unknown_label: str = "unknown") -> None:
        self._unknown_label = unknown_label
        self._last_effective: str | None = None
        self._trackers: dict[str, RepTracker] = {
            unknown_label: UnknownRepTracker(),
            "squat": SquatRepTracker(),
        }

    def reset_all(self) -> None:
        self._last_effective = None
        for t in self._trackers.values():
            t.reset()

    def update(self, frame: FeatureFrame) -> RepState:
        label = _norm_label(frame.exercise_label, self._unknown_label)
        effective = label if label in self._trackers else self._unknown_label

        if self._last_effective is not None and self._last_effective != effective:
            # Al cambiar de ejercicio, limpiar estado del tracker anterior.
            prev = self._trackers.get(self._last_effective)
            if prev is not None:
                prev.reset()
        self._last_effective = effective

        tracker = self._trackers.get(effective) or self._trackers[self._unknown_label]
        return tracker.update(frame)

