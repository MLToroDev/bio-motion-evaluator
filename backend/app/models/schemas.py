from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ExerciseClassifierConfig(BaseModel):
    """Parámetros centralizados del clasificador (umbral, ventana, histéresis, EMA/Kalman)."""

    min_confidence: float = Field(default=0.72, ge=0.0, le=1.0)
    window_size_frames: int = Field(default=45, ge=2, le=300)
    hysteresis_frames: int = Field(default=10, ge=0, le=120)
    unknown_label: str = Field(default="unknown", min_length=1)
    confidence_ema_alpha: float = Field(default=0.25, ge=0.0, le=1.0)
    confidence_filter: Literal["ema", "kalman"] = Field(default="ema")

    @field_validator("confidence_filter", mode="before")
    @classmethod
    def confidence_filter_coerce(cls, v: object) -> str:
        if v is None:
            return "ema"
        s = str(v).strip().lower()
        return s if s in ("ema", "kalman") else "ema"
    kalman_process_noise: float = Field(default=1e-4, ge=1e-9, le=1.0)
    kalman_measurement_noise: float = Field(default=0.05, ge=1e-9, le=1.0)
    feature_default_dt_s: float = Field(default=0.06666666666666667, ge=0.001, le=1.0)
    feature_calibration_min_frames: int = Field(default=10, ge=3, le=120)


class PipelineTimingMs(BaseModel):
    """Tiempos por etapa en ms (payload WS ``pipeline_ms``)."""

    extract: float = 0.0
    feature: float = 0.0
    classify: float = 0.0
    track: float = 0.0
    total: float = 0.0


class UnifiedWsFrameV1(BaseModel):
    """
    Contrato unificado servidor → cliente (v1).
    En runtime el WebSocket puede enviar un ``dict``; este modelo documenta/valida tests.
    """

    schema_version: int = Field(default=1, ge=1)
    frame_index: int = Field(default=-1)
    server_ts_ms: int = 0
    pose_ok: bool = False
    note: str | None = None
    landmarks: list[dict[str, Any]] | None = None
    knees: dict[str, Any] | None = None
    exercise_label: str = "unknown"
    exercise_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rep_phase: str = "idle"
    rep_count: int = 0
    quality_flags: list[str] = Field(default_factory=list)
    pipeline_ms: dict[str, float] | None = None
    preview_jpeg_base64: str | None = None
    consumer_timing_ms: dict[str, float] | None = None
    total_frames: int | None = None
    error: str | None = None
    stream_done: bool | None = None

    @field_validator("quality_flags", mode="before")
    @classmethod
    def quality_flags_coerce_none(cls, v: object) -> list[str]:
        if v is None:
            return []
        return [str(x) for x in v] if isinstance(v, list) else []


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
    schema_version: int = Field(default=1, ge=1)
    exercise_label: str = "unknown"
    exercise_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rep_phase: str = "idle"
    rep_count: int = 0
    quality_flags: list[str] = Field(default_factory=list)
    pipeline_ms: dict[str, float] | None = None

    @field_validator("quality_flags", mode="before")
    @classmethod
    def quality_flags_coerce_pose(cls, v: object) -> list[str]:
        if v is None:
            return []
        return [str(x) for x in v] if isinstance(v, list) else []


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
    include_preview: bool = Field(
        default=True,
        description="Si True, cada mensaje incluye preview_jpeg_base64 (vista + marcas en cliente).",
    )
    preview_fps: Literal[8, 10, 12] = Field(
        default=10,
        description="FPS objetivo para la vista previa JPEG (8/10/12).",
    )
    preview_jpeg_quality: int = Field(
        default=84,
        ge=70,
        le=90,
        description="Calidad JPEG de la vista previa (70-90).",
    )
    capture_only: bool = Field(
        default=False,
        description="Si True, extrae pose (landmarks/knees) sin clasificador ni rep tracker.",
    )
    diagnostics: bool = Field(
        default=False,
        description="Si True, cada mensaje incluye consumer_timing_ms (desglose de latencia en el consumer).",
    )

    @field_validator("include_preview", mode="before")
    @classmethod
    def include_preview_coerce_none(cls, v: object) -> bool:
        """Flutter/JSON a veces envía null; por defecto se comporta como True."""
        if v is None:
            return True
        return bool(v)

    @field_validator("capture_only", mode="before")
    @classmethod
    def capture_only_coerce_none(cls, v: object) -> bool:
        if v is None:
            return False
        return bool(v)

    @field_validator("diagnostics", mode="before")
    @classmethod
    def diagnostics_coerce_none(cls, v: object) -> bool:
        if v is None:
            return False
        return bool(v)

