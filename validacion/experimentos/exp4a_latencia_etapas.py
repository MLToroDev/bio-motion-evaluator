#!/usr/bin/env python3
"""
Experimento 4 - Nivel A: desglose de latencia por etapa del pipeline de vision.

Mide, fotograma a fotograma y sin servidor de por medio, el costo en milisegundos de
cada etapa del pipeline que el backend ejecuta en produccion:

  1. lectura del fotograma (OpenCV ``VideoCapture.read``),
  2. downscale de decodificacion (solo en la configuracion que replica el tier "heavy"),
  3. inferencia de pose (MediaPipe Pose Landmarker, ``analyze_frame_bgr_video``),
  4. calculo de angulos de rodilla (``knee_angles_from_landmarks``),
  5. codificacion JPEG de la vista previa (``_encode_preview_jpeg`` del router WebSocket).

Notas metodologicas (declaradas de forma explicita porque afectan la lectura de los numeros):

- El servicio de pose hace downscale interno al lado mayor ``_TARGET_MAX_DIM`` (640 px por
  defecto). Para barrer la resolucion de inferencia SIN tocar el codigo de produccion se
  reasigna esa constante del modulo en tiempo de ejecucion desde este script. El fotograma
  se entrega siempre en su resolucion nativa, de modo que el costo de ``cv2.resize`` queda
  incluido dentro de la etapa de inferencia, igual que en produccion.
- ``vision.pose_extractor.extract_pose_bgr_video`` es exactamente la composicion
  ``analyze_frame_bgr_video`` + ``knee_angles_from_landmarks`` (mas la construccion de un
  dataclass). Aqui se invocan las dos funciones por separado para poder separar el costo de
  la inferencia del costo del calculo angular; la suma de ambas etapas equivale al costo de
  ``extract_pose_bgr_video``.
- La etapa JPEG se mide en una pasada dedicada (sin inferencia) para no contaminar el
  cronometro de MediaPipe con cuatro codificaciones por fotograma.

Ejecucion (desde la carpeta ``backend/``)::

    PYTHONPATH=. ~/.venvs/biomotion/bin/python \
        ../validacion/experimentos/exp4a_latencia_etapas.py
"""

from __future__ import annotations

import csv
import platform
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

# Permite ejecutar el script desde backend/ con PYTHONPATH=.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ROOT = _REPO_ROOT / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.api.websocket.live_pose import _encode_preview_jpeg  # noqa: E402
from app.services.pose import mediapipe as pose_service  # noqa: E402
from app.services.pose.mediapipe import (  # noqa: E402
    analyze_frame_bgr,
    analyze_frame_bgr_video,
    reset_pose_video_timestamp_anchor,
)
from vision.biomechanics import knee_angles_from_landmarks  # noqa: E402
from vision.stream_processing_plan import downscale_bgr_max_side  # noqa: E402

VIDEOS_DIR = _REPO_ROOT / "tests" / "assets" / "videos"
RESULTS_DIR = _REPO_ROOT / "validacion" / "resultados"
MODEL_PATH = _BACKEND_ROOT / "models" / "pose_landmarker_full.task"

#: Fotogramas iniciales excluidos de los agregados (inicializacion del modelo, JIT, GC).
WARMUP_FRAMES = 5

#: Calidades JPEG barridas para la vista previa.
JPEG_QUALITIES = (60, 76, 84, 90)

#: Lado mayor del JPEG de vista previa: 800 px (tier light/manual) y 640 px (tier heavy).
JPEG_MAX_SIDES = (800.0, 640.0)


@dataclass
class ConfiguracionPose:
    """Una corrida del pipeline de pose sobre un video con una resolucion de inferencia dada."""

    nombre: str
    video: str
    target_max_dim: int
    decode_max_side: int | None = None
    max_frames: int | None = None
    descripcion: str = ""
    #: "video" usa RunningMode.VIDEO (tracking temporal); "imagen" usa RunningMode.IMAGE
    #: (deteccion completa en cada fotograma, sin tracking).
    modo: str = "video"


@dataclass
class SerieEtapa:
    """Acumulador de tiempos (ms) de una etapa para una configuracion."""

    valores: list[float] = field(default_factory=list)

    def agregar(self, ms: float) -> None:
        self.valores.append(float(ms))


