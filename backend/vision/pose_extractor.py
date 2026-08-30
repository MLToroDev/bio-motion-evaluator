# ARCH-1: pose_extractor.py — Capa 1 del motor (ver docs/planificacion/bio_motion_plan_v2.md §2.1)
"""
Extracción de pose: wrapper sobre ``app.services.pose.mediapipe`` + ángulos de rodilla.

Los ángulos se calculan mediante :func:`vision.biomechanics.angulos_rodilla`, que
prefiere los ``world_landmarks`` métricos. Calcularlos sobre los landmarks normalizados
sin corregir introduce un sesgo sistemático de hasta ~32 grados
(ver ``docs/spec/goniometria-espacio-de-coordenadas.md``).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from app.services.pose.mediapipe import (
    analyze_frame_bgr,
    analyze_frame_bgr_video,
    analyze_image_bytes,
)
from vision.biomechanics import angulos_rodilla
from vision.types import PoseFrame


def _relacion_aspecto(bgr: np.ndarray) -> float | None:
    """Cociente ``alto / ancho`` del fotograma, o ``None`` si la forma no es utilizable."""
    if bgr is None or getattr(bgr, "ndim", 0) < 2:
        return None
    alto, ancho = int(bgr.shape[0]), int(bgr.shape[1])
    if ancho <= 0 or alto <= 0:
        return None
    return alto / ancho


def extract_pose_jpeg(image_bytes: bytes, model_path: Path) -> PoseFrame:
    """Decodifica JPEG y ejecuta el mismo pipeline que :func:`extract_pose_bgr`."""
    result = analyze_image_bytes(image_bytes, model_path)
    # Sin acceso a la forma del fotograma; se confía en world_landmarks, presente
    # siempre que MediaPipe detecta pose.
    knees = angulos_rodilla(result.landmarks, result.world_landmarks)
    return PoseFrame(
        ok=result.ok,
        landmarks=result.landmarks,
        note=result.note,
        knees=knees,
        world_landmarks=result.world_landmarks or None,
    )


def extract_pose_bgr(bgr: np.ndarray, model_path: Path) -> PoseFrame:
    """Ejecuta MediaPipe sobre BGR OpenCV y calcula rodillas si hay landmarks."""
    result = analyze_frame_bgr(bgr, model_path)
    knees = angulos_rodilla(result.landmarks, result.world_landmarks, _relacion_aspecto(bgr))
    return PoseFrame(
        ok=result.ok,
        landmarks=result.landmarks,
        note=result.note,
        knees=knees,
        world_landmarks=result.world_landmarks or None,
    )


def extract_pose_bgr_video(bgr: np.ndarray, model_path: Path, timestamp_ms: int) -> PoseFrame:
    """Streaming: usa RunningMode.VIDEO para aprovechar tracking temporal de MediaPipe."""
    result = analyze_frame_bgr_video(bgr, model_path, timestamp_ms)
    knees = angulos_rodilla(result.landmarks, result.world_landmarks, _relacion_aspecto(bgr))
    return PoseFrame(
        ok=result.ok,
        landmarks=result.landmarks,
        note=result.note,
        knees=knees,
        world_landmarks=result.world_landmarks or None,
    )

