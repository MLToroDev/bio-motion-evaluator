# ARCH-7: pipeline_timer.py — Telemetría desde Fase 1 (ver docs/planificacion/bio_motion_plan_v2.md §7.1)
"""Medición de latencia por etapa del motor de análisis (pose → features → classify → track)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class PipelineTiming:
    """Tiempos por etapa en milisegundos."""

    extract_ms: float = 0.0
    feature_ms: float = 0.0
    classify_ms: float = 0.0
    track_ms: float = 0.0
    total_ms: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {
            "extract": round(self.extract_ms, 3),
            "feature": round(self.feature_ms, 3),
            "classify": round(self.classify_ms, 3),
            "track": round(self.track_ms, 3),
            "total": round(self.total_ms, 3),
        }

    def log_debug(self, extra: dict[str, Any] | None = None) -> None:
        if extra:
            log.debug("pipeline_ms=%s extra=%s", self.as_dict(), extra)
        else:
            log.debug("pipeline_ms=%s", self.as_dict())


@dataclass
class StageTimer:
    """Acumulador mutable usado durante un solo fotograma."""

    timing: PipelineTiming = field(default_factory=PipelineTiming)
    _absolute_start: float = field(default_factory=time.perf_counter)
    _t0: float = field(init=False)

    def __post_init__(self) -> None:
        self._t0 = self._absolute_start

    def mark_extract(self) -> None:
        self.timing.extract_ms = (time.perf_counter() - self._t0) * 1000.0
        self._t0 = time.perf_counter()

    def mark_feature(self) -> None:
        self.timing.feature_ms = (time.perf_counter() - self._t0) * 1000.0
        self._t0 = time.perf_counter()

    def mark_classify(self) -> None:
        self.timing.classify_ms = (time.perf_counter() - self._t0) * 1000.0
        self._t0 = time.perf_counter()

    def mark_track(self) -> None:
        self.timing.track_ms = (time.perf_counter() - self._t0) * 1000.0
        self._t0 = time.perf_counter()

    def finish(self) -> PipelineTiming:
        self.timing.total_ms = (time.perf_counter() - self._absolute_start) * 1000.0
        return self.timing

