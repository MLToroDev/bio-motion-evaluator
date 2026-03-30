from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


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


settings = Settings()
