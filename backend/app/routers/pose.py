from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.models.schemas import LandmarkPoint, PoseAnalysisResponse
from app.services import huggingface_service
from vision.realtime_engine import RealtimeEngineSession

router = APIRouter(tags=["pose"])

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


@router.post("/analyze/pose", response_model=PoseAnalysisResponse)
async def analyze_pose(file: UploadFile = File(...)) -> PoseAnalysisResponse:
    """Imagen → pose MediaPipe + motor (features/clasificador/rep) en una sola pasada por request."""
    model_path = settings.resolve_model_path(_BACKEND_ROOT)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    session = RealtimeEngineSession(
        _BACKEND_ROOT,
        model_path,
        settings.exercise_classifier_config(),
    )
    try:
        payload = session.process_jpeg(data, frame_index=0)
    finally:
        session.reset()

    landmarks_raw = payload.get("landmarks") or []
    landmarks = [LandmarkPoint(**p) for p in landmarks_raw]
    world_raw = payload.get("world_landmarks") or []
    world = [LandmarkPoint(**p) for p in world_raw]

    hf_raw = await huggingface_service.run_optional_inference(
        {"landmarks": [lm.model_dump() for lm in landmarks], "note": payload.get("note")}
    )

    return PoseAnalysisResponse(
        ok=bool(payload.get("pose_ok")),
        landmarks=landmarks,
        world_landmarks=world,
        note=payload.get("note"),
        raw=hf_raw,
        schema_version=int(payload.get("schema_version", 1)),
        exercise_label=str(payload.get("exercise_label", "unknown")),
        exercise_confidence=float(payload.get("exercise_confidence", 0.0)),
        rep_phase=str(payload.get("rep_phase", "idle")),
        rep_count=int(payload.get("rep_count", 0)),
        quality_flags=list(payload.get("quality_flags") or []),
        pipeline_ms=payload.get("pipeline_ms"),
    )

