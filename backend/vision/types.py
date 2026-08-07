# Tipos compartidos del motor de análisis (pose, tracking, clasificación; plan v2).
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

RepPhase = Literal["concentric", "eccentric", "hold", "idle"]


@dataclass
class PoseFrame:
    """Un fotograma tras extracción de pose (MediaPipe)."""

    ok: bool
    landmarks: list[dict[str, Any]]
    note: str | None
    knees: dict[str, float] | None = None
    world_landmarks: list[dict[str, Any]] | None = None


@dataclass
class ClassificationResult:
    """Salida del clasificador de ejercicio (ventana o frame)."""

    label: str
    confidence: float
    raw_scores: dict[str, float] | None = None


@dataclass
class RepState:
    """Estado de repeticiones y fase para el payload WS."""

    rep_phase: RepPhase = "idle"
    rep_count: int = 0
    quality_flags: list[str] = field(default_factory=list)


@dataclass
class FeatureFrame:
    """
    Entrada unificada al RepTracker: pose + derivadas por frame + contexto de clasificación.
    """

    pose: PoseFrame
    frame_index: int
    exercise_label: str
    exercise_confidence: float
    dt_s: float
    angular_velocity_deg_s: dict[str, float] = field(default_factory=dict)
    periodicity_score: float = 0.0
    calibration_scale: float = 1.0


