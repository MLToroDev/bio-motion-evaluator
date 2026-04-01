from __future__ import annotations

from vision.rep_tracker_abc import RepTracker
from vision.types import FeatureFrame, RepState


class UnknownRepTracker(RepTracker):
    """Sin ejercicio detectado: siempre idle."""

    def __init__(self) -> None:
        self._state = RepState()

    def reset(self) -> None:
        self._state = RepState()

    def update(self, frame: FeatureFrame) -> RepState:
        self._state = RepState(rep_phase="idle", rep_count=0, quality_flags=[])
        return self._state

