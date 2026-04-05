from __future__ import annotations

from collections.abc import Generator

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import SessionLocal, engine_configured


def verify_dev_api_key(x_dev_api_key: str | None = Header(None, alias="X-Dev-API-Key")) -> None:
    expected = settings.dev_api_key
    if expected and str(expected).strip():
        if (x_dev_api_key or "").strip() != str(expected).strip():
            raise HTTPException(status_code=401, detail="X-Dev-API-Key inválida o ausente")


def require_database() -> None:
    if not engine_configured():
        raise HTTPException(status_code=503, detail="DATABASE_URL not configured")


def get_dev_db() -> Generator[Session, None, None]:
    require_database()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
