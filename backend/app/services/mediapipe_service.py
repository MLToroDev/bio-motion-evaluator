"""Detección de pose con MediaPipe Tasks (Pose Landmarker)."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

log = logging.getLogger(__name__)

_LANDMARKER_IMAGE = None
_LANDMARKER_VIDEO = None
_MODEL_PATH_IMAGE: Path | None = None
_MODEL_PATH_VIDEO: Path | None = None
_LAST_VIDEO_TIMESTAMP_MS = -1
_VIDEO_LANDMARKER_LOCK = threading.Lock()

# Reducción de resolución para acelerar MediaPipe sin perder demasiada precisión.
_TARGET_MAX_DIM = 640


@dataclass
class PoseResult:
    ok: bool
    landmarks: list[dict[str, Any]]
    world_landmarks: list[dict[str, Any]]
    note: str | None = None


def _build_landmarker_options(model_path: Path, running_mode: str):
    import mediapipe as mp

    mode = (
        mp.tasks.vision.RunningMode.VIDEO
        if running_mode == "video"
        else mp.tasks.vision.RunningMode.IMAGE
    )
    base_options = mp.tasks.BaseOptions(model_asset_path=str(model_path))
    return mp.tasks.vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=mode,
        num_poses=1,
        # Leve mejora en precisión (filtros menos permisivos) sin cambiar el pipeline.
        min_pose_detection_confidence=0.6,
        min_pose_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )


def _get_landmarker(model_path: Path, running_mode: str = "image"):
    global _LANDMARKER_IMAGE, _LANDMARKER_VIDEO, _MODEL_PATH_IMAGE, _MODEL_PATH_VIDEO, _LAST_VIDEO_TIMESTAMP_MS
    if not model_path.is_file():
        msg = (
            f"Modelo no encontrado: {model_path}. Ejecuta: python scripts/download_models.py "
            "(full por defecto; para lite: python scripts/download_models.py lite)"
        )
        log.warning(msg)
        raise FileNotFoundError(msg)

    try:
        import mediapipe as mp
    except ImportError as exc:
        raise RuntimeError("mediapipe no está instalado") from exc

    if running_mode == "video":
        if _LANDMARKER_VIDEO is not None and _MODEL_PATH_VIDEO == model_path:
            return _LANDMARKER_VIDEO
        options = _build_landmarker_options(model_path, running_mode="video")
        _LANDMARKER_VIDEO = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        _MODEL_PATH_VIDEO = model_path
        _LAST_VIDEO_TIMESTAMP_MS = -1
        return _LANDMARKER_VIDEO

    if _LANDMARKER_IMAGE is not None and _MODEL_PATH_IMAGE == model_path:
        return _LANDMARKER_IMAGE
    options = _build_landmarker_options(model_path, running_mode="image")
    _LANDMARKER_IMAGE = mp.tasks.vision.PoseLandmarker.create_from_options(options)
    _MODEL_PATH_IMAGE = model_path
    return _LANDMARKER_IMAGE


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

        landmarker = _get_landmarker(model_path, running_mode="image")
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


def analyze_frame_bgr_video(bgr: np.ndarray, model_path: Path, timestamp_ms: int) -> PoseResult:
    """
    Variante para streaming: RunningMode.VIDEO + detect_for_video(timestamp_ms).

    Requiere ``timestamp_ms`` estrictamente creciente para habilitar tracker temporal.
    """
    if bgr is None or bgr.size == 0:
        return PoseResult(ok=False, landmarks=[], world_landmarks=[], note="Frame vacío")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    h, w = rgb.shape[:2]
    max_dim = max(h, w)
    if max_dim > _TARGET_MAX_DIM:
        scale = _TARGET_MAX_DIM / max_dim
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        rgb = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)

    try:
        import mediapipe as mp

        landmarker = _get_landmarker(model_path, running_mode="video")
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        # MediaPipe VIDEO exige monotonicidad estricta por instancia de landmarker.
        # Como el landmarker VIDEO se reutiliza globalmente entre sesiones, aquí
        # normalizamos y serializamos el acceso para evitar regresiones de timestamp.
        global _LAST_VIDEO_TIMESTAMP_MS
        with _VIDEO_LANDMARKER_LOCK:
            ts = int(timestamp_ms)
            if ts <= _LAST_VIDEO_TIMESTAMP_MS:
                ts = _LAST_VIDEO_TIMESTAMP_MS + 1
            _LAST_VIDEO_TIMESTAMP_MS = ts
            result = landmarker.detect_for_video(mp_image, ts)
    except FileNotFoundError as exc:
        return PoseResult(ok=False, landmarks=[], world_landmarks=[], note=str(exc))
    except Exception as exc:  # noqa: BLE001
        log.exception("Error MediaPipe (video frame)")
        return PoseResult(ok=False, landmarks=[], world_landmarks=[], note=str(exc))

    return _pose_result_from_detection(result)


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

        landmarker = _get_landmarker(model_path, running_mode="image")
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_image)
    except FileNotFoundError as exc:
        return PoseResult(ok=False, landmarks=[], world_landmarks=[], note=str(exc))
    except Exception as exc:  # noqa: BLE001
        log.exception("Error MediaPipe")
        return PoseResult(ok=False, landmarks=[], world_landmarks=[], note=str(exc))

    return _pose_result_from_detection(result)

