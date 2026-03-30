from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.models.schemas import LandmarkPoint, PoseAnalysisResponse
from app.services import huggingface_service
from app.services.mediapipe_service import analyze_image_bytes

router = APIRouter(tags=["pose"])

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


@router.post("/analyze/pose", response_model=PoseAnalysisResponse)
async def analyze_pose(file: UploadFile = File(...)) -> PoseAnalysisResponse:
    """Recibe una imagen y devuelve landmarks de pose (MediaPipe Pose Landmarker)."""
    model_path = settings.resolve_model_path(_BACKEND_ROOT)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    result = analyze_image_bytes(data, model_path)

    landmarks = [LandmarkPoint(**p) for p in result.landmarks]
    world = [LandmarkPoint(**p) for p in result.world_landmarks]

    hf_raw = await huggingface_service.run_optional_inference(
        {"landmarks": [lm.model_dump() for lm in landmarks], "note": result.note}
    )

    return PoseAnalysisResponse(
        ok=result.ok,
        landmarks=landmarks,
        world_landmarks=world,
        note=result.note,
        raw=hf_raw,
    )
