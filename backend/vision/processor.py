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

    Para vídeo en archivo, si el stream termina se reinicia al frame 0 (útil en bucles
    de regresión sin intervención manual).
    """

    def __init__(
        self,
        source_type: SourceType = "camera",
        file_path: str | None = None,
        device_index: int = 0,
    ) -> None:
        self.source_type: SourceType = source_type
        self._cap: cv2.VideoCapture | None = None

        if source_type == "camera":
            self._cap = cv2.VideoCapture(device_index)
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

    def get_frame(self) -> np.ndarray | None:
        """Lee un frame BGR. Devuelve None si la fuente falla (excepto archivo en loop)."""
        if self._cap is None:
            return None
        ok, frame = self._cap.read()
        if ok and frame is not None:
            return frame

        if self.source_type == "file":
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