def percentil(valores_ordenados: list[float], p: float) -> float:
    """Percentil por interpolacion lineal sobre una lista ya ordenada."""
    if not valores_ordenados:
        return float("nan")
    if len(valores_ordenados) == 1:
        return valores_ordenados[0]
    k = (len(valores_ordenados) - 1) * p / 100.0
    lo = int(k)
    hi = min(lo + 1, len(valores_ordenados) - 1)
    if lo == hi:
        return valores_ordenados[lo]
    frac = k - lo
    return valores_ordenados[lo] * (1.0 - frac) + valores_ordenados[hi] * frac


def resumen(valores: list[float]) -> dict[str, float]:
    """Media, p50, p95, p99, maximo y minimo en ms."""
    if not valores:
        return {"n": 0, "media": float("nan"), "p50": float("nan"), "p95": float("nan"),
                "p99": float("nan"), "max": float("nan"), "min": float("nan")}
    s = sorted(valores)
    return {
        "n": len(s),
        "media": statistics.fmean(s),
        "p50": percentil(s, 50.0),
        "p95": percentil(s, 95.0),
        "p99": percentil(s, 99.0),
        "max": s[-1],
        "min": s[0],
    }


def geometria_video(path: Path) -> tuple[int, int, float, int]:
    """Ancho, alto, FPS y numero de fotogramas declarados por el contenedor."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {path}")
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return w, h, fps, n


def correr_configuracion_pose(cfg: ConfiguracionPose) -> tuple[dict[str, SerieEtapa], list[dict[str, Any]]]:
    """
    Procesa un video completo cronometrando lectura, downscale, inferencia y angulos.

    Devuelve (series por etapa, filas por fotograma).
    """
    path = VIDEOS_DIR / cfg.video
    _, _, fps, _ = geometria_video(path)
    if fps < 0.1:
        fps = 30.0

    # Barrido de resolucion de inferencia sin tocar codigo de produccion.
    dim_original = pose_service._TARGET_MAX_DIM
    pose_service._TARGET_MAX_DIM = int(cfg.target_max_dim)
    reset_pose_video_timestamp_anchor()

    series: dict[str, SerieEtapa] = {
        "lectura": SerieEtapa(),
        "downscale_decode": SerieEtapa(),
        "inferencia_pose": SerieEtapa(),
        "calculo_angulos": SerieEtapa(),
        "total_sin_preview": SerieEtapa(),
    }
    filas: list[dict[str, Any]] = []

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        pose_service._TARGET_MAX_DIM = dim_original
        raise RuntimeError(f"No se pudo abrir el video: {path}")

    idx = 0
    detecciones_ok = 0
    try:
        while True:
            if cfg.max_frames is not None and idx >= cfg.max_frames:
                break

            t0 = time.perf_counter()
            ok, frame = cap.read()
            t_lectura = (time.perf_counter() - t0) * 1000.0
            if not ok or frame is None:
                break

            t1 = time.perf_counter()
            if cfg.decode_max_side:
                frame_work = downscale_bgr_max_side(frame, cfg.decode_max_side)
            else:
                frame_work = frame
            t_downscale = (time.perf_counter() - t1) * 1000.0

            ts_ms = int(round(idx * 1000.0 / fps))

            t2 = time.perf_counter()
            if cfg.modo == "imagen":
                resultado = analyze_frame_bgr(frame_work, MODEL_PATH)
            else:
                resultado = analyze_frame_bgr_video(frame_work, MODEL_PATH, ts_ms)
            t_infer = (time.perf_counter() - t2) * 1000.0

            t3 = time.perf_counter()
            knees = knee_angles_from_landmarks(resultado.landmarks) if resultado.landmarks else None
            t_ang = (time.perf_counter() - t3) * 1000.0

            total = t_lectura + t_downscale + t_infer + t_ang
            es_warmup = idx < WARMUP_FRAMES
            if not es_warmup:
                series["lectura"].agregar(t_lectura)
                series["downscale_decode"].agregar(t_downscale)
                series["inferencia_pose"].agregar(t_infer)
                series["calculo_angulos"].agregar(t_ang)
                series["total_sin_preview"].agregar(total)
            if resultado.landmarks:
                detecciones_ok += 1

            filas.append({
                "configuracion": cfg.nombre,
                "video": cfg.video,
                "frame_index": idx,
                "warmup": int(es_warmup),
                "lectura_ms": round(t_lectura, 4),
                "downscale_decode_ms": round(t_downscale, 4),
                "inferencia_pose_ms": round(t_infer, 4),
                "calculo_angulos_ms": round(t_ang, 4),
                "total_sin_preview_ms": round(total, 4),
                "pose_detectada": int(bool(resultado.landmarks)),
                "left_knee_flexion_angle_deg": (
                    round(float(knees["left_knee_flexion_angle_deg"]), 3) if knees else ""
                ),
                "right_knee_flexion_angle_deg": (
                    round(float(knees["right_knee_flexion_angle_deg"]), 3) if knees else ""
                ),
            })
            idx += 1
    finally:
        cap.release()
        pose_service._TARGET_MAX_DIM = dim_original
        reset_pose_video_timestamp_anchor()

    print(
        f"  [{cfg.nombre}] {idx} fotogramas, pose detectada en {detecciones_ok} "
        f"({100.0 * detecciones_ok / max(idx, 1):.1f} %)",
        flush=True,
    )
    return series, filas


def correr_barrido_jpeg(video: str, max_frames: int | None = None) -> tuple[dict[str, SerieEtapa], list[dict[str, Any]]]:
    """
    Pasada dedicada al costo de la vista previa: resize + ``cv2.imencode`` + base64.

    Usa el mismo codificador que ``/ws/pose-stream`` para cada combinacion de
    lado mayor (800 / 640 px) y calidad JPEG (60 / 76 / 84 / 90).
    """
    path = VIDEOS_DIR / video
    series: dict[str, SerieEtapa] = {}
    filas: list[dict[str, Any]] = []
    tam_b64: dict[str, list[int]] = {}

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {path}")

    idx = 0
    try:
        while True:
            if max_frames is not None and idx >= max_frames:
                break
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            es_warmup = idx < WARMUP_FRAMES
            for lado in JPEG_MAX_SIDES:
                for q in JPEG_QUALITIES:
                    clave = f"jpeg_q{q}_lado{int(lado)}"
                    t0 = time.perf_counter()
                    b64, ok_enc = _encode_preview_jpeg(frame, q, max_long_side=lado)
                    dt = (time.perf_counter() - t0) * 1000.0
                    n_b64 = len(b64) if (ok_enc and b64) else 0
                    if not es_warmup:
                        series.setdefault(clave, SerieEtapa()).agregar(dt)
                        tam_b64.setdefault(clave, []).append(n_b64)
                    filas.append({
                        "video": video,
                        "frame_index": idx,
                        "warmup": int(es_warmup),
                        "jpeg_max_long_side": int(lado),
                        "jpeg_quality": q,
                        "encode_ms": round(dt, 4),
                        "payload_base64_bytes": n_b64,
                    })
            idx += 1
    finally:
        cap.release()

    for clave, tam in tam_b64.items():
        print(f"  [{clave}] payload base64 medio = {statistics.fmean(tam) / 1024.0:.1f} KiB", flush=True)
    return series, filas


def correr_barrido_resize(video: str, max_frames: int = 60) -> dict[str, SerieEtapa]:
    """
    Micro-medicion del pre-proceso puro: ``cv2.cvtColor`` y ``cv2.resize`` (INTER_AREA).

    Sirve para explicar por que un downscale a 720 px cuesta mas que uno a 640 px sobre un
    fotograma 1920x1080: OpenCV tiene una ruta optimizada de INTER_AREA cuando el factor de
    reduccion es entero (1920/640 = 3, 1920/480 = 4, 1920/960 = 2), y la ruta generica,
    mas cara, cuando no lo es (1920/720 = 2.67, 1920/1280 = 1.5).
    """
    path = VIDEOS_DIR / video
    series: dict[str, SerieEtapa] = {}
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {path}")
    idx = 0
    try:
        while idx < max_frames:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            es_warmup = idx < WARMUP_FRAMES

            t0 = time.perf_counter()
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            dt_cvt = (time.perf_counter() - t0) * 1000.0
            if not es_warmup:
                series.setdefault("cvtColor_bgr2rgb_1080p", SerieEtapa()).agregar(dt_cvt)

            for lado in (480, 640, 720, 960, 1280):
                t1 = time.perf_counter()
                downscale_bgr_max_side(rgb, lado)
                dt = (time.perf_counter() - t1) * 1000.0
                if not es_warmup:
                    series.setdefault(f"resize_1080p_a_{lado}", SerieEtapa()).agregar(dt)
            idx += 1
    finally:
        cap.release()
    return series


def escribir_csv(path: Path, filas: list[dict[str, Any]], columnas: list[str]) -> None:
    """Vuelca filas a CSV UTF-8 con finales de linea LF."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        writer = csv.DictWriter(fh, fieldnames=columnas, lineterminator="\n")
        writer.writeheader()
        for fila in filas:
            writer.writerow(fila)


