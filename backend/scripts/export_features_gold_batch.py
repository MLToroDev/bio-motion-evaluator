#!/usr/bin/env python3
"""
Exporta vectores 32D desde **todos** los vídeos gold-standard bajo ``tests/assets/videos/``
(hay que ejecutarlo con el Python del venv del backend, igual que ``export_features_from_video.py``).

Etiqueta por archivo, en orden de prioridad:

1. Entrada en ``video_labels.json`` (ruta con ``--labels`` o, por defecto,
   ``<gold_dir>/video_labels.json`` si existe).
2. Heurística por nombre de archivo (p. ej. ``squat``, ``lunge``, ``running``).
3. ``--default-label`` (por defecto ``unknown``).

Salida: un único CSV (``f0``…``f31`` + ``label``) compatible con
``train_exercise_classifier_from_csv.py``.

Ejemplo::

    .venv\\Scripts\\python scripts/export_features_gold_batch.py --out data/gold_all.csv --only-window-full
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = Path(__file__).resolve().parent
for _p in (_BACKEND_ROOT, _SCRIPTS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from app.config import Settings, settings
    from app.models.schemas import ExerciseClassifierConfig
    from export_features_from_video import _open_csv_writer, export_gold_video_features_to_writer
    from vision.paths import list_gold_standard_video_filenames
except ModuleNotFoundError as exc:
    name = getattr(exc, "name", None) or str(exc)
    print(
        f"Falta el módulo '{name}' (¿venv activado / ``pip install -r requirements.txt``?).\n"
        f"Intérprete: {sys.executable}\n",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


def _load_label_map(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {}
    inner = data.get("labels") if isinstance(data.get("labels"), dict) else data
    out: dict[str, str] = {}
    for k, v in inner.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        name = Path(k.strip()).name
        if name:
            out[name] = v.strip()
    return out


def _infer_label_from_filename(filename: str) -> str | None:
    stem = Path(filename).stem.lower()
    if any(x in stem for x in ("squat", "sentadilla")):
        return "squat"
    if any(x in stem for x in ("lunge", "zancada", "estocada")):
        return "lunge"
    if any(x in stem for x in ("run", "running", "carrera", "correr", "jog")):
        return "running"
    if any(x in stem for x in ("walk", "camin")):
        return "walk"
    if any(x in stem for x in ("jump", "salto")):
        return "jump"
    return None


def _resolve_label(filename: str, label_map: dict[str, str], default: str) -> str:
    if filename in label_map:
        return label_map[filename]
    inferred = _infer_label_from_filename(filename)
    return inferred if inferred is not None else default


def main() -> None:
    p = argparse.ArgumentParser(
        description="Exporta features 32D de todos los vídeos gold-standard a un CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Directorio gold: {Settings.gold_standard_videos_dir()}",
    )
    p.add_argument("--out", type=Path, required=True, help="CSV combinado (f0..f31,label)")
    p.add_argument(
        "--labels",
        type=Path,
        default=None,
        help="JSON de mapeo archivo→etiqueta (por defecto: <gold>/video_labels.json si existe)",
    )
    p.add_argument(
        "--default-label",
        default="unknown",
        help="Etiqueta si no hay entrada en JSON ni heurística (default: unknown)",
    )
    p.add_argument(
        "--window-size",
        type=int,
        default=None,
        help="Tamaño ventana FeatureEngine (default: settings)",
    )
    p.add_argument("--only-window-full", action="store_true", help="Solo filas con ventana llena")
    p.add_argument("--emit-every", type=int, default=1, help="1 de cada N frames (post-filtros)")
    p.add_argument("--require-pose-ok", action="store_true", help="Omitir frames sin pose_ok")
    p.add_argument("--max-frames", type=int, default=0, help="Máx. frames por vídeo (0 = completo)")
    p.add_argument(
        "--append",
        action="store_true",
        help="Añadir al CSV existente (cabecera solo si el archivo está vacío)",
    )
    args = p.parse_args()

    if args.emit_every < 1:
        p.error("--emit-every debe ser >= 1")

    gold = Settings.gold_standard_videos_dir()
    filenames = list_gold_standard_video_filenames(gold)
    if not filenames:
        raise SystemExit(f"No hay vídeos en {gold} (extensiones .mp4, .mov, .avi, .mkv, .webm).")

    if args.labels is not None:
        if not args.labels.is_file():
            raise SystemExit(f"No se encontró el archivo --labels: {args.labels}")
        labels_path = args.labels.resolve()
    else:
        candidate = gold / "video_labels.json"
        labels_path = candidate if candidate.is_file() else None

    label_map = _load_label_map(labels_path)

    cfg: ExerciseClassifierConfig = settings.exercise_classifier_config()
    if args.window_size is not None:
        cfg = cfg.model_copy(update={"window_size_frames": max(2, int(args.window_size))})

    model_path = settings.resolve_model_path(_BACKEND_ROOT)
    if not model_path.is_file():
        raise SystemExit(f"Modelo pose no encontrado: {model_path}")

    writer, fh = _open_csv_writer(args.out, append=args.append)
    total_rows = 0
    summary: list[tuple[str, str, int, int]] = []

    try:
        for name in filenames:
            label = _resolve_label(name, label_map, args.default_label.strip() or "unknown")
            rows, frames = export_gold_video_features_to_writer(
                video_filename=name,
                gold_dir=gold,
                label=label,
                writer=writer,
                classifier_cfg=cfg,
                model_path=model_path,
                only_window_full=args.only_window_full,
                require_pose_ok=args.require_pose_ok,
                emit_every=args.emit_every,
                max_frames=args.max_frames,
            )
            total_rows += rows
            summary.append((name, label, rows, frames))
    finally:
        fh.close()

    print(f"CSV combinado: {args.out.resolve()} — {total_rows} filas en total, {len(filenames)} vídeos.")
    for name, label, rows, frames in summary:
        print(f"  {name!r} label={label!r} rows={rows} frames_read={frames}")


if __name__ == "__main__":
    main()
