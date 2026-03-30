from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = Field(..., examples=["0.1.0"])


class LandmarkPoint(BaseModel):
    index: int
    x: float
    y: float
    z: float
    visibility: float | None = None


class PoseAnalysisResponse(BaseModel):
    ok: bool
    landmarks: list[LandmarkPoint] = []
    world_landmarks: list[LandmarkPoint] = []
    note: str | None = None
    raw: dict[str, Any] | None = None
