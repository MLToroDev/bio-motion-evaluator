"""Abstracción de captura de video: cámara local, archivo o URL/RTSP (OpenCV)."""

from __future__ import annotations

import logging
from typing import Literal

import cv2
import numpy as np

log = logging.getLogger(__name__)

SourceType = Literal["camera", "file", "url"]


class VideoSource:
    """
    Proveedor de frames BGR intercambiable para pruebas con cámara o vídeo pre-grabado.

    Para vídeo en archivo, por defecto al llegar al final devuelve ``None`` (fin del análisis).
    Con ``loop_file=True`` se vuelve al frame 0 (p. ej. bucles de regresión).
    """

    def __init__(
        self,
        source_type: SourceType = "camera",
        file_path: str | None = None,
        device_index: int = 0,
        *,
        loop_file: bool = False,
    ) -> None:
        self.source_type: SourceType = source_type
        self._loop_file = loop_file
        self._cap: cv2.VideoCapture | None = None

        if source_type == "camera":
            self._cap = cv2.VideoCapture(device_index)
            # Cola de captura mínima (donde el backend lo permite): evita acumular
            # fotogramas viejos cuando el procesamiento va más lento que la cámara.
            # No sube el FPS máximo de la webcam (suele ser ~30 a 1080p), pero mejora
            # la sensación de "tiempo real" en /ws/pose-stream y similares.
            try:
                self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:  # noqa: BLE001 — propiedad opcional según driver
                pass
            log.info("VideoSource: cámara índice %s", device_index)
        elif source_type == "file":
            if not file_path:
                raise ValueError("file_path es obligatorio cuando source_type='file'")
            self._cap = cv2.VideoCapture(file_path)
            log.info("VideoSource: archivo %s", file_path)
        elif source_type == "url":
            if not file_path:
                raise ValueError("file_path debe ser la URL RTSP/HTTP cuando source_type='url'")
            self._cap = cv2.VideoCapture(file_path)
            log.info("VideoSource: URL/stream %s", file_path)
        else:
            raise ValueError(f"source_type no soportado: {source_type}")

        if self._cap is None or not self._cap.isOpened():
            raise RuntimeError(f"No se pudo abrir la fuente: {source_type} {file_path!r}")

        self._native_width = max(0, int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)))
        self._native_height = max(0, int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        self._native_fps = float(self._cap.get(cv2.CAP_PROP_FPS))

        #: Número reportado por el códec para `file` (OpenCV). Puede ser 0 o inexacto; `None` si no aplica.
        self.total_frame_count: int | None = None
        if source_type == "file":
            reported = float(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if reported > 0.0 and reported < 1e9:
                self.total_frame_count = int(reported)

    def stream_geometry(self) -> tuple[int, int, float]:
        """
        Ancho, alto y FPS tal como los reporta OpenCV (pueden ser 0 si el backend no los expone).

        El FPS se sustituye por 30.0 solo para heurísticas cuando es desconocido.
        """
        w, h = self._native_width, self._native_height
        fps = self._native_fps
        if fps < 0.1:
            fps = 30.0
        return w, h, fps

    def get_frame(self) -> np.ndarray | None:
        """Lee un frame BGR. Devuelve None si la fuente falla (excepto archivo en loop)."""
        if self._cap is None:
            return None
        ok, frame = self._cap.read()
        if ok and frame is not None:
            return frame

        if self.source_type == "file":
            if self._loop_file:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok2, frame2 = self._cap.read()
                if ok2 and frame2 is not None:
                    return frame2
            return None

        log.warning("VideoSource: fallo al leer frame (%s)", self.source_type)
        return None

    def release(self) -> None:
        """Libera el recurso de captura."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self) -> VideoSource:
        return self

    def __exit__(self, *args: object) -> None:
        self.release()

