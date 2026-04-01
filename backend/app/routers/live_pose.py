"""
WebSocket de pose en tiempo (semi-)real con fuente intercambiable (cámara / archivo / URL).

Arquitectura producer-consumer (v2):
- Producer: lee frames de VideoSource en hilo dedicado, los pone en _frame_queue.
- Consumer: toma frames de la queue, corre engine.process_bgr en hilo de CPU,
  codifica JPEG si aplica, y envía por WebSocket.
- Sleep compensado: el consumer mide el tiempo real de cada iteración y duerme
  solo el tiempo restante del presupuesto por frame — evita acumulación de delay.

Documentación sugerida — Cap. 6: requisito de trazabilidad en pruebas con vídeo inyectado;
Cap. 7: conjunto gold standard bajo ``tests/assets/videos``.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.models.schemas import PoseStreamConfig
from vision.paths import resolve_gold_standard_video
from vision.processor import VideoSource
from vision.realtime_engine import RealtimeEngineSession

log = logging.getLogger(__name__)

router = APIRouter(tags=["pose-stream"])

BACKEND_ROOT = Path(__file__).resolve().parents[2]

# Máximo de frames pre-leídos esperando proceso. 2 es suficiente para solapar
# I/O con CPU sin consumir memoria innecesaria (cada frame ~1-3 MB BGR).
_QUEUE_MAXSIZE = 2

# Sentinel para señalar fin de stream al consumer sin usar None ambiguo.
_STREAM_DONE = object()


class _PreviewParams(NamedTuple):
    """Estado mutable de preview empaquetado para pasar entre corutinas."""
    fps: float
    quality: int
    stride: int


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


def _encode_preview_jpeg(frame: np.ndarray, quality: int) -> str | None:
    """Resize + encode JPEG → base64. Corre en hilo de CPU (to_thread)."""
    try:
        h, w = frame.shape[:2]
        scale = min(800 / max(w, 1), 600 / max(h, 1), 1.0)
        small = cv2.resize(frame, (int(w * scale), int(h * scale))) if scale < 1.0 else frame
        ok, buf = cv2.imencode(".jpg", small, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if ok:
            return base64.b64encode(buf.tobytes()).decode("ascii")
    except Exception:  # noqa: BLE001
        pass
    return None


def _read_frames_blocking(source: VideoSource, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop) -> None:
    """
    Hilo productor (threading, no async).

    Lee frames de VideoSource y los deposita en la queue usando
    ``call_soon_threadsafe`` para cruzar la frontera hilo→event loop de forma segura.
    Deposita ``_STREAM_DONE`` al terminar para que el consumer pueda salir limpiamente.
    """
    try:
        while True:
            frame = source.get_frame()
            # Bloqueamos aquí si la queue está llena — backpressure natural hacia el producer.
            # Como la queue es asyncio pero estamos en un hilo, usamos run_coroutine_threadsafe.
            future = asyncio.run_coroutine_threadsafe(queue.put(frame), loop)
            future.result()  # espera a que haya espacio en la queue
            if frame is None:
                break  # fin de archivo o fallo de cámara
    except Exception:  # noqa: BLE001
        log.exception("Error en hilo productor de frames")
        asyncio.run_coroutine_threadsafe(queue.put(None), loop)
    finally:
        # Siempre depositar el sentinel para que el consumer no quede bloqueado.
        asyncio.run_coroutine_threadsafe(queue.put(_STREAM_DONE), loop)


@router.websocket("/ws/pose-stream")
async def pose_stream(ws: WebSocket) -> None:
    """
    1. El cliente envía un único mensaje JSON (texto) con :class:`PoseStreamConfig`.
    2. El servidor envía mensajes JSON por frame con ángulos de rodilla y estado de pose.

    Arquitectura interna: producer (hilo) → asyncio.Queue → consumer (event loop).
    El producer lee frames de disco/cámara mientras el consumer procesa el anterior,
    solapando I/O con CPU y eliminando el principal origen de jitter.

    Ejemplo::

        {"source":"file","video_filename":"squat_test.mp4","target_fps":15}
        {"source":"camera","device_index":0,"target_fps":10}
    """
    await ws.accept()
    source: VideoSource | None = None
    producer_task: asyncio.Future | None = None
    frame_queue: asyncio.Queue | None = None

    try:
        raw = await ws.receive_text()
        cfg = PoseStreamConfig.model_validate_json(raw)
        source = _build_video_source(cfg)
        total_frames = source.total_frame_count
        model_path = settings.resolve_model_path(BACKEND_ROOT)
        engine = RealtimeEngineSession(
            BACKEND_ROOT,
            model_path,
            settings.exercise_classifier_config(),
            inference_stride=settings.pose_inference_stride,
            analysis_enabled=not cfg.capture_only,
        )

        interval = 1.0 / cfg.target_fps
        frame_index = 0
        stream_start = time.perf_counter()
        last_timestamp_ms = -1
        preview = _PreviewParams(
            fps=float(cfg.preview_fps),
            quality=int(cfg.preview_jpeg_quality),
            stride=max(1, int(round(cfg.target_fps / cfg.preview_fps))),
        )

        # ── Producer: lanza hilo dedicado a leer frames ──────────────────────
        loop = asyncio.get_running_loop()
        frame_queue = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        producer_task = loop.run_in_executor(
            None,  # ThreadPoolExecutor por defecto
            _read_frames_blocking,
            source,
            frame_queue,
            loop,
        )

        # ── Consumer: procesa frames de la queue ──────────────────────────────
        while True:
            t_frame_start = time.perf_counter()

            # Tomar el siguiente frame — el producer ya lo tiene listo o está leyéndolo.
            item = await frame_queue.get()
            t_after_queue = time.perf_counter()
            queue_wait_ms = (t_after_queue - t_frame_start) * 1000.0

            # Sentinel: el producer terminó.
            if item is _STREAM_DONE:
                break

            frame: np.ndarray | None = item

            if frame is None:
                # Fin de archivo o fallo de cámara sin sentinel (defensivo).
                if cfg.source == "file":
                    break
                # Sleep compensado incluso en error; luego un único envío con timings coherentes.
                elapsed = time.perf_counter() - t_frame_start
                t_sleep0 = time.perf_counter()
                await asyncio.sleep(max(0.0, interval - elapsed))
                sleep_wall_ms = (time.perf_counter() - t_sleep0) * 1000.0
                err_payload: dict = {
                    "schema_version": 1,
                    "frame_index": frame_index,
                    "error": "sin_frame",
                    "knees": None,
                    "total_frames": total_frames,
                    "server_ts_ms": int(time.time() * 1000),
                }
                if cfg.diagnostics:
                    iteration_wall_ms = (time.perf_counter() - t_frame_start) * 1000.0
                    err_payload["consumer_timing_ms"] = {
                        "queue_wait_ms": round(queue_wait_ms, 3),
                        "process_bgr_ms": 0.0,
                        "jpeg_encode_ms": 0.0,
                        "sleep_wall_ms": round(sleep_wall_ms, 3),
                        "iteration_wall_ms": round(iteration_wall_ms, 3),
                        "frame_budget_ms": round(interval * 1000.0, 3),
                    }
                await ws.send_json(err_payload)
                continue

            # RunningMode.VIDEO exige timestamp_ms incremental para activar tracking temporal.
            # Usamos tiempo monotónico desde el inicio del stream.
            ts_ms = int((time.perf_counter() - stream_start) * 1000.0)
            if ts_ms <= last_timestamp_ms:
                ts_ms = last_timestamp_ms + 1
            last_timestamp_ms = ts_ms

            # Proceso de pose en hilo de CPU (MediaPipe + features + classifier).
            t_before_process = time.perf_counter()
            payload: dict = await asyncio.to_thread(engine.process_bgr, frame, frame_index, ts_ms)
            process_bgr_ms = (time.perf_counter() - t_before_process) * 1000.0
            payload["total_frames"] = total_frames

            # Codificación JPEG también en hilo para no bloquear el event loop.
            jpeg_encode_ms = 0.0
            if cfg.include_preview and (frame_index % preview.stride == 0):
                t_jpeg0 = time.perf_counter()
                jpeg_b64 = await asyncio.to_thread(_encode_preview_jpeg, frame, preview.quality)
                jpeg_encode_ms = (time.perf_counter() - t_jpeg0) * 1000.0
                if jpeg_b64:
                    payload["preview_jpeg_base64"] = jpeg_b64

            # ── Ajustes en caliente antes de enviar (incluido en el presupuesto de sleep) ──
            try:
                control_raw = await asyncio.wait_for(ws.receive_text(), timeout=0.0)
            except asyncio.TimeoutError:
                control_raw = None
            if control_raw:
                try:
                    ctrl = json.loads(control_raw)
                except json.JSONDecodeError:
                    ctrl = None
                if isinstance(ctrl, dict):
                    pf = ctrl.get("preview_fps")
                    new_fps = preview.fps
                    new_quality = preview.quality
                    if pf in (8, 10, 12):
                        new_fps = float(pf)
                    q = ctrl.get("preview_jpeg_quality")
                    if isinstance(q, (int, float)):
                        new_quality = max(70, min(90, int(round(q))))
                    preview = _PreviewParams(
                        fps=new_fps,
                        quality=new_quality,
                        stride=max(1, int(round(cfg.target_fps / new_fps))),
                    )

            t_pre_send = time.perf_counter()
            wall_before_send_ms = (t_pre_send - t_frame_start) * 1000.0
            elapsed = t_pre_send - t_frame_start
            sleep_budget = max(0.0, interval - elapsed)
            if cfg.diagnostics:
                payload["consumer_timing_ms"] = {
                    "queue_wait_ms": round(queue_wait_ms, 3),
                    "process_bgr_ms": round(process_bgr_ms, 3),
                    "jpeg_encode_ms": round(jpeg_encode_ms, 3),
                    "wall_before_send_ms": round(wall_before_send_ms, 3),
                    "residual_before_send_ms": round(
                        max(
                            0.0,
                            wall_before_send_ms - queue_wait_ms - process_bgr_ms - jpeg_encode_ms,
                        ),
                        3,
                    ),
                    "scheduled_sleep_ms": round(sleep_budget * 1000.0, 3),
                    "frame_budget_ms": round(interval * 1000.0, 3),
                }

            await ws.send_json(payload)
            frame_index += 1

            await asyncio.sleep(sleep_budget)

        # ── Fin limpio de archivo ─────────────────────────────────────────────
        if cfg.source == "file":
            try:
                await ws.send_json({
                    "schema_version": 1,
                    "stream_done": True,
                    "frame_index": frame_index,
                    "total_frames": total_frames,
                    "server_ts_ms": int(time.time() * 1000),
                })
            except Exception:  # noqa: BLE001
                pass
            await ws.close(code=1000)

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
        # El producer puede estar bloqueado en queue.put esperando espacio.
        # Drenar la queue desbloquea el hilo para que pueda terminar.
        if frame_queue is not None:
            while not frame_queue.empty():
                try:
                    frame_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        if producer_task is not None:
            try:
                await asyncio.wait_for(asyncio.shield(producer_task), timeout=2.0)
            except (asyncio.TimeoutError, Exception):
                pass
        if source is not None:
            source.release()