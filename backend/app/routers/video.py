import asyncio
import json
import logging
import time
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from vision.realtime_engine import RealtimeEngineSession

log = logging.getLogger(__name__)

router = APIRouter(tags=["video"])

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _process_jpeg_frame(engine: RealtimeEngineSession, chunk: bytes, frame_idx: int) -> dict:
    """Ejecuta el motor en el hilo worker y añade metadatos de diagnóstico de latencia."""
    t0 = time.perf_counter()
    payload = engine.process_jpeg(chunk, frame_idx)
    wall_ms = (time.perf_counter() - t0) * 1000.0
    payload["jpeg_bytes"] = len(chunk)
    payload["server_wall_ms"] = round(wall_ms, 3)
    return payload


def _maybe_log_pose_timing(frame_idx: int, payload: dict) -> None:
    pipe = payload.get("pipeline_ms")
    if not isinstance(pipe, dict):
        return
    try:
        total = float(pipe.get("total", 0.0))
    except (TypeError, ValueError):
        total = 0.0
    if settings.log_pose_pipeline_timing:
        log.info(
            "pose_timing frame=%s jpeg_bytes=%s wall_ms=%s pipeline_ms=%s",
            frame_idx,
            payload.get("jpeg_bytes"),
            payload.get("server_wall_ms"),
            pipe,
        )
    elif total >= float(settings.server_pipeline_warn_ms):
        log.warning(
            "pose_slow frame=%s jpeg_bytes=%s wall_ms=%s pipeline_ms=%s (warn>=%sms)",
            frame_idx,
            payload.get("jpeg_bytes"),
            payload.get("server_wall_ms"),
            pipe,
            settings.server_pipeline_warn_ms,
        )


@router.websocket("/ws/video")
async def video_stream(ws: WebSocket) -> None:
    """
    Recibe fotogramas binarios (JPEG) desde cliente o IoT.

    **Protocolo recomendado (análisis en vivo):**
    1. Primer mensaje **texto** JSON: ``{"analyze_pose": true}``
    2. Luego mensajes **binarios** JPEG → respuesta JSON por frame con ``landmarks`` y ``knees``.

    **Protocolo legado (solo contadores):** primer mensaje ya es binario → no hay pose, solo estadísticas.
    """
    await ws.accept()
    model_path = settings.resolve_model_path(BACKEND_ROOT)
    engine: RealtimeEngineSession | None = None

    analyze_pose = False
    capture_only = False
    frames = 0
    bytes_in = 0
    frame_idx = 0

    try:
        first = await ws.receive()

        if first.get("text"):
            try:
                data = json.loads(first["text"])
                analyze_pose = bool(data.get("analyze_pose"))
                capture_only = bool(data.get("capture_only", False))
            except json.JSONDecodeError:
                await ws.send_json({"error": 'Primer mensaje inválido. Usa {"analyze_pose": true} antes de los JPEG.'})
                await ws.close(code=4000)
                return
        elif first.get("bytes"):
            chunk = first["bytes"]
            frames += 1
            bytes_in += len(chunk)
            if analyze_pose:
                if engine is None:
                    engine = RealtimeEngineSession(
                        BACKEND_ROOT,
                        model_path,
                        settings.exercise_classifier_config(),
                        inference_stride=settings.pose_inference_stride,
                        analysis_enabled=not capture_only,
                    )
                payload = await asyncio.to_thread(_process_jpeg_frame, engine, chunk, frame_idx)
                _maybe_log_pose_timing(frame_idx, payload)
                await ws.send_json(payload)
                frame_idx += 1
            else:
                await ws.send_json({"frames": frames, "last_chunk_bytes": len(chunk), "total_bytes": bytes_in})
        else:
            await ws.close(code=4000)
            return

        while True:
            msg = await ws.receive()
            if msg.get("bytes") is not None:
                chunk = msg["bytes"]
                frames += 1
                bytes_in += len(chunk)
                if analyze_pose:
                    if engine is None:
                        engine = RealtimeEngineSession(
                            BACKEND_ROOT,
                            model_path,
                            settings.exercise_classifier_config(),
                            inference_stride=settings.pose_inference_stride,
                            analysis_enabled=not capture_only,
                        )
                    payload = await asyncio.to_thread(_process_jpeg_frame, engine, chunk, frame_idx)
                    _maybe_log_pose_timing(frame_idx, payload)
                    await ws.send_json(payload)
                    frame_idx += 1
                else:
                    await ws.send_json({"frames": frames, "last_chunk_bytes": len(chunk), "total_bytes": bytes_in})
            elif msg.get("text"):
                await ws.send_json({"echo": msg["text"], "frames": frames})
            else:
                break
    except WebSocketDisconnect:
        log.info("WebSocket /ws/video desconectado; frames=%s bytes=%s analyze_pose=%s", frames, bytes_in, analyze_pose)

