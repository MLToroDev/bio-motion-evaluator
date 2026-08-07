from __future__ import annotations

from collections.abc import AsyncGenerator, Generator

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.base import Base


def _to_async_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def _to_sync_url(url: str) -> str:
    """URL para motor síncrono (psycopg2); quita ``+asyncpg`` si viene de copiar la async."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None

_sync_engine = None
_sync_session_factory: sessionmaker[Session] | None = None


def _init_sync_engine() -> None:
    """Motor ORM síncrono: Celery y routers que usan ``Session`` clásica."""
    global _sync_engine, _sync_session_factory
    if _sync_session_factory is not None:
        return
    url = settings.database_url
    if not url or not str(url).strip():
        return
    sync_url = _to_sync_url(str(url).strip())
    _sync_engine = create_engine(sync_url, echo=False, pool_pre_ping=True)
    _sync_session_factory = sessionmaker(
        bind=_sync_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )


class _SyncSessionLocal:
    """Compatible con ``with SessionLocal() as db:`` en tareas Celery."""

    def __call__(self) -> Session:
        _init_sync_engine()
        if _sync_session_factory is None:
            raise RuntimeError("DATABASE_URL not configured")
        return _sync_session_factory()


SessionLocal = _SyncSessionLocal()


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
    _init_sync_engine()


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


def get_db() -> Generator[Session, None, None]:
    """Dependencia FastAPI para endpoints síncronos (p. ej. descargas + Celery)."""
    if not engine_configured():
        raise HTTPException(status_code=503, detail="DATABASE_URL not configured")
    _init_sync_engine()
    if _sync_session_factory is None:
        raise HTTPException(status_code=503, detail="DATABASE_URL not configured")
    db = _sync_session_factory()
    try:
        yield db
    finally:
        db.close()


async def create_all_tables() -> None:
    """Desarrollo: crear tablas sin Alembic (no usar en producción)."""
    if _engine is None:
        init_engine()
    if _engine is None:
        return
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

