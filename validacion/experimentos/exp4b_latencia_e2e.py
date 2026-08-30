#!/usr/bin/env python3
"""
Experimento 4 - Nivel B: latencia extremo a extremo sobre ``/ws/pose-stream``.

Levanta el backend real con uvicorn, espera a que responda ``GET /api/v1/health`` y ejecuta
una matriz de configuraciones. Por cada configuracion se hacen dos mediciones complementarias:

1. **Desglose del servidor**: se invoca ``backend/scripts/profile_pose_stream.py`` (el
   perfilador que ya existe en el repositorio), que activa ``diagnostics: true`` y agrega
   ``consumer_timing_ms`` y ``pipeline_ms``. Su salida en Markdown se parsea a filas.
2. **Latencia de entrega medida en el cliente**: un cliente WebSocket minimo que compara el
   reloj de pared del cliente al recibir el mensaje con el campo ``server_ts_ms`` del payload.
   Como cliente y servidor corren en la misma maquina comparten reloj, asi que la diferencia
   es una latencia de una sola via valida. ``server_ts_ms`` se sella en
   ``build_frame_payload_v1`` justo despues de extraer la pose, de modo que esta metrica
   captura exactamente lo que el reporte previo no tenia desglosado: codificacion JPEG,
   serializacion JSON, envio por el socket y parseo en el cliente.

Tambien registra el tamano en bytes de cada mensaje JSON, que es el coste real que introduce
la vista previa en el enlace.

Ejecucion (desde la carpeta ``backend/``)::

    PYTHONPATH=. ~/.venvs/biomotion/bin/python \
        ../validacion/experimentos/exp4b_latencia_e2e.py
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import signal
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import websockets

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ROOT = _REPO_ROOT / "backend"
RESULTS_DIR = _REPO_ROOT / "validacion" / "resultados"
PERFILADOR = _BACKEND_ROOT / "scripts" / "profile_pose_stream.py"

PUERTO = 8077
BASE_URL = f"http://127.0.0.1:{PUERTO}"
WS_URI = f"ws://127.0.0.1:{PUERTO}/ws/pose-stream"

VIDEO_PESADO = "SentadillaProfunda.mp4"   # 1920x1080 @ 25.07 fps -> tier "heavy"
VIDEO_LIGERO = "Running.mp4"              # 640x360 @ 29.99 fps  -> tier "light"

WARMUP_FRAMES = 5


@dataclass
class Corrida:
    """Una configuracion del stream a perfilar."""

    nombre: str
    video: str
    target_fps: float
    include_preview: bool = True
    preview_fps: int = 10
    jpeg_quality: int = 84
    full_analysis: bool = False
    max_frames: int = 300
    medir_e2e: bool = False
    descripcion: str = ""

    def parametros(self) -> str:
        return (
            f"target_fps={self.target_fps:g}; preview={self.include_preview}; "
            f"preview_fps={self.preview_fps}; jpeg_quality={self.jpeg_quality}; "
            f"capture_only={not self.full_analysis}"
        )

    def config_ws(self) -> dict[str, Any]:
        """Mismo primer mensaje que construye ``profile_pose_stream.py``."""
        return {
            "source": "file",
            "video_filename": self.video,
            "target_fps": self.target_fps,
            "include_preview": self.include_preview,
            "capture_only": not self.full_analysis,
            "diagnostics": True,
            "preview_fps": self.preview_fps,
            "preview_jpeg_quality": self.jpeg_quality,
        }


def percentil(valores_ordenados: list[float], p: float) -> float:
    """Percentil por interpolacion lineal sobre lista ordenada."""
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
    """Media, p50, p95, p99 y maximo."""
    if not valores:
        return {"n": 0, "media": float("nan"), "p50": float("nan"), "p95": float("nan"),
                "p99": float("nan"), "max": float("nan")}
    s = sorted(valores)
    return {
        "n": len(s),
        "media": statistics.fmean(s),
        "p50": percentil(s, 50.0),
        "p95": percentil(s, 95.0),
        "p99": percentil(s, 99.0),
        "max": s[-1],
    }


# ---------------------------------------------------------------- ciclo de vida del servidor

def arrancar_backend(log_path: Path) -> subprocess.Popen:
    """Lanza uvicorn en segundo plano con el mismo entorno que usa el equipo en desarrollo."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fh = log_path.open("w", encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_BACKEND_ROOT)
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PUERTO),
         "--host", "127.0.0.1", "--log-level", "info"],
        cwd=str(_BACKEND_ROOT),
        env=env,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return proc


