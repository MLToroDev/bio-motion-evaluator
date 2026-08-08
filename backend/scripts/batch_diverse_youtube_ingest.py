#!/usr/bin/env python3
"""
Segunda tanda de ingesta YouTube orientada a diversidad (ángulos, principiantes, gym/casa).

Usa las queries del catálogo (incluye las nuevas de dominio real) y evita
re-entrenar automáticamente: solo ingesta. Después evaluar con GroupKFold.

    python scripts/batch_diverse_youtube_ingest.py \\
      --labels squat,lunge,curl,idle,running,pushup,plank,jumping_jack,overhead_press,deadlift,mountain_climber \\
      --queries-per-label 3 --max-videos 3
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--labels", required=True)
    p.add_argument("--max-videos", type=int, default=3)
    p.add_argument("--queries-per-label", type=int, default=3)
    p.add_argument("--skip-first-queries", type=int, default=2,
                   help="Saltar las N primeras queries (típicamente 'perfect form') para priorizar diversidad")
    p.add_argument(
        "--query-offset",
        type=int,
        default=0,
        help="Desplazamiento extra sobre skip-first (para no repetir queries de rondas previas)",
    )
    p.add_argument("--emit-every", type=int, default=3)
    p.add_argument("--max-frames-per-video", type=int, default=600)
    p.add_argument("--poll-s", type=float, default=10.0)
    p.add_argument("--timeout-s", type=float, default=7200.0)
    p.add_argument("--auto-approve", action="store_true", default=True)
    args = p.parse_args()

    labels = [x.strip().lower() for x in args.labels.split(",") if x.strip()]
    catalog = json.loads((_BACKEND / "vision" / "data" / "exercise_catalog.json").read_text(encoding="utf-8"))
    by_id = {str(e["id"]): e for e in catalog.get("exercises") or [] if isinstance(e, dict)}

    from app.db.models import IngestJobORM
    from app.db.session import SessionLocal
    from app.workers.celery_app import celery_app

    job_ids: list[uuid.UUID] = []
    with SessionLocal() as db:
        for lab in labels:
            queries = list(by_id.get(lab, {}).get("youtube_search_queries") or [])
            if not queries:
                queries = [f"{lab} exercise home gym phone camera full body"]
            # Priorizar queries de diversidad (después de las de 'perfect form')
            start = min(
                max(0, args.skip_first_queries) + max(0, args.query_offset),
                max(0, len(queries) - 1),
            )
            selected = queries[start : start + max(1, args.queries_per_label)]
            if not selected:
                selected = queries[: max(1, args.queries_per_label)]
            for q in selected:
                job = IngestJobORM(
                    status="pending",
                    exercise_label=lab,
                    source_type="youtube_search_diverse",
                    query=q,
                    max_videos=max(1, args.max_videos),
                    auto_approve=bool(args.auto_approve),
                    params_json={
                        "only_window_full": True,
                        "require_pose_ok": True,
                        "emit_every": max(1, args.emit_every),
                        "max_frames_per_video": max(0, args.max_frames_per_video),
                        "diversity_round": "2026-08-07",
                    },
                )
                db.add(job)
                db.flush()
                job_ids.append(job.id)
                print(f"enqueue {lab!r} :: {q!r} id={job.id}")
        db.commit()

    for jid in job_ids:
        celery_app.send_task("ingest_exercise_videos", args=[str(jid)])

    deadline = time.time() + float(args.timeout_s)
    pending = set(job_ids)
    while pending and time.time() < deadline:
        time.sleep(float(args.poll_s))
        with SessionLocal() as db:
            done = []
            for jid in list(pending):
                job = db.query(IngestJobORM).filter(IngestJobORM.id == jid).first()
                if not job:
                    done.append(jid)
                    continue
                if job.status in ("completed", "failed"):
                    m = job.metrics_json or {}
                    print(
                        f"{job.status}: {job.exercise_label} inserted={m.get('samples_inserted')} "
                        f"videos={m.get('videos_processed')} fail={m.get('videos_failed')} q={job.query[:50]}",
                    )
                    done.append(jid)
            for jid in done:
                pending.discard(jid)
    if pending:
        raise SystemExit(f"Timeout: {len(pending)} jobs pendientes")
    print("OK: tanda diversa completada")


if __name__ == "__main__":
    main()
