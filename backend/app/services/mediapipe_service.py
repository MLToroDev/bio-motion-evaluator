"""Detección de pose con MediaPipe Tasks (Pose Landmarker)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

log = logging.getLogger(__name__)

_LANDMARKER = None
_MODEL_PATH_USED: Path | None = None


@dataclass
class PoseResult:
    ok: bool
    landmarks: list[dict[str, Any]]
    world_landmarks: list[dict[str, Any]]
    note: str | None = None


def _get_landmarker(model_path: Path):
    global _LANDMARKER, _MODEL_PATH_USED
    if _LANDMARKER is not None and _MODEL_PATH_USED == model_path:
        return _LANDMARKER

    if not model_path.is_file():
        msg = f"Modelo no encontrado: {model_path}. Ejecuta: python scripts/download_models.py"
        log.warning(msg)
        raise FileNotFoundError(msg)

    try:
        import mediapipe as mp
    except ImportError as exc:
        raise RuntimeError("mediapipe no está instalado") from exc

    base_options = mp.tasks.BaseOptions(model_asset_path=str(model_path))
    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    _LANDMARKER = mp.tasks.vision.PoseLandmarker.create_from_options(options)
    _MODEL_PATH_USED = model_path
    return _LANDMARKER


def _pose_result_from_detection(result: Any) -> PoseResult:
    """Convierte la salida de PoseLandmarker.detect en [PoseResult]."""
    if not result.pose_landmarks:
        return PoseResult(ok=True, landmarks=[], world_landmarks=[], note="No se detectó ninguna pose")

    lm = result.pose_landmarks[0]
    landmarks = [
        {
            "index": i,
            "x": p.x,
            "y": p.y,
            "z": p.z,
            "visibility": getattr(p, "visibility", None),
        }
        for i, p in enumerate(lm)
    ]

    world: list[dict[str, Any]] = []
    if result.pose_world_landmarks:
        wl = result.pose_world_landmarks[0]
        world = [
            {
                "index": i,
                "x": p.x,
                "y": p.y,
                "z": p.z,
                "visibility": None,
            }
            for i, p in enumerate(wl)
        ]

    return PoseResult(ok=True, landmarks=landmarks, world_landmarks=world, note=None)


def analyze_frame_rgb(rgb: np.ndarray, model_path: Path) -> PoseResult:
    """
    Ejecuta Pose Landmarker sobre un frame RGB (uint8, forma H×W×3).

    Usado por el pipeline de streaming (cámara o vídeo inyectado) sin codificar a JPEG.
    """
    if rgb is None or rgb.size == 0:
        return PoseResult(ok=False, landmarks=[], world_landmarks=[], note="Frame vacío")
    try:
        import mediapipe as mp

        landmarker = _get_landmarker(model_path)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_image)
    except FileNotFoundError as exc:
        return PoseResult(ok=False, landmarks=[], world_landmarks=[], note=str(exc))
    except Exception as exc:  # noqa: BLE001
        log.exception("Error MediaPipe (frame)")
        return PoseResult(ok=False, landmarks=[], world_landmarks=[], note=str(exc))

    return _pose_result_from_detection(result)


def analyze_frame_bgr(bgr: np.ndarray, model_path: Path) -> PoseResult:
    """Conveniencia: convierte BGR (OpenCV) a RGB y analiza."""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return analyze_frame_rgb(rgb, model_path)


def analyze_image_bytes(image_bytes: bytes, model_path: Path) -> PoseResult:
    """Decodifica imagen y ejecuta Pose Landmarker."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        return PoseResult(ok=False, landmarks=[], world_landmarks=[], note="No se pudo decodificar la imagen")

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    try:
        import mediapipe as mp

        landmarker = _get_landmarker(model_path)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_image)
    except FileNotFoundError as exc:
        return PoseResult(ok=False, landmarks=[], world_landmarks=[], note=str(exc))
    except Exception as exc:  # noqa: BLE001
        log.exception("Error MediaPipe")
        return PoseResult(ok=False, landmarks=[], world_landmarks=[], note=str(exc))

    return _pose_result_from_detection(result)
