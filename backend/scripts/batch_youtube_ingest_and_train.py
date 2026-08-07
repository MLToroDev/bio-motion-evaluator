#!/usr/bin/env python3
"""
Ingesta masiva YouTube → feature_samples (approved) + entrenamiento multi-clase.

Usa las ``youtube_search_queries`` del catálogo
(``vision/data/exercise_catalog.json``) y la tarea Celery ``ingest_exercise_videos``.

Ejemplo (desde ``backend/``, con stack Docker o Redis+DB locales)::

    python scripts/batch_youtube_ingest_and_train.py \\
        --labels squat,lunge,curl,idle,running \\
        --max-videos 4 \\
        --set-active

Notas:
- ``exercises-dataset`` (hasaneyldrm) NO aporta vídeo de pose: solo metadatos/GIF.
  El aprendizaje real sigue siendo MediaPipe → vector 32D → RandomForest ONNX.
- YouTube varía; revisa métricas del job y curación en ``/dev/dataset`` si hace falta.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def _load_catalog() -> dict[str, Any]:
    path = _BACKEND_ROOT / "vision" / "data" / "exercise_catalog.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    p = argparse.ArgumentParser(description="Ingesta YouTube por catálogo + train ONNX")
    p.add_argument(
        "--labels",
        default="squat,lunge,curl,idle,running",
        help="Etiquetas separadas por coma (deben existir en el catálogo)",
    )
    p.add_argument("--max-videos", type=int, default=4, help="Vídeos por query de búsqueda")
    p.add_argument("--queries-per-label", type=int, default=2, help="Cuántas queries del catálogo usar")
    p.add_argument("--emit-every", type=int, default=3)
    p.add_argument("--max-frames-per-video", type=int, default=900)
    p.add_argument("--skip-ingest", action="store_true", help="Solo entrenar con muestras ya approved")
    p.add_argument("--skip-train", action="store_true")
    p.add_argument("--set-active", action="store_true", default=True)
    p.add_argument("--no-set-active", action="store_true")
    p.add_argument("--poll-s", type=float, default=8.0)
    p.add_argument("--timeout-s", type=float, default=3600.0)
    args = p.parse_args()

    set_active = bool(args.set_active) and not bool(args.no_set_active)
    labels = [x.strip().lower() for x in args.labels.split(",") if x.strip()]
    catalog = _load_catalog()
    by_id = {str(e["id"]): e for e in catalog.get("exercises") or [] if isinstance(e, dict)}
    missing = [lab for lab in labels if lab not in by_id]
    if missing:
        raise SystemExit(f"Etiquetas no están en catálogo: {missing}")

    from app.db.models import FeatureSampleORM, IngestJobORM, TrainingJobORM
    from app.db.session import SessionLocal
    from app.workers.celery_app import celery_app

    if not args.skip_ingest:
        job_ids: list[uuid.UUID] = []
        with SessionLocal() as db:
            for lab in labels:
                queries = list(by_id[lab].get("youtube_search_queries") or [])
                if not queries:
                    queries = [f"{lab} exercise form full body tutorial"]
                for q in queries[: max(1, args.queries_per_label)]:
                    job = IngestJobORM(
                        status="pending",
                        exercise_label=lab,
                        query=q,
                        max_videos=max(1, args.max_videos),
                        auto_approve=True,
                        params_json={
                            "only_window_full": True,
                            "require_pose_ok": True,
                            "emit_every": max(1, args.emit_every),
                            "max_frames_per_video": max(0, args.max_frames_per_video),
                        },
                    )
                    db.add(job)
                    db.flush()
                    job_ids.append(job.id)
                    print(f"enqueue ingest label={lab!r} query={q!r} id={job.id}")
            db.commit()

        for jid in job_ids:
            celery_app.send_task("ingest_exercise_videos", args=[str(jid)])

        deadline = time.time() + float(args.timeout_s)
        pending = set(job_ids)
        while pending and time.time() < deadline:
            time.sleep(float(args.poll_s))
            with SessionLocal() as db:
                done: list[uuid.UUID] = []
                for jid in list(pending):
                    job = db.query(IngestJobORM).filter(IngestJobORM.id == jid).first()
                    if not job:
                        done.append(jid)
                        continue
                    if job.status in ("completed", "failed"):
                        m = job.metrics_json or {}
                        print(
                            f"ingest {job.status}: {job.exercise_label} "
                            f"inserted={m.get('samples_inserted')} "
                            f"videos={m.get('videos_processed')} err={job.error_message}",
                        )
                        done.append(jid)
                for jid in done:
                    pending.discard(jid)
        if pending:
            raise SystemExit(f"Timeout: {len(pending)} jobs de ingesta aún pendientes")

    with SessionLocal() as db:
        rows = (
            db.query(FeatureSampleORM.label)
            .filter(
                FeatureSampleORM.review_status == "approved",
                FeatureSampleORM.label.in_(labels),
            )
            .all()
        )
        counts: dict[str, int] = {lab: 0 for lab in labels}
        for (lab,) in rows:
            counts[str(lab).lower()] = counts.get(str(lab).lower(), 0) + 1
        print("approved counts:", counts)
        trainable = [lab for lab in labels if counts.get(lab, 0) >= 2]
        if len(trainable) < 2:
            raise SystemExit(
                "Se necesitan al menos 2 clases con >=2 muestras approved. "
                f"Actual: {counts}",
            )

    if args.skip_train:
        print("skip-train: fin")
        return

    with SessionLocal() as db:
        job = TrainingJobORM(
            status="pending",
            classes_json=trainable,
            params_json={
                "validation_fraction": 0.2,
                "set_active": set_active,
                "seed": 42,
                "n_estimators": 250,
            },
        )
        db.add(job)
        db.commit()
        train_id = job.id
        print(f"enqueue train id={train_id} classes={trainable} set_active={set_active}")

    celery_app.send_task("train_exercise_classifier", args=[str(train_id)])
    deadline = time.time() + float(args.timeout_s)
    while time.time() < deadline:
        time.sleep(float(args.poll_s))
        with SessionLocal() as db:
            job = db.query(TrainingJobORM).filter(TrainingJobORM.id == train_id).first()
            if not job:
                raise SystemExit("Training job desapareció")
            if job.status in ("completed", "failed"):
                print(
                    f"train {job.status}: model={job.model_key} samples={job.sample_count} "
                    f"metrics={job.metrics_json} err={job.error_message}",
                )
                if job.status != "completed":
                    raise SystemExit(1)
                return
    raise SystemExit("Timeout esperando entrenamiento")


if __name__ == "__main__":
    main()
