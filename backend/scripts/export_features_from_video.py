#!/usr/bin/env python3
"""
Exporta vectores de 32 features (mismo formato que ``FeatureEngine.build_feature_vector()``)
desde un vídeo **gold standard** bajo ``tests/assets/videos/``, con etiqueta fija por CLI
o por **tramos temporales** (`--segments` JSON).

Salida CSV compatible con ``scripts/train_exercise_classifier_from_csv.py`` (columnas ``f0``…``f31`` + ``label``).

Ejemplo etiqueta única::

    .venv\\Scripts\\python scripts/export_features_from_video.py --video clip.mp4 --label squat --out data/squat_rows.csv

Tramos (``start_sec`` / ``end_sec`` / ``label`` en segundos de vídeo)::

    .venv\\Scripts\\python scripts/export_features_from_video.py --video clip.mp4 --segments segments.json --out data/mixed.csv --only-window-full

Acumular en el mismo CSV::

    .venv\\Scripts\\python scripts/export_features_from_video.py --video otro.mp4 --label squat --out data/squat_rows.csv --append

Requisitos: ``pip install -r requirements.txt`` en el venv; ``.env`` y modelo ``.task`` en ``models/`` (igual que el API).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

# Ejecutar desde ``backend/`` (como el resto de scripts del proyecto).
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

try:
    import cv2

    from app.config import Settings, settings
    from app.models.schemas import ExerciseClassifierConfig
    from vision.feature_engine import FEATURE_VECTOR_DIM, FeatureEngine
    from vision.paths import resolve_gold_standard_video
    from vision.pose_extractor import extract_pose_bgr_video
    from vision.processor import VideoSource
except ModuleNotFoundError as exc:
    name = getattr(exc, "name", None) or str(exc)
    print(
        f"Falta el módulo '{name}' (¿estás usando el Python del sistema en lugar del venv?).\n\n"
        f"Intérprete actual: {sys.executable}\n\n"
        "Desde la carpeta backend:\n"
        "  .venv\\Scripts\\python scripts\\export_features_from_video.py ...\n"
        "o activa el venv e instala:\n"
        "  pip install -r requirements.txt\n",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


def _label_at_time_sec(t_sec: float, segments: list[dict[str, Any]] | None, fixed_label: str) -> str | None:
    """Etiqueta por tiempo; ``segments`` con ``start_sec``, ``end_sec``, ``label``. Fuera de tramos → None."""
    if not segments:
        return fixed_label.strip() if fixed_label.strip() else None
    for seg in segments:
        lo = float(seg["start_sec"])
        hi = float(seg["end_sec"])
        if lo <= t_sec <= hi:
            lab = str(seg.get("label", "")).strip()
            return lab if lab else None
    return None


def export_gold_video_features_to_writer(
    *,
    video_filename: str,
    gold_dir: Path,
    label: str,
    writer: csv.writer,
    classifier_cfg: ExerciseClassifierConfig,
    model_path: Path,
    only_window_full: bool,
    require_pose_ok: bool,
    emit_every: int,
    max_frames: int,
    segments: list[dict[str, Any]] | None = None,
) -> tuple[int, int]:
    """
    Procesa un vídeo gold-standard y escribe filas ``f0..f31,label`` en ``writer``.
    Reinicia el ancla temporal de MediaPipe VIDEO al inicio (seguro entre clips en batch).
    Devuelve ``(filas_escritas, frames_leídos)``.
    """
    from app.services.pose.mediapipe import reset_pose_video_timestamp_anchor

    video_path = resolve_gold_standard_video(video_filename, gold_dir)
    if not video_path.is_file():
        raise FileNotFoundError(str(video_path))

    reset_pose_video_timestamp_anchor()
    engine = FeatureEngine(classifier_cfg)
    rows_out = 0
    frames_read = 0
    emit_counter = 0

    with VideoSource(source_type="file", file_path=str(video_path), loop_file=False) as src:
        cap = src._cap
        fps = float(cap.get(cv2.CAP_PROP_FPS)) if cap is not None else 0.0
        if fps <= 1.0 or fps > 240.0:
            fps = 30.0
        dt_s = 1.0 / fps

        while True:
            if max_frames and frames_read >= max_frames:
                break
            bgr = src.get_frame()
            if bgr is None:
                break

            ts_ms = int(round(frames_read * (1000.0 / fps)))
            pose = extract_pose_bgr_video(bgr, model_path, ts_ms)
            engine.push(pose, dt_s)
            frames_read += 1

            if require_pose_ok and not pose.ok:
                continue
            if only_window_full and not engine.window_full():
                continue

            emit_counter += 1
            if emit_counter % emit_every != 0:
                continue

            vec = engine.build_feature_vector()
            if vec.shape[0] != FEATURE_VECTOR_DIM:
                raise RuntimeError(f"vector dim {vec.shape[0]} != {FEATURE_VECTOR_DIM}")
            t_sec = max(0.0, (frames_read - 1) / fps)
            row_label = _label_at_time_sec(t_sec, segments, label)
            if row_label is None:
                continue
            row = [f"{float(vec[i]):.10g}" for i in range(FEATURE_VECTOR_DIM)] + [row_label]
            writer.writerow(row)
            rows_out += 1

    return rows_out, frames_read


def _open_csv_writer(
    path: Path,
    *,
    append: bool,
) -> tuple[csv.writer, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not append or not path.is_file() or path.stat().st_size == 0
    f = path.open("a" if append and path.is_file() else "w", encoding="utf-8", newline="")
    w = csv.writer(f)
    if write_header:
        w.writerow([f"f{i}" for i in range(FEATURE_VECTOR_DIM)] + ["label"])
    return w, f


def main() -> None:
    p = argparse.ArgumentParser(
        description="Exporta features 32D desde MP4 gold-standard a CSV para entrenar clasificador",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Directorio gold standard: {Settings.gold_standard_videos_dir()}",
    )
    p.add_argument(
        "--video",
        required=True,
        help="Nombre del archivo solo (p. ej. squat_test.mp4) bajo tests/assets/videos/",
    )
    p.add_argument(
        "--label",
        default="",
        help="Etiqueta fija por filas (si no se usa --segments). Obligatoria sin --segments.",
    )
    p.add_argument(
        "--segments",
        type=Path,
        default=None,
        help='JSON lista de tramos: [{"start_sec":0,"end_sec":5,"label":"idle"},...]',
    )
    p.add_argument("--out", type=Path, required=True, help="CSV de salida (f0..f31,label)")
    p.add_argument("--append", action="store_true", help="Añade filas sin reescribir cabecera si el archivo ya existe")
    p.add_argument(
        "--window-size",
        type=int,
        default=None,
        help="Tamaño ventana FeatureEngine (por defecto: classifier_window_size_frames del settings)",
    )
    p.add_argument(
        "--only-window-full",
        action="store_true",
        help="Solo escribe filas cuando la ventana esté llena (recomendado para entrenamiento)",
    )
    p.add_argument(
        "--emit-every",
        type=int,
        default=1,
        help="Escribir 1 de cada N frames procesados (tras filtros; >=1)",
    )
    p.add_argument(
        "--require-pose-ok",
        action="store_true",
        help="No escribe fila si el frame actual no tiene pose_ok",
    )
    p.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="Detener tras N frames leídos (0 = hasta el fin del vídeo)",
    )
    args = p.parse_args()

    if args.emit_every < 1:
        p.error("--emit-every debe ser >= 1")

    segments_list: list[dict[str, Any]] | None = None
    if args.segments is not None:
        if not args.segments.is_file():
            raise SystemExit(f"No existe --segments: {args.segments}")
        raw_seg = json.loads(args.segments.read_text(encoding="utf-8"))
        if not isinstance(raw_seg, list):
            raise SystemExit("--segments debe ser una lista JSON")
        segments_list = [x for x in raw_seg if isinstance(x, dict)]
        if not segments_list:
            raise SystemExit("--segments está vacío")
    elif not (args.label or "").strip():
        p.error("Indica --label o bien --segments con JSON de tramos")

    gold = Settings.gold_standard_videos_dir()
    video_path = resolve_gold_standard_video(args.video, gold)
    if not video_path.is_file():
        raise SystemExit(f"Vídeo no encontrado: {video_path}")

    cfg: ExerciseClassifierConfig = settings.exercise_classifier_config()
    if args.window_size is not None:
        cfg = cfg.model_copy(update={"window_size_frames": max(2, int(args.window_size))})

    model_path = settings.resolve_model_path(_BACKEND_ROOT)
    if not model_path.is_file():
        raise SystemExit(f"Modelo pose no encontrado: {model_path}")

    writer, fh = _open_csv_writer(args.out, append=args.append)
    try:
        rows_out, frames_read = export_gold_video_features_to_writer(
            video_filename=args.video,
            gold_dir=gold,
            label=args.label or "",
            writer=writer,
            classifier_cfg=cfg,
            model_path=model_path,
            only_window_full=args.only_window_full,
            require_pose_ok=args.require_pose_ok,
            emit_every=args.emit_every,
            max_frames=args.max_frames,
            segments=segments_list,
        )
    finally:
        fh.close()

    lab_info = "segments" if segments_list else repr(args.label)
    print(
        f"Listo: {rows_out} filas → {args.out.resolve()} "
        f"(frames leídos={frames_read}, vídeo={video_path.name}, label={lab_info})"
    )


if __name__ == "__main__":
    main()
