"""
WebSocket de pose en tiempo (semi-)real con fuente intercambiable (cámara / archivo / URL).

Arquitectura producer-consumer (v2):
- Producer: lee frames de VideoSource en hilo dedicado, los pone en _frame_queue.
- Consumer: toma frames de la queue, corre engine.process_bgr en hilo de CPU,
  codifica JPEG si aplica, y envía por WebSocket.
- Sleep compensado: el consumer mide el tiempo real de cada iteración y duerme
  solo el tiempo restante del presupuesto por frame — evita acumulación de delay.

Fix frames negros (v2.1):
- _encode_preview_jpeg devuelve (b64, ok) en vez de str|None, para distinguir
  "encode falló" de "no había JPEG este stride".
- Cuando include_preview=True y el encode falla, se reenvía el último JPEG válido
  (_last_valid_jpeg_b64) en lugar de omitir la clave — el cliente no pierde imagen.
- El stride de preview sigue igual: frames entre previews no incluyen JPEG
  (el cliente retiene el anterior). Solo ante fallo de encode se reenvía el último válido.

Documentación sugerida — Cap. 6: requisito de trazabilidad en pruebas con vídeo inyectado;
Cap. 7: conjunto gold standard bajo ``tests/assets/videos``.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import threading
import time
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.models.schemas import PoseStreamConfig
from app.paths import backend_root
from app.services.equipment_detect_factory import build_optional_equipment_detector
from app.services.feature_sample_persist import build_optional_feature_collector
from app.services.pose.mediapipe import reset_pose_video_timestamp_anchor, sdr_tonemap_bgr
from app.services.video.downloader import (
    download_video,
    is_youtube_page_url,
    normalize_youtube_url,
    resolve_playable_stream,
)
from vision.paths import resolve_gold_standard_video
from vision.processor import VideoSource
from vision.realtime_engine import RealtimeEngineSession
from vision.stream_processing_plan import (
    build_stream_processing_plan,
    downscale_bgr_max_side,
)

log = logging.getLogger(__name__)

router = APIRouter(tags=["pose-stream"])

_BACKEND_ROOT = backend_root()

# Máximo de frames pre-leídos esperando proceso. 2 es suficiente para solapar
# I/O con CPU sin consumir memoria innecesaria (cada frame ~1-3 MB BGR).
_QUEUE_MAXSIZE = 2

# Sentinel para señalar fin de stream al consumer sin usar None ambiguo.
_STREAM_DONE = object()

# Una sola sesión pose-stream activa: evita que un segundo cliente llame a
# ``reset_pose_video_timestamp_anchor`` mientras el primero está entre frames
# (p. ej. en ``asyncio.sleep``), lo que cerraba el landmarker global y dejaba
# el proceso en estado inconsistente.
_POSE_STREAM_SLOT = asyncio.Lock()


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
        page = cfg.stream_url.strip()
        if is_youtube_page_url(page):
            page = normalize_youtube_url(page)
        try:
            playable = resolve_playable_stream(page)
            try:
                return VideoSource(
                    "url",
                    file_path=playable.url,
                    finite=playable.finite,
                    http_headers=playable.http_headers,
                )
            except RuntimeError as open_exc:
                if not is_youtube_page_url(page):
                    raise
                log.warning(
                    "OpenCV no abrió el stream YouTube; descarga H.264 de respaldo: %s",
                    open_exc,
                )
                raise
        except Exception as exc:
            if not is_youtube_page_url(page):
                raise RuntimeError(f"No se pudo abrir el stream: {exc}") from exc
            log.warning("YouTube stream falló (%s); descarga H.264: %s", page, exc)
            out_dir = settings.downloads_dir
            if not Path(out_dir).is_absolute():
                out_dir = str(backend_root() / out_dir)
            local = download_video(page, out_dir, quality="720p")
            return VideoSource("file", file_path=local)
    raise ValueError(f"Fuente no soportada: {cfg.source}")


def _encode_preview_jpeg(
    frame: np.ndarray,
    quality: int,
    *,
    max_long_side: float = 800.0,
    max_short_side: float = 600.0,
) -> tuple[str | None, bool]:
    """
    Resize + encode JPEG → base64. Corre en hilo de CPU (to_thread).

    Returns:
        (b64_string, success): si el encode falla, devuelve (None, False).
        El caller distingue fallo de encode vs. stride sin preview.
    """
    try:
        h, w = frame.shape[:2]
        scale = min(max_long_side / max(w, 1), max_short_side / max(h, 1), 1.0)
        small = cv2.resize(frame, (int(w * scale), int(h * scale))) if scale < 1.0 else frame
        ok, buf = cv2.imencode(".jpg", small, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if ok:
            return base64.b64encode(buf.tobytes()).decode("ascii"), True
    except Exception:  # noqa: BLE001
        pass
    return None, False


def _read_frames_blocking(
    source: VideoSource,
    queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
    stop_event: threading.Event,
) -> None:
    """
    Hilo productor (threading, no async).

    Lee frames de VideoSource y los deposita en la queue usando
    ``run_coroutine_threadsafe`` para cruzar la frontera hilo→event loop de forma segura.
    Deposita ``_STREAM_DONE`` al terminar para que el consumer pueda salir limpiamente.

    ``stop_event`` permite abortar lectura al cerrar el WebSocket sin llamar a
    ``VideoSource.release()`` mientras ``get_frame()`` sigue en curso en otro hilo.
    """
    try:
        while not stop_event.is_set():
            frame = source.get_frame()
            if stop_event.is_set():
                break
            future = asyncio.run_coroutine_threadsafe(queue.put(frame), loop)
            future.result()
            if frame is None:
                break
    except Exception:  # noqa: BLE001
        log.exception("Error en hilo productor de frames")
        asyncio.run_coroutine_threadsafe(queue.put(None), loop)
    finally:
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
        {"source":"url","stream_url":"https://www.youtube.com/watch?v=...","target_fps":12}
    """
    await ws.accept()
    try:
        raw = await ws.receive_text()
        cfg = PoseStreamConfig.model_validate_json(raw)
    except WebSocketDisconnect:
        log.info("Cliente desconectó /ws/pose-stream (sin iniciar sesión)")
        return
    except json.JSONDecodeError as exc:
        log.warning("JSON inválido en /ws/pose-stream: %s", exc)
        try:
            await ws.close(code=4000)
        except Exception:  # noqa: BLE001
            pass
        return

    async with _POSE_STREAM_SLOT:
        source: VideoSource | None = None
        producer_task: asyncio.Future | None = None
        frame_queue: asyncio.Queue | None = None
        stop_producer = threading.Event()

        try:
            source = await asyncio.to_thread(_build_video_source, cfg)
            total_frames = source.total_frame_count
            nw, nh, nf = source.stream_geometry()

            plan = build_stream_processing_plan(
                stream_tuning=cfg.stream_tuning,
                requested_target_fps=float(cfg.target_fps),
                max_throughput=bool(cfg.max_throughput),
                preview_jpeg_quality=int(cfg.preview_jpeg_quality),
                base_inference_stride=settings.pose_inference_stride,
                native_width=nw,
                native_height=nh,
                native_fps=nf,
            )
            log.info("Pose-stream perfil de vídeo: %s", plan.to_public_dict())

            model_path = settings.resolve_model_path(_BACKEND_ROOT)
            engine = RealtimeEngineSession(
                _BACKEND_ROOT,
                model_path,
                settings.exercise_classifier_config(),
                inference_stride=plan.inference_stride,
                analysis_enabled=not cfg.capture_only,
                forced_exercise_label=cfg.forced_exercise_label,
                equipment_label=cfg.equipment_label,
                feature_collector=build_optional_feature_collector(),
                equipment_detector=build_optional_equipment_detector(),
                object_detect_stride=settings.object_detect_stride,
            )

            max_tp = bool(cfg.max_throughput)
            interval = 0.0 if max_tp else (1.0 / max(plan.effective_target_fps, 0.5))
            pacing_fps_for_preview = float(plan.effective_target_fps)
            decode_max_side = plan.decode_max_side
            preview_encode_max_side = float(plan.preview_encode_max_side)

            frame_index = 0

            reset_pose_video_timestamp_anchor()

            try:
                await ws.send_json({
                    "schema_version": 1,
                    "stream_profile": plan.to_public_dict(),
                })
            except Exception:  # noqa: BLE001
                pass

            stream_start = time.perf_counter()
            last_timestamp_ms = -1
            preview = _PreviewParams(
                fps=float(cfg.preview_fps),
                quality=int(plan.preview_jpeg_quality),
                stride=(
                    1
                    if max_tp
                    else max(1, int(round(pacing_fps_for_preview / float(cfg.preview_fps))))
                ),
            )

            _last_valid_jpeg_b64: str | None = None
            last_preview_wall = 0.0

            loop = asyncio.get_running_loop()
            frame_queue = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
            producer_task = loop.run_in_executor(
                None,
                _read_frames_blocking,
                source,
                frame_queue,
                loop,
                stop_producer,
            )

            while True:
                t_frame_start = time.perf_counter()
    
                item = await frame_queue.get()
                t_after_queue = time.perf_counter()
                queue_wait_ms = (t_after_queue - t_frame_start) * 1000.0
    
                if item is _STREAM_DONE:
                    break
    
                frame: np.ndarray | None = item
    
                if frame is None:
                    if source is not None and source.finite:
                        break
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
                    if cfg.include_preview and _last_valid_jpeg_b64 is not None:
                        err_payload["preview_jpeg_base64"] = _last_valid_jpeg_b64
                    if cfg.diagnostics:
                        iteration_wall_ms = (time.perf_counter() - t_frame_start) * 1000.0
                        err_payload["consumer_timing_ms"] = {
                            "queue_wait_ms": round(queue_wait_ms, 3),
                            "process_bgr_ms": 0.0,
                            "jpeg_encode_ms": 0.0,
                            "sleep_wall_ms": round(sleep_wall_ms, 3),
                            "iteration_wall_ms": round(iteration_wall_ms, 3),
                            "frame_budget_ms": round(interval * 1000.0, 3) if interval > 0 else 0.0,
                            "max_throughput": max_tp,
                        }
                    await ws.send_json(err_payload)
                    continue
    
                ts_ms = int((time.perf_counter() - stream_start) * 1000.0)
                if ts_ms <= last_timestamp_ms:
                    ts_ms = last_timestamp_ms + 1
                last_timestamp_ms = ts_ms

                frame_work = (
                    downscale_bgr_max_side(frame, decode_max_side)
                    if decode_max_side
                    else frame
                )
                # 4K HDR (iPhone HEVC): tone-map tras downscale; MediaPipe espera SDR.
                if max(nw, nh) >= 3000:
                    frame_work = sdr_tonemap_bgr(frame_work)

                t_before_process = time.perf_counter()
                payload: dict = await asyncio.to_thread(engine.process_bgr, frame_work, frame_index, ts_ms)
                process_bgr_ms = (time.perf_counter() - t_before_process) * 1000.0
                payload["total_frames"] = total_frames
    
                jpeg_encode_ms = 0.0
                if cfg.include_preview:
                    if max_tp:
                        now_pv = time.perf_counter()
                        min_pv_gap = 1.0 / max(preview.fps, 1.0)
                        is_preview_frame = (now_pv - last_preview_wall) >= min_pv_gap
                    else:
                        is_preview_frame = frame_index % preview.stride == 0
                    if is_preview_frame:
                        if max_tp:
                            last_preview_wall = time.perf_counter()
                        t_jpeg0 = time.perf_counter()
                        jpeg_b64, encode_ok = await asyncio.to_thread(
                            lambda: _encode_preview_jpeg(
                                frame_work,
                                preview.quality,
                                max_long_side=preview_encode_max_side,
                            ),
                        )
                        jpeg_encode_ms = (time.perf_counter() - t_jpeg0) * 1000.0
                        if encode_ok and jpeg_b64:
                            _last_valid_jpeg_b64 = jpeg_b64
                            payload["preview_jpeg_base64"] = jpeg_b64
                        elif _last_valid_jpeg_b64 is not None:
                            payload["preview_jpeg_base64"] = _last_valid_jpeg_b64
    
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
                            stride=(
                                1
                                if max_tp
                                else max(1, int(round(pacing_fps_for_preview / new_fps)))
                            ),
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
                        "frame_budget_ms": round(interval * 1000.0, 3) if interval > 0 else 0.0,
                        "max_throughput": max_tp,
                    }
    
                await ws.send_json(payload)
                frame_index += 1
    
                await asyncio.sleep(sleep_budget)

            if source is not None and source.finite:
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
        except (ValueError, FileNotFoundError) as exc:
            log.warning("Config o archivo inválido: %s", exc)
            try:
                await ws.send_json({"error": str(exc)})
            except Exception:  # noqa: BLE001
                pass
            try:
                await ws.close(code=4000)
            except Exception:  # noqa: BLE001
                pass
        except Exception as exc:  # noqa: BLE001
            log.exception("Error en /ws/pose-stream")
            try:
                await ws.send_json({"error": str(exc)})
            except Exception:  # noqa: BLE001
                pass
            try:
                await ws.close(code=1011)
            except Exception:  # noqa: BLE001
                pass
        finally:
            stop_producer.set()
            if frame_queue is not None:
                while not frame_queue.empty():
                    try:
                        frame_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
            if producer_task is not None:
                try:
                    await asyncio.wait_for(asyncio.shield(producer_task), timeout=15.0)
                except (asyncio.TimeoutError, Exception):
                    log.warning("Productor pose-stream: timeout esperando fin del hilo")
            if source is not None:
                source.release()
