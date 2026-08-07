"""
Perfil de procesamiento adaptativo para /ws/pose-stream.

A partir de la geometría y FPS nativos del flujo (OpenCV) y la petición del cliente,
decide cómo tratar el vídeo sin ser solo una validación: downscale previo a la pose,
stride de inferencia, techo de FPS de consumo y parámetros de JPEG de preview.

Objetivo: equilibrar carga de CPU, latencia y utilidad biomecánica cuando el clip
es exigente (p. ej. 1080p60).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import cv2
import numpy as np

StreamTuningMode = Literal["auto", "off"]


def downscale_bgr_max_side(bgr: np.ndarray, max_side: int) -> np.ndarray:
    """Escala BGR manteniendo aspecto para que el lado mayor sea como mucho ``max_side``."""
    if max_side <= 0 or bgr is None or bgr.size == 0:
        return bgr
    h, w = bgr.shape[:2]
    m = max(h, w)
    if m <= max_side:
        return bgr
    scale = max_side / m
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    return cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_AREA)


def classify_stream_tier(width: int, height: int, fps: float) -> Literal["light", "medium", "heavy"]:
    """Clasificación heurística por píxeles por frame y FPS declarado."""
    if width <= 0 or height <= 0:
        return "medium"
    pixels = width * height
    hi = 1920 * 1080
    med = 1280 * 720
    if pixels >= hi * 0.92 or fps >= 55.0:
        return "heavy"
    if pixels >= med * 0.92 or fps >= 36.0:
        return "medium"
    return "light"


@dataclass
class StreamProcessingPlan:
    """Decisiones aplicadas en el consumer del pose-stream."""

    tier: str
    tuning_mode: StreamTuningMode
    native_width: int
    native_height: int
    native_fps: float
    decode_max_side: int | None
    inference_stride: int
    effective_target_fps: float
    preview_jpeg_quality: int
    preview_encode_max_side: float
    rationale: list[str] = field(default_factory=list)

    def to_public_dict(self) -> dict[str, Any]:
        """Payload JSON para el cliente (primer mensaje ``stream_profile``)."""
        return {
            "tier": self.tier,
            "stream_tuning": self.tuning_mode,
            "native": {
                "width": self.native_width,
                "height": self.native_height,
                "fps": round(self.native_fps, 3),
            },
            "decode_max_side": self.decode_max_side,
            "inference_stride": self.inference_stride,
            "effective_target_fps": round(self.effective_target_fps, 4),
            "preview_jpeg_quality": self.preview_jpeg_quality,
            "preview_encode_max_side": self.preview_encode_max_side,
            "notes": list(self.rationale),
        }


def build_stream_processing_plan(
    *,
    stream_tuning: StreamTuningMode,
    requested_target_fps: float,
    max_throughput: bool,
    preview_jpeg_quality: int,
    base_inference_stride: int,
    native_width: int,
    native_height: int,
    native_fps: float,
) -> StreamProcessingPlan:
    """
    Construye el plan. Con ``stream_tuning=off`` solo respeta configuración + stride base.

    Con ``auto``, ajusta según tier (resolución × FPS nativos).
    """
    base_stride = max(1, int(base_inference_stride))
    q0 = max(70, min(90, int(preview_jpeg_quality)))
    w = max(0, int(native_width))
    h = max(0, int(native_height))
    fps = float(native_fps) if native_fps > 0.1 else 30.0

    if stream_tuning == "off":
        return StreamProcessingPlan(
            tier="manual",
            tuning_mode="off",
            native_width=w,
            native_height=h,
            native_fps=fps,
            decode_max_side=None,
            inference_stride=base_stride,
            effective_target_fps=float(requested_target_fps),
            preview_jpeg_quality=q0,
            preview_encode_max_side=800.0,
            rationale=["Ajuste automático desactivado (stream_tuning=off)."],
        )

    tier = classify_stream_tier(w, h, fps)
    rationale: list[str] = [
        f"Perfil automático: tier={tier} ({w}×{h} @ {fps:.1f} FPS declarados).",
    ]

    decode_max: int | None = None
    min_stride = base_stride
    fps_cap = float(requested_target_fps)
    q = q0
    enc_side = 800.0

    if tier == "heavy":
        decode_max = 720
        min_stride = max(base_stride, 2)
        if not max_throughput:
            fps_cap = min(fps_cap, 16.0)
        q = max(70, q0 - 6)
        enc_side = 640.0
        rationale.append(
            "Carga alta: downscale de decodificación a 720px en el lado mayor, "
            "stride de inferencia ≥2 y techo de ~16 FPS de consumo (si no es max_throughput)."
        )
    elif tier == "medium":
        decode_max = 960
        if not max_throughput:
            fps_cap = min(fps_cap, 22.0)
        q = max(70, q0 - 3)
        enc_side = 720.0
        rationale.append(
            "Carga media: downscale a 960px, techo de ~22 FPS de consumo si aplica, "
            "JPEG de preview algo más ligero."
        )
    else:
        rationale.append("Carga ligera: sin downscale extra; se respeta target_fps del cliente.")

    if max_throughput:
        rationale.append("max_throughput: sin techo de FPS; se mantienen downscale/stride para aliviar CPU.")

    return StreamProcessingPlan(
        tier=tier,
        tuning_mode="auto",
        native_width=w,
        native_height=h,
        native_fps=fps,
        decode_max_side=decode_max,
        inference_stride=min_stride,
        effective_target_fps=float(fps_cap),
        preview_jpeg_quality=q,
        preview_encode_max_side=enc_side,
        rationale=rationale,
    )