def esperar_health(timeout_s: float = 90.0) -> dict[str, Any]:
    """Sondea ``GET /api/v1/health`` hasta que responda 200 o se agote el tiempo."""
    t0 = time.perf_counter()
    ultimo_error = ""
    while time.perf_counter() - t0 < timeout_s:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/api/v1/health", timeout=3.0) as resp:
                cuerpo = resp.read().decode("utf-8")
                if resp.status == 200:
                    return {
                        "ok": True,
                        "segundos": round(time.perf_counter() - t0, 2),
                        "cuerpo": cuerpo,
                    }
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            ultimo_error = str(exc)
        time.sleep(0.5)
    return {"ok": False, "segundos": round(time.perf_counter() - t0, 2), "error": ultimo_error}


def detener_backend(proc: subprocess.Popen) -> None:
    """Cierra el grupo de procesos de uvicorn (SIGTERM y, si insiste, SIGKILL)."""
    if proc.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=10)


# ------------------------------------------------------------------ perfilador del repositorio

_RE_INTERVALO = re.compile(
    r"Intervalo entre mensajes \(cliente, ms\): n=(\d+) mean=([\d.]+) p50=([\d.]+) "
    r"p95=([\d.]+) p99=([\d.]+) max=([\d.]+)"
)


def ejecutar_perfilador(corrida: Corrida) -> tuple[str, list[dict[str, Any]]]:
    """
    Invoca ``scripts/profile_pose_stream.py`` y convierte sus tablas Markdown en filas.

    Devuelve (salida cruda, filas). Cada fila corresponde a una metrica de
    ``consumer_timing_ms`` o ``pipeline_ms``, o al intervalo entre mensajes del cliente.
    """
    cmd = [
        sys.executable, str(PERFILADOR),
        "--base-url", BASE_URL,
        "--video", corrida.video,
        "--fps", str(corrida.target_fps),
        "--max-frames", str(corrida.max_frames),
        "--preview-fps", str(corrida.preview_fps),
        "--jpeg-quality", str(corrida.jpeg_quality),
        "--warmup-frames", str(WARMUP_FRAMES),
        "--outlier-ms", "100",
    ]
    if not corrida.include_preview:
        cmd.append("--no-preview")
    if corrida.full_analysis:
        cmd.append("--full-analysis")

    env = dict(os.environ)
    env["PYTHONPATH"] = str(_BACKEND_ROOT)
    proc = subprocess.run(
        cmd, cwd=str(_BACKEND_ROOT), env=env, capture_output=True, text=True, timeout=600
    )
    salida = proc.stdout
    filas: list[dict[str, Any]] = []

    seccion = ""
    for linea in salida.splitlines():
        linea = linea.strip()
        m = _RE_INTERVALO.search(linea)
        if m:
            filas.append({
                "bloque": "cliente",
                "metrica": "intervalo_entre_mensajes",
                "n": int(m.group(1)),
                "media_ms": float(m.group(2)),
                "p50_ms": float(m.group(3)),
                "p95_ms": float(m.group(4)),
                "p99_ms": float(m.group(5)),
                "max_ms": float(m.group(6)),
            })
            continue
        if linea.startswith("## "):
            titulo = linea[3:]
            seccion = "consumer_timing_ms" if "consumer" in titulo else "pipeline_ms"
            continue
        if not linea.startswith("|") or not seccion:
            continue
        partes = [p.strip() for p in linea.strip("|").split("|")]
        if len(partes) < 7 or partes[0] in ("métrica", "metrica") or partes[0].startswith("---"):
            continue
        try:
            filas.append({
                "bloque": seccion,
                "metrica": partes[0],
                "n": int(partes[1]),
                "media_ms": float(partes[2]),
                "p50_ms": float(partes[3]),
                "p95_ms": float(partes[4]),
                "p99_ms": float(partes[5]),
                "max_ms": float(partes[6]),
            })
        except ValueError:
            continue
    if proc.returncode != 0:
        print(f"    AVISO: el perfilador salio con codigo {proc.returncode}", flush=True)
        print(f"    stderr: {proc.stderr[-400:]}", flush=True)
    return salida, filas


# ------------------------------------------------------------------- cliente de latencia real

async def _cliente_e2e(corrida: Corrida) -> dict[str, list[float]]:
    """
    Cliente WebSocket minimo que mide la latencia de entrega real por fotograma.

    ``latencia_entrega_ms`` = reloj del cliente al recibir - ``server_ts_ms`` del payload.
    """
    series: dict[str, list[float]] = {
        "latencia_entrega_ms": [],
        "intervalo_llegada_ms": [],
        "tamano_payload_kib": [],
    }
    prev_rx: float | None = None
    n_validos = 0
    async with websockets.connect(WS_URI, max_size=None) as ws:
        await ws.send(json.dumps(corrida.config_ws()))
        while True:
            raw = await ws.recv()
            t_rx = time.time() * 1000.0
            data = json.loads(raw)
            if data.get("stream_done"):
                break
            if data.get("error"):
                continue
            if data.get("frame_index") is None or "landmarks" not in data:
                continue
            n_validos += 1
            sts = data.get("server_ts_ms")
            if n_validos > WARMUP_FRAMES and isinstance(sts, (int, float)):
                series["latencia_entrega_ms"].append(t_rx - float(sts))
                series["tamano_payload_kib"].append(len(raw.encode("utf-8")) / 1024.0)
                if prev_rx is not None:
                    series["intervalo_llegada_ms"].append(t_rx - prev_rx)
            prev_rx = t_rx
            if n_validos >= corrida.max_frames:
                break
    return series


