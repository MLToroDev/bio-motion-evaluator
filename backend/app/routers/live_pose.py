"""
WebSocket de pose en tiempo (semi-)real con fuente intercambiable (cámara / archivo / URL).

Documentación sugerida — Cap. 6: requisito de trazabilidad en pruebas con vídeo inyectado;
Cap. 7: conjunto gold standard bajo ``tests/assets/videos``.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.models.schemas import PoseStreamConfig
from app.services.mediapipe_service import analyze_frame_bgr
from vision.biomechanics import knee_angles_from_landmarks
from vision.paths import resolve_gold_standard_video
from vision.processor import VideoSource

log = logging.getLogger(__name__)

router = APIRouter(tags=["pose-stream"])

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _build_video_source(cfg: PoseStreamConfig) -> VideoSource:
    if cfg.source == "camera":
        return VideoSource("camera", device_index=cfg.device_index)
    if cfg.source == "file":
        if not cfg.video_filename:
            raise ValueError("video_filename es obligatorio cuando source='file'")
        path = resolve_gold_standard_video(cfg.video_filename, settings.gold_standard_videos_dir())
        if not path.is_file():
            raise FileNotFoundError(f"No existe el vídeo: {path}")
        return VideoSource("file", file_path=str(path))
    if cfg.source == "url":
        if not cfg.stream_url:
            raise ValueError("stream_url es obligatorio cuando source='url'")
        return VideoSource("url", file_path=cfg.stream_url)
    raise ValueError(f"Fuente no soportada: {cfg.source}")


@router.websocket("/ws/pose-stream")
async def pose_stream(ws: WebSocket) -> None:
    """
    1. El cliente envía un único mensaje JSON (texto) con :class:`PoseStreamConfig`.
    2. El servidor envía mensajes JSON por frame con ángulos de rodilla y estado de pose.

    Ejemplo::

        {"source":"file","video_filename":"squat_test.mp4","target_fps":15}
        {"source":"camera","device_index":0,"target_fps":10}
    """
    await ws.accept()
    source: VideoSource | None = None
    try:
        raw = await ws.receive_text()
        cfg = PoseStreamConfig.model_validate_json(raw)
        source = _build_video_source(cfg)
        model_path = settings.resolve_model_path(BACKEND_ROOT)
        interval = 1.0 / cfg.target_fps
        frame_index = 0

        while True:
            frame = await asyncio.to_thread(source.get_frame)
            if frame is None:
                await ws.send_json(
                    {
                        "frame_index": frame_index,
                        "error": "sin_frame",
                        "knees": None,
                    }
                )
                await asyncio.sleep(interval)
                continue

            pose = await asyncio.to_thread(analyze_frame_bgr, frame, model_path)
            knees = knee_angles_from_landmarks(pose.landmarks) if pose.landmarks else None

            await ws.send_json(
                {
                    "frame_index": frame_index,
                    "pose_ok": pose.ok,
                    "note": pose.note,
                    "knees": knees,
                }
            )
            frame_index += 1
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        log.info("Cliente desconectó /ws/pose-stream")
    except json.JSONDecodeError as exc:
        log.warning("JSON inválido en /ws/pose-stream: %s", exc)
        await ws.close(code=4000)
    except (ValueError, FileNotFoundError) as exc:
        log.warning("Config o archivo inválido: %s", exc)
        await ws.send_json({"error": str(exc)})
        await ws.close(code=4000)
    except Exception as exc:  # noqa: BLE001
        log.exception("Error en /ws/pose-stream")
        try:
            await ws.send_json({"error": str(exc)})
        finally:
            await ws.close(code=1011)
    finally:
        if source is not None:
            source.release()
