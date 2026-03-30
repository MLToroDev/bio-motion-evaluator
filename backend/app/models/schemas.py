from typing import Any, Literal

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


class PoseStreamConfig(BaseModel):
    """
    Primer mensaje (texto JSON) del cliente en ``/ws/pose-stream``.

    - ``file``: usar ``video_filename`` (solo nombre, p. ej. ``squat_test.mp4``)
      dentro de ``tests/assets/videos/``.
    - ``camera``: índice OpenCV ``device_index``.
    - ``url``: cadena RTSP/HTTP en ``stream_url``.
    """

    source: Literal["camera", "file", "url"] = "file"
    video_filename: str | None = Field(
        default=None,
        description="Nombre de archivo bajo tests/assets/videos (ej. squat_test.mp4)",
    )
    device_index: int = 0
    stream_url: str | None = None
    target_fps: float = Field(default=15.0, ge=0.5, le=60.0)
