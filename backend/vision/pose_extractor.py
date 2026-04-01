# ARCH-1: pose_extractor.py — Capa 1 del motor (ver docs/bio_motion_plan_v2.md §2.1)
"""Extracción de pose: wrapper sobre mediapipe_service + ángulos de rodilla."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from app.services.mediapipe_service import analyze_frame_bgr, analyze_image_bytes
from vision.biomechanics import knee_angles_from_landmarks
from vision.types import PoseFrame


def extract_pose_jpeg(image_bytes: bytes, model_path: Path) -> PoseFrame:
    """Decodifica JPEG y ejecuta el mismo pipeline que :func:`extract_pose_bgr`."""
    result = analyze_image_bytes(image_bytes, model_path)
    knees = knee_angles_from_landmarks(result.landmarks) if result.landmarks else None
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
    knees = knee_angles_from_landmarks(result.landmarks) if result.landmarks else None
    return PoseFrame(
        ok=result.ok,
        landmarks=result.landmarks,
        note=result.note,
        knees=knees,
        world_landmarks=result.world_landmarks or None,
    )

