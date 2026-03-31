# Payload unificado WS v1 (complemento ARCH-5 realtime_engine).
"""Construcción del dict JSON por fotograma (contrato WS unificado v1)."""

from __future__ import annotations

import time
from typing import Any

from vision.types import PoseFrame, RepState

SCHEMA_VERSION = 1


def build_frame_payload_v1(
    frame_index: int,
    pose: PoseFrame,
    exercise_label: str,
    exercise_confidence: float,
    rep: RepState,
    pipeline_ms: dict[str, float],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "frame_index": frame_index,
        "server_ts_ms": int(time.time() * 1000),
        "pose_ok": pose.ok,
        "note": pose.note,
        "landmarks": pose.landmarks,
        "knees": pose.knees,
        "exercise_label": exercise_label,
        "exercise_confidence": float(exercise_confidence),
        "rep_phase": rep.rep_phase,
        "rep_count": rep.rep_count,
        "quality_flags": rep.quality_flags,
        "pipeline_ms": pipeline_ms,
    }
