#!/usr/bin/env python3
"""
Ingesta de vídeos locales → feature_samples (grabaciones propias / gold).

Lee un manifiesto JSON: lista de {path, label, notes?}.
Etiqueta ``label_source=own_recording`` (o el valor indicado) y
``review_status=approved`` solo si ``--auto-approve`` (por defecto: pending,
porque las tomas propias suelen ser imperfectas y conviene curar).

Ejemplo de manifiesto::

    {
      "items": [
        {"path": "tests/assets/videos/SentadillaProfunda.mp4", "label": "squat"},
        {"path": "/Volumes/.../Running con jeff.mp4", "label": "running", "notes": "forma imperfecta OK"}
      ]
    }

Uso (contenedor backend, con el path montado o copiado)::

    python scripts/ingest_local_videos.py \\
      --manifest vision/data/own_recordings_manifest.json \\
      --auto-approve \\
      --max-frames 900
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def main() -> None:
    p = argparse.ArgumentParser(description="Ingesta local → feature_samples")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--auto-approve", action="store_true")
    p.add_argument("--emit-every", type=int, default=3)
    p.add_argument("--max-frames", type=int, default=900)
    p.add_argument("--label-source", default="own_recording")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo lista paths/labels sin extraer",
    )
    args = p.parse_args()

    man_path = args.manifest
    if not man_path.is_absolute():
        man_path = (_BACKEND / man_path).resolve()
    if not man_path.is_file():
        raise SystemExit(f"No existe manifiesto: {man_path}")

    data = json.loads(man_path.read_text(encoding="utf-8"))
    items = data.get("items") or []
    if not items:
        raise SystemExit("Manifiesto sin items")

    from app.config import settings
    from app.db.models import FeatureSampleORM
    from app.db.session import SessionLocal, engine_configured
    from app.paths import backend_root

    if not engine_configured():
        raise SystemExit("DATABASE_URL no configurada")

    import importlib.util as _ilu

    script = _BACKEND / "scripts" / "export_features_from_video.py"
    spec = _ilu.spec_from_file_location("export_features_from_video", script)
    assert spec and spec.loader
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    extract = mod.extract_features_from_file

    root = backend_root()
    model_path = settings.resolve_model_path(root)
    cfg = settings.exercise_classifier_config()
    review = "approved" if args.auto_approve else "pending"
    job_tag = uuid.uuid4()

    summary: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_path = str(item.get("path") or "").strip()
        label = str(item.get("label") or "").strip().lower()
        notes = str(item.get("notes") or "")
        if not raw_path or not label:
            print(f"SKIP item incompleto: {item}")
            continue
        path = Path(raw_path)
        if not path.is_absolute():
            # relativo al monorepo (padre de backend) o a backend
            cand = [
                (_BACKEND.parent / path).resolve(),
                (_BACKEND / path).resolve(),
                path.resolve(),
            ]
            path = next((c for c in cand if c.is_file()), cand[0])
        if not path.is_file():
            print(f"MISSING: {path}")
            summary.append({"path": str(path), "label": label, "status": "missing"})
            continue
        if args.dry_run:
            print(f"dry-run OK {label}: {path}")
            summary.append({"path": str(path), "label": label, "status": "dry_run"})
            continue

        print(f"Extrayendo {label} ← {path.name} ...")
        try:
            vectors, frames = extract(
                path,
                label,
                cfg,
                model_path,
                only_window_full=True,
                require_pose_ok=True,
                emit_every=max(1, args.emit_every),
                max_frames=max(0, args.max_frames),
            )
        except Exception as exc:
            print(f"ERROR {path.name}: {exc}")
            summary.append({"path": str(path), "label": label, "status": f"error:{exc}"})
            continue

        source_key = f"own:{path.name}"
        inserted = 0
        with SessionLocal() as db:
            for vec in vectors:
                db.add(
                    FeatureSampleORM(
                        label=label[:64],
                        label_source=str(args.label_source)[:32],
                        review_status=review,
                        feature_vector=vec,
                        confidence_at_collection=None,
                        pose_ok=True,
                        session_id=None,
                        source_file=source_key[:512],
                        split="unset",
                        notes=(notes or f"local_ingest={job_tag}")[:2000],
                    ),
                )
                inserted += 1
            db.commit()
        print(f"  frames={frames} vectors={len(vectors)} inserted={inserted} review={review}")
        summary.append(
            {
                "path": str(path),
                "label": label,
                "source_file": source_key,
                "frames": frames,
                "inserted": inserted,
                "status": "ok",
            },
        )

    out = man_path.with_suffix(".ingest_report.json")
    out.write_text(json.dumps({"job": str(job_tag), "items": summary}, indent=2) + "\n", encoding="utf-8")
    print("report →", out)


if __name__ == "__main__":
    main()