def medir_e2e(corrida: Corrida) -> dict[str, list[float]]:
    """Envoltorio sincrono de :func:`_cliente_e2e`."""
    return asyncio.run(_cliente_e2e(corrida))


# ------------------------------------------------------------------------------------ matriz

def construir_matriz() -> list[Corrida]:
    """
    Matriz de configuraciones.

    Extiende la propuesta en ``docs/guias/reporte_latencia_frames_ws_pose_stream.md``
    (target_fps 8/10/12, preview_fps 8/10/12, calidad JPEG 76/84/90) con un video ligero
    y con corridas sin vista previa para aislar el coste del JPEG en el enlace.
    """
    return [
        Corrida("pesado_fps8_preview", VIDEO_PESADO, 8, medir_e2e=False,
                descripcion="Barrido de throttle: 8 FPS objetivo."),
        Corrida("pesado_fps10_preview", VIDEO_PESADO, 10, medir_e2e=True,
                descripcion="Barrido de throttle: 10 FPS objetivo (preset de referencia)."),
        Corrida("pesado_fps12_preview", VIDEO_PESADO, 12, medir_e2e=False,
                descripcion="Barrido de throttle: 12 FPS objetivo."),
        Corrida("pesado_fps15_preview", VIDEO_PESADO, 15, medir_e2e=True,
                descripcion="Barrido de throttle: 15 FPS objetivo (por encima del techo del tier heavy)."),
        Corrida("pesado_fps10_sinpreview", VIDEO_PESADO, 10, include_preview=False, medir_e2e=True,
                descripcion="Aisla el coste de la vista previa en el enlace."),
        Corrida("pesado_fps15_sinpreview", VIDEO_PESADO, 15, include_preview=False, medir_e2e=False,
                descripcion="Sin vista previa a 15 FPS objetivo."),
        Corrida("pesado_fps10_q76", VIDEO_PESADO, 10, jpeg_quality=76, medir_e2e=False,
                descripcion="Barrido de calidad JPEG: 76."),
        Corrida("pesado_fps10_q90", VIDEO_PESADO, 10, jpeg_quality=90, medir_e2e=False,
                descripcion="Barrido de calidad JPEG: 90."),
        Corrida("pesado_fps12_pf8", VIDEO_PESADO, 12, preview_fps=8, medir_e2e=False,
                descripcion="Barrido de preview_fps: 8."),
        Corrida("pesado_fps12_pf12", VIDEO_PESADO, 12, preview_fps=12, medir_e2e=False,
                descripcion="Barrido de preview_fps: 12."),
        Corrida("pesado_fps10_analisis_completo", VIDEO_PESADO, 10, full_analysis=True, medir_e2e=False,
                descripcion="Motor completo (features + clasificador + rep tracker) en vez de capture_only."),
        Corrida("ligero_fps10_preview", VIDEO_LIGERO, 10, max_frames=150, medir_e2e=False,
                descripcion="Video 640x360 (tier light) a 10 FPS objetivo."),
        Corrida("ligero_fps15_preview", VIDEO_LIGERO, 15, max_frames=150, medir_e2e=True,
                descripcion="Video 640x360 a 15 FPS objetivo."),
        Corrida("ligero_fps15_sinpreview", VIDEO_LIGERO, 15, include_preview=False, max_frames=150,
                medir_e2e=False, descripcion="Video 640x360 sin vista previa."),
        Corrida("ligero_fps30_preview", VIDEO_LIGERO, 30, max_frames=150, medir_e2e=True,
                descripcion="Video 640x360 a 30 FPS objetivo: busca el techo real de la maquina."),
    ]


