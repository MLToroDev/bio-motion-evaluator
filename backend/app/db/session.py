from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.base import Base


def _to_async_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> None:
    global _engine, _session_factory
    url = settings.database_url
    if not url or not str(url).strip():
        _engine = None
        _session_factory = None
        return
    async_url = _to_async_url(str(url).strip())
    _engine = create_async_engine(async_url, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


def engine_configured() -> bool:
    return bool(settings.database_url and str(settings.database_url).strip())


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia FastAPI para sesión async."""
    global _session_factory
    if not engine_configured():
        raise HTTPException(status_code=503, detail="DATABASE_URL not configured")
    if _session_factory is None:
        init_engine()
    if _session_factory is None:
        raise HTTPException(status_code=503, detail="DATABASE_URL not configured")
    async with _session_factory() as session:
        yield session


async def create_all_tables() -> None:
    """Desarrollo: crear tablas sin Alembic (no usar en producción)."""
    if _engine is None:
        init_engine()
    if _engine is None:
        return
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
