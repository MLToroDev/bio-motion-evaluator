# Payload unificado WS v1 (complemento ARCH-5 realtime_engine).
"""Construcción del dict JSON por fotograma (contrato WS unificado v1)."""

from __future__ import annotations

import time
from typing import Any

from app.config import settings
from vision.landmark_filter import landmarks_for_api_response
from vision.types import PoseFrame, RepState

SCHEMA_VERSION = 1


def build_frame_payload_v1(
    frame_index: int,
    pose: PoseFrame,
    exercise_label: str,
    exercise_confidence: float,
    rep: RepState,
    pipeline_ms: dict[str, float],
    equipment_label: str | None = None,
    detected_objects: list[dict[str, Any]] | None = None,
    exercise_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    min_vis = float(settings.pose_landmark_min_visibility_response)
    lm_out, wl_out = landmarks_for_api_response(
        pose.landmarks,
        pose.world_landmarks,
        min_vis,
    )
    out: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "frame_index": frame_index,
        "server_ts_ms": int(time.time() * 1000),
        "pose_ok": pose.ok,
        "note": pose.note,
        "landmarks": lm_out,
        "knees": pose.knees,
        "exercise_label": exercise_label,
        "exercise_confidence": float(exercise_confidence),
        "rep_phase": rep.rep_phase,
        "rep_count": rep.rep_count,
        "quality_flags": rep.quality_flags,
        "pipeline_ms": pipeline_ms,
    }
    if equipment_label:
        # Manual o inferido por detector de objetos (extensión compatible v1).
        out["equipment_label"] = equipment_label
    if detected_objects:
        out["detected_objects"] = detected_objects
    if exercise_validation:
        # Extensión compatible v1: veredicto confirm|reject|changed|uncertain.
        out["exercise_validation"] = exercise_validation
    if pose.world_landmarks:
        out["world_landmarks"] = wl_out if wl_out is not None else []
    return out

