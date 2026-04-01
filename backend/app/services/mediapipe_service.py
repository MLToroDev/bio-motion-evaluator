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

# Reducción de resolución para acelerar MediaPipe sin perder demasiada precisión.
_TARGET_MAX_DIM = 640


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
        # Leve mejora en precisión (filtros menos permisivos) sin cambiar el pipeline.
        min_pose_detection_confidence=0.6,
        min_pose_presence_confidence=0.6,
        min_tracking_confidence=0.6,
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

    # Downscale para acelerar el infer (MediaPipe cuelga mucho de la resolución).
    h, w = rgb.shape[:2]
    max_dim = max(h, w)
    if max_dim > _TARGET_MAX_DIM:
        scale = _TARGET_MAX_DIM / max_dim
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        rgb = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
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


def _jpeg_bytes_to_rgb(image_bytes: bytes) -> np.ndarray | None:
    """
    RGB H×W×3. Primero intenta decodificar con orientación EXIF (JPEG de móviles);
    ``cv2.imdecode`` no aplica EXIF, lo que desfasa la pose respecto a la vista previa.
    """
    try:
        import io

        from PIL import Image, ImageOps

        img = Image.open(io.BytesIO(image_bytes))
        # Optimización: solo aplicar exif_transpose si la orientación no es la “normal”.
        # Así evitamos trabajo extra en frames donde el tag no esté presente o sea 1.
        exif = img.getexif()
        orientation = exif.get(274)  # 274 = Orientation tag
        if orientation not in (None, 1):
            img = ImageOps.exif_transpose(img)
        return np.asarray(img.convert("RGB"))
    except Exception:
        pass
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        return None
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def analyze_image_bytes(image_bytes: bytes, model_path: Path) -> PoseResult:
    """Decodifica imagen y ejecuta Pose Landmarker."""
    rgb = _jpeg_bytes_to_rgb(image_bytes)
    if rgb is None:
        return PoseResult(ok=False, landmarks=[], world_landmarks=[], note="No se pudo decodificar la imagen")
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

