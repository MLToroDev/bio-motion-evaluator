import json
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.models.schemas import ExerciseClassifierConfig


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "bio-motion-evaluator-api"
    app_version: str = "0.1.0"
    cors_origins: str = "*"

    mediapipe_pose_model_path: str = "models/pose_landmarker_full.task"

    hf_api_token: str | None = None
    hf_inference_url: str | None = None

    # Clasificador / motor (env opcional; ver ExerciseClassifierConfig)
    classifier_min_confidence: float = 0.72
    classifier_window_size_frames: int = 45
    classifier_hysteresis_frames: int = 10
    classifier_unknown_label: str = "unknown"
    classifier_confidence_ema_alpha: float = 0.25
    classifier_confidence_filter: str = "ema"
    classifier_kalman_process_noise: float = 1e-4
    classifier_kalman_measurement_noise: float = 0.05
    feature_default_dt_s: float = 1.0 / 15.0
    feature_calibration_min_frames: int = 10

    # Persistencia (Fase 1: schema listo; dejar vacío en dev sin Docker)
    database_url: str | None = None

    # Auth stub (Fase 1): JWT para trazabilidad; clave debe cambiarse en producción
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # Usuario fantasma cuando no hay login (user_id en sesiones)
    stub_user_email: str = "anonymous@local.test"

    # Feature flags JSON, p. ej. {"enable_onnx_classifier": false}
    feature_flags_json: str = "{}"

    # ARCH-T14 — umbral de latencia / backpressure (activar drop en routers cuando se integre cola)
    server_pipeline_warn_ms: float = 300.0
    enable_adaptive_frame_drop: bool = False

    # Telemetría: log INFO por frame con pipeline_ms (extract/feature/classify/track/total) en /ws/video
    log_pose_pipeline_timing: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    def resolve_model_path(self, backend_root: Path) -> Path:
        p = Path(self.mediapipe_pose_model_path)
        if not p.is_absolute():
            p = backend_root / p
        return p

    @staticmethod
    def repo_root() -> Path:
        """Raíz del monorepo (directorio que contiene `app/`, `backend/`, `tests/`)."""
        return Path(__file__).resolve().parents[2]

    @classmethod
    def gold_standard_videos_dir(cls) -> Path:
        """Directorio de vídeos de referencia para regresión y validación (Capítulo 7)."""
        return cls.repo_root() / "tests" / "assets" / "videos"

    def exercise_classifier_config(self) -> ExerciseClassifierConfig:
        cf = (self.classifier_confidence_filter or "ema").strip().lower()
        if cf not in ("ema", "kalman"):
            cf = "ema"
        return ExerciseClassifierConfig(
            min_confidence=self.classifier_min_confidence,
            window_size_frames=self.classifier_window_size_frames,
            hysteresis_frames=self.classifier_hysteresis_frames,
            unknown_label=self.classifier_unknown_label,
            confidence_ema_alpha=self.classifier_confidence_ema_alpha,
            confidence_filter=cf,
            kalman_process_noise=self.classifier_kalman_process_noise,
            kalman_measurement_noise=self.classifier_kalman_measurement_noise,
            feature_default_dt_s=float(self.feature_default_dt_s),
            feature_calibration_min_frames=int(self.feature_calibration_min_frames),
        )

    def feature_flags(self) -> dict[str, Any]:
        try:
            data = json.loads(self.feature_flags_json or "{}")
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}


settings = Settings()