def escribir_csv(path: Path, filas: list[dict[str, Any]], columnas: list[str]) -> None:
    """Vuelca filas a CSV UTF-8 con finales de linea LF."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        writer = csv.DictWriter(fh, fieldnames=columnas, lineterminator="\n")
        writer.writeheader()
        for fila in filas:
            writer.writerow(fila)


def main() -> int:
    ap = argparse.ArgumentParser(description="Experimento 4 Nivel B: latencia extremo a extremo")
    ap.add_argument("--sin-servidor", action="store_true",
                    help="No levanta uvicorn; asume que ya hay un backend escuchando en el puerto.")
    args = ap.parse_args()

    log_uvicorn = RESULTS_DIR / "exp4b_uvicorn.log"
    proc: subprocess.Popen | None = None
    agregados: list[dict[str, Any]] = []
    salidas_perfilador: list[str] = []

    try:
        if not args.sin_servidor:
            print(f"Levantando uvicorn en el puerto {PUERTO} ...", flush=True)
            proc = arrancar_backend(log_uvicorn)
            estado = esperar_health()
            if not estado["ok"]:
                print(f"ERROR: el backend no respondio /api/v1/health en {estado['segundos']} s",
                      file=sys.stderr)
                print(f"Ultimo error: {estado.get('error')}", file=sys.stderr)
                cola = log_uvicorn.read_text(encoding="utf-8", errors="replace")[-3000:]
                print(f"--- cola del log de uvicorn ---\n{cola}", file=sys.stderr)
                return 2
            print(f"Backend arriba en {estado['segundos']} s -> {estado['cuerpo']}", flush=True)
        else:
            estado = esperar_health(timeout_s=10.0)
            if not estado["ok"]:
                print("ERROR: no hay backend escuchando", file=sys.stderr)
                return 2

        for corrida in construir_matriz():
            print(f"\n-> {corrida.nombre} | {corrida.video} | {corrida.parametros()}", flush=True)

            t0 = time.perf_counter()
            salida, filas = ejecutar_perfilador(corrida)
            dur = time.perf_counter() - t0
            salidas_perfilador.append(f"===== {corrida.nombre} =====\n{salida}")
            print(f"   perfilador: {dur:.1f} s, {len(filas)} metricas", flush=True)
            for fila in filas:
                agregados.append({
                    "nivel": "B",
                    "bloque": fila["bloque"],
                    "configuracion": corrida.nombre,
                    "video": corrida.video,
                    "parametros": corrida.parametros(),
                    "metrica": fila["metrica"],
                    "n": fila["n"],
                    "media_ms": round(fila["media_ms"], 3),
                    "p50_ms": round(fila["p50_ms"], 3),
                    "p95_ms": round(fila["p95_ms"], 3),
                    "p99_ms": round(fila["p99_ms"], 3),
                    "max_ms": round(fila["max_ms"], 3),
                    "pct_del_total": "",
                })

            if corrida.medir_e2e:
                time.sleep(1.0)
                t0 = time.perf_counter()
                series = medir_e2e(corrida)
                dur = time.perf_counter() - t0
                lat = resumen(series["latencia_entrega_ms"])
                print(
                    f"   cliente e2e: {dur:.1f} s | latencia entrega media={lat['media']:.2f} ms "
                    f"p95={lat['p95']:.2f} ms | payload medio="
                    f"{statistics.fmean(series['tamano_payload_kib']):.1f} KiB",
                    flush=True,
                )
                for metrica, valores in series.items():
                    r = resumen(valores)
                    agregados.append({
                        "nivel": "B",
                        "bloque": "cliente_e2e",
                        "configuracion": corrida.nombre,
                        "video": corrida.video,
                        "parametros": corrida.parametros(),
                        "metrica": metrica,
                        "n": r["n"],
                        "media_ms": round(r["media"], 3),
                        "p50_ms": round(r["p50"], 3),
                        "p95_ms": round(r["p95"], 3),
                        "p99_ms": round(r["p99"], 3),
                        "max_ms": round(r["max"], 3),
                        "pct_del_total": "",
                    })
            time.sleep(1.0)

    finally:
        if proc is not None:
            print("\nDeteniendo uvicorn ...", flush=True)
            detener_backend(proc)
            print(f"uvicorn detenido (codigo {proc.poll()})", flush=True)

    cols = ["nivel", "bloque", "configuracion", "video", "parametros", "metrica",
            "n", "media_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms", "pct_del_total"]
    escribir_csv(RESULTS_DIR / "exp4b_agregados.csv", agregados, cols)
    (RESULTS_DIR / "exp4b_perfilador_salida.txt").write_text(
        "\n".join(salidas_perfilador), encoding="utf-8"
    )

    # Plan de procesamiento que el servidor eligio en cada sesion (log de uvicorn).
    if log_uvicorn.is_file():
        planes = [
            l.strip() for l in log_uvicorn.read_text(encoding="utf-8", errors="replace").splitlines()
            if "perfil de" in l
        ]
        vistos: list[str] = []
        for p in planes:
            cuerpo = p.split("perfil de", 1)[1]
            if cuerpo not in vistos:
                vistos.append(cuerpo)
        print("\nPlanes de procesamiento observados en el servidor:", flush=True)
        for v in vistos:
            print(f"  {v}", flush=True)

    print(
        f"\nArchivos escritos:\n  {RESULTS_DIR / 'exp4b_agregados.csv'}\n"
        f"  {RESULTS_DIR / 'exp4b_perfilador_salida.txt'}\n  {log_uvicorn}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
