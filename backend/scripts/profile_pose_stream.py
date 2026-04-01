#!/usr/bin/env python3
"""
Perfil de rendimiento de ``/ws/pose-stream``.

Agrega ``consumer_timing_ms`` (servidor, con ``diagnostics: true``) y ``pipeline_ms``
del motor, e imprime tablas mean / p50 / p95 / p99 / max y recuento de outliers
(por defecto valores > 100 ms).

Uso (desde la carpeta ``backend/``, con el API en marcha).
Requiere el paquete ``websockets`` (viene en ``requirements.txt`` del backend).
Usa el mismo Python que el venv del proyecto, por ejemplo::

    .venv\\Scripts\\python scripts\\profile_pose_stream.py --video RunningParcial.mp4 --fps 15 --max-frames 200

Sin vista previa JPEG (aislar MediaPipe + red mínima)::

    python scripts/profile_pose_stream.py --video RunningParcial.mp4 --no-preview
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from typing import Any

try:
    import websockets
except ModuleNotFoundError as exc:
    print(
        "Falta el paquete 'websockets'.\n\n"
        "El backend lo declara en requirements.txt; instálalo en ESTE intérprete:\n"
        f"  {sys.executable} -m pip install \"websockets>=12.0,<14\"\n\n"
        "O activa el venv del backend y ejecuta:\n"
        "  pip install -r requirements.txt\n\n"
        "Luego lanza el script con el Python del venv:\n"
        "  .venv\\Scripts\\python scripts\\profile_pose_stream.py ...\n",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


def _pctl(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p / 100.0
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    if lo == hi:
        return sorted_vals[lo]
    frac = k - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _gather_series(rows: list[dict[str, Any]], key: str) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for row in rows:
        m = row.get(key)
        if not isinstance(m, dict):
            continue
        for k, v in m.items():
            if isinstance(v, (int, float)):
                out.setdefault(str(k), []).append(float(v))
    return out


def _outlier_count(values: list[float], threshold_ms: float) -> int:
    return sum(1 for x in values if x > threshold_ms)


def _print_table(
    title: str,
    series: dict[str, list[float]],
    *,
    outlier_threshold_ms: float,
) -> None:
    print(f"\n## {title}")
    if not series:
        print("(sin datos)")
        return
    thr_col = f">{outlier_threshold_ms:g}ms"
    print(f"| métrica | n | mean | p50 | p95 | p99 | max | {thr_col} |")
    print("|---------|---|------|-----|-----|-----|-----|------|")
    for k in sorted(series.keys()):
        s = sorted(series[k])
        n = len(s)
        oc = _outlier_count(s, outlier_threshold_ms)
        print(
            f"| {k} | {n} | {statistics.mean(s):.2f} | {_pctl(s, 50):.2f} | "
            f"{_pctl(s, 95):.2f} | {_pctl(s, 99):.2f} | {max(s):.2f} | {oc} |"
        )


async def _run(args: argparse.Namespace) -> None:
    base = args.base_url.rstrip("/")
    if base.startswith("http://"):
        base = "ws://" + base[len("http://") :]
    elif base.startswith("https://"):
        base = "wss://" + base[len("https://") :]
    uri = f"{base}/ws/pose-stream"

    capture_only = not args.full_analysis
    cfg: dict[str, Any] = {
        "source": "file",
        "video_filename": args.video,
        "target_fps": args.fps,
        "include_preview": not args.no_preview,
        "capture_only": capture_only,
        "diagnostics": True,
        "preview_fps": args.preview_fps,
        "preview_jpeg_quality": args.jpeg_quality,
    }

    rows: list[dict[str, Any]] = []
    inter_ms: list[float] = []
    prev_mono: float | None = None

    async with websockets.connect(uri, max_size=None) as ws:
        await ws.send(json.dumps(cfg))
        while True:
            mono = asyncio.get_running_loop().time()
            raw = await ws.recv()
            mono_after = asyncio.get_running_loop().time()
            if prev_mono is not None:
                inter_ms.append((mono_after - prev_mono) * 1000.0)
            prev_mono = mono_after

            data = json.loads(raw)
            if data.get("stream_done"):
                break
            if data.get("error"):
                continue
            if data.get("frame_index") is not None and "landmarks" in data:
                rows.append(data)
            if args.max_frames and len(rows) >= args.max_frames:
                break

    warmup = max(0, int(args.warmup_frames))
    rows_eff = rows[warmup:] if warmup else rows
    inter_eff = inter_ms[warmup:] if warmup else inter_ms

    print("# Perfil /ws/pose-stream")
    print(f"- URL: {uri}")
    print(
        f"- Vídeo: {args.video} | target_fps={args.fps} | preview={not args.no_preview} "
        f"| capture_only={capture_only}"
    )
    print(f"- Frames recibidos (válidos): {len(rows)}")
    if warmup:
        print(f"- Warmup descartado: primeros {warmup} frames")
    print(f"- Frames en agregados: {len(rows_eff)}")
    thr = float(args.outlier_ms)
    if inter_eff:
        s = sorted(inter_eff)
        oc_inter = _outlier_count(list(inter_eff), thr)
        print(
            f"- Intervalo entre mensajes (cliente, ms): n={len(inter_eff)} "
            f"mean={statistics.mean(inter_eff):.2f} p50={_pctl(s, 50):.2f} "
            f"p95={_pctl(s, 95):.2f} p99={_pctl(s, 99):.2f} max={max(inter_eff):.2f} "
            f">{thr:g}ms={oc_inter}"
        )
    elif inter_ms and warmup >= len(inter_ms):
        print("- Intervalo entre mensajes: (sin muestras tras warmup; reduce --warmup-frames)")

    if not rows_eff:
        print("\n(sin filas tras warmup; sube --max-frames o baja --warmup-frames)")
    else:
        _print_table(
            "consumer_timing_ms (servidor)",
            _gather_series(rows_eff, "consumer_timing_ms"),
            outlier_threshold_ms=thr,
        )
        _print_table(
            "pipeline_ms (motor)",
            _gather_series(rows_eff, "pipeline_ms"),
            outlier_threshold_ms=thr,
        )

    print(
        "\nInterpretación rápida:\n"
        "- ``p99`` resume la cola sin depender de un único ``max``; la columna ``>umbral`` cuenta outliers (``--outlier-ms``).\n"
        "- ``--warmup-frames`` evita mezclar arranque/GC con el régimen estable.\n"
        "- ``process_bgr_ms`` ≈ costo total del hilo del motor (MediaPipe + análisis si aplica).\n"
        "- ``pipeline_ms.extract`` desglosa la etapa de extracción dentro del motor.\n"
        "- ``jpeg_encode_ms`` sube con preview ON y calidad/resolución.\n"
        "- ``scheduled_sleep_ms`` es el throttle a ``target_fps``; si suele ~0, el cuello es CPU.\n"
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Perfil de latencia pose-stream")
    p.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Origen del API (http(s) o ws(s))",
    )
    p.add_argument("--video", required=True, help="Nombre bajo tests/assets/videos/")
    p.add_argument("--fps", type=float, default=15.0)
    p.add_argument("--max-frames", type=int, default=300)
    p.add_argument("--no-preview", action="store_true", help="Sin JPEG en el payload")
    p.add_argument(
        "--full-analysis",
        action="store_true",
        help="Ejecuta motor completo (clasificador/rep); por defecto solo captura",
    )
    p.add_argument("--preview-fps", type=int, default=10, choices=(8, 10, 12))
    p.add_argument("--jpeg-quality", type=int, default=84)
    p.add_argument(
        "--warmup-frames",
        type=int,
        default=0,
        help="Descarta los primeros N frames válidos antes de agregar (arranque/GC).",
    )
    p.add_argument(
        "--outlier-ms",
        type=float,
        default=100.0,
        help="Umbral en ms para la columna de conteo de outliers en cada métrica.",
    )
    args = p.parse_args()
    if args.warmup_frames < 0:
        p.error("--warmup-frames debe ser >= 0")
    if args.outlier_ms <= 0:
        p.error("--outlier-ms debe ser > 0")
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