def main() -> int:
    if not MODEL_PATH.is_file():
        print(f"ERROR: no existe el modelo {MODEL_PATH}", file=sys.stderr)
        return 1

    configuraciones = [
        ConfiguracionPose(
            nombre="res480_sentadilla",
            video="SentadillaProfunda.mp4",
            target_max_dim=480,
            descripcion="Inferencia a 480 px de lado mayor (mas rapido, menos detalle).",
        ),
        ConfiguracionPose(
            nombre="res640_sentadilla",
            video="SentadillaProfunda.mp4",
            target_max_dim=640,
            descripcion="Configuracion por defecto del servicio (_TARGET_MAX_DIM = 640).",
        ),
        ConfiguracionPose(
            nombre="res960_sentadilla",
            video="SentadillaProfunda.mp4",
            target_max_dim=960,
            descripcion="Inferencia a 960 px de lado mayor.",
        ),
        ConfiguracionPose(
            nombre="res1280_sentadilla",
            video="SentadillaProfunda.mp4",
            target_max_dim=1280,
            descripcion="Inferencia a 1280 px de lado mayor.",
        ),
        ConfiguracionPose(
            nombre="prod_heavy_sentadilla",
            video="SentadillaProfunda.mp4",
            target_max_dim=640,
            decode_max_side=720,
            descripcion=(
                "Replica del plan automatico tier heavy: downscale de decodificacion a 720 px "
                "y luego inferencia a 640 px."
            ),
        ),
        ConfiguracionPose(
            nombre="res640_running_360p",
            video="Running.mp4",
            target_max_dim=640,
            max_frames=183,
            descripcion="Video nativo 640x360 (tier light): la inferencia no requiere downscale.",
        ),
        ConfiguracionPose(
            nombre="modo_imagen_640_sentadilla",
            video="SentadillaProfunda.mp4",
            target_max_dim=640,
            modo="imagen",
            descripcion=(
                "Control: RunningMode.IMAGE (deteccion completa por fotograma, sin tracking "
                "temporal). Cuantifica el ahorro que aporta RunningMode.VIDEO."
            ),
        ),
    ]

    todas_las_filas: list[dict[str, Any]] = []
    agregados: list[dict[str, Any]] = []

    print("== Nivel A: desglose por etapa ==", flush=True)
    for cfg in configuraciones:
        w, h, fps, n = geometria_video(VIDEOS_DIR / cfg.video)
        print(
            f"\n-> {cfg.nombre}: {cfg.video} {w}x{h} @ {fps:.2f} fps ({n} fotogramas declarados)",
            flush=True,
        )
        t_ini = time.perf_counter()
        series, filas = correr_configuracion_pose(cfg)
        dur = time.perf_counter() - t_ini
        print(f"  duracion de la pasada: {dur:.1f} s", flush=True)
        todas_las_filas.extend(filas)

        total_media = resumen(series["total_sin_preview"].valores)["media"]
        for etapa, serie in series.items():
            r = resumen(serie.valores)
            pct = (r["media"] / total_media * 100.0) if (total_media and total_media > 0) else float("nan")
            agregados.append({
                "nivel": "A",
                "bloque": "pose",
                "configuracion": cfg.nombre,
                "video": cfg.video,
                "parametros": (
                    f"modo={cfg.modo}; target_max_dim={cfg.target_max_dim}"
                    + (f"; decode_max_side={cfg.decode_max_side}" if cfg.decode_max_side else "")
                ),
                "metrica": etapa,
                "n": r["n"],
                "media_ms": round(r["media"], 3),
                "p50_ms": round(r["p50"], 3),
                "p95_ms": round(r["p95"], 3),
                "p99_ms": round(r["p99"], 3),
                "max_ms": round(r["max"], 3),
                "pct_del_total": ("" if etapa == "total_sin_preview" else round(pct, 2)),
            })

    print("\n== Nivel A: micro-medicion de pre-proceso (cvtColor / resize) ==", flush=True)
    series_resize = correr_barrido_resize("SentadillaProfunda.mp4", max_frames=60)
    for clave, serie in sorted(series_resize.items()):
        r = resumen(serie.valores)
        print(f"  [{clave}] media={r['media']:.3f} ms p95={r['p95']:.3f} ms", flush=True)
        agregados.append({
            "nivel": "A",
            "bloque": "preproceso",
            "configuracion": clave,
            "video": "SentadillaProfunda.mp4",
            "parametros": "fuente=1920x1080; interpolacion=INTER_AREA",
            "metrica": "preproceso_opencv",
            "n": r["n"],
            "media_ms": round(r["media"], 3),
            "p50_ms": round(r["p50"], 3),
            "p95_ms": round(r["p95"], 3),
            "p99_ms": round(r["p99"], 3),
            "max_ms": round(r["max"], 3),
            "pct_del_total": "",
        })

    print("\n== Nivel A: barrido de calidad JPEG de vista previa ==", flush=True)
    series_jpeg, filas_jpeg = correr_barrido_jpeg("SentadillaProfunda.mp4")
    for clave, serie in sorted(series_jpeg.items()):
        r = resumen(serie.valores)
        partes = clave.split("_")
        agregados.append({
            "nivel": "A",
            "bloque": "preview_jpeg",
            "configuracion": clave,
            "video": "SentadillaProfunda.mp4",
            "parametros": f"quality={partes[1][1:]}; max_long_side={partes[2][4:]}",
            "metrica": "codificacion_jpeg",
            "n": r["n"],
            "media_ms": round(r["media"], 3),
            "p50_ms": round(r["p50"], 3),
            "p95_ms": round(r["p95"], 3),
            "p99_ms": round(r["p99"], 3),
            "max_ms": round(r["max"], 3),
            "pct_del_total": "",
        })

    cols_frames = [
        "configuracion", "video", "frame_index", "warmup", "lectura_ms",
        "downscale_decode_ms", "inferencia_pose_ms", "calculo_angulos_ms",
        "total_sin_preview_ms", "pose_detectada",
        "left_knee_flexion_angle_deg", "right_knee_flexion_angle_deg",
    ]
    escribir_csv(RESULTS_DIR / "exp4a_frames.csv", todas_las_filas, cols_frames)
    escribir_csv(
        RESULTS_DIR / "exp4a_jpeg_frames.csv",
        filas_jpeg,
        ["video", "frame_index", "warmup", "jpeg_max_long_side", "jpeg_quality",
         "encode_ms", "payload_base64_bytes"],
    )
    cols_agg = [
        "nivel", "bloque", "configuracion", "video", "parametros", "metrica",
        "n", "media_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms", "pct_del_total",
    ]
    escribir_csv(RESULTS_DIR / "exp4a_agregados.csv", agregados, cols_agg)

    print(
        "\nArchivos escritos:\n"
        f"  {RESULTS_DIR / 'exp4a_frames.csv'}\n"
        f"  {RESULTS_DIR / 'exp4a_jpeg_frames.csv'}\n"
        f"  {RESULTS_DIR / 'exp4a_agregados.csv'}",
        flush=True,
    )
    print(
        f"\nHardware: {platform.platform()} | {platform.machine()} | "
        f"Python {platform.python_version()} | OpenCV {cv2.__version__} | NumPy {np.__version__}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
