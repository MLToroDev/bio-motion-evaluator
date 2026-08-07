from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user_id
from app.db.models import SessionMetricORM, SessionORM, UserORM
from app.db.session import get_session

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSessionBody(BaseModel):
    exercise_label: str = Field(default="unknown", max_length=128)
    device_info: dict[str, Any] | None = None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    exercise_label: str
    started_at: datetime | None = None
    ended_at: datetime | None = None


@router.post("", response_model=SessionOut)
async def create_session(
    body: CreateSessionBody,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_sub: Annotated[str, Depends(require_user_id)],
) -> SessionORM:
    try:
        uid = uuid.UUID(user_sub)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id in token") from exc
    q = await session.execute(select(UserORM).where(UserORM.id == uid))
    if q.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="User not found")
    row = SessionORM(user_id=uid, exercise_label=body.exercise_label, device_info=body.device_info)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    session: Annotated[AsyncSession, Depends(get_session)],
    user_sub: Annotated[str, Depends(require_user_id)],
) -> list[SessionORM]:
    try:
        uid = uuid.UUID(user_sub)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id in token") from exc
    q = await session.execute(
        select(SessionORM).where(SessionORM.user_id == uid).order_by(SessionORM.started_at.desc()).limit(50)
    )
    return list(q.scalars().all())


class SessionMetricBody(BaseModel):
    frame_index: int | None = None
    rep_count: int | None = None
    avg_confidence: float | None = None
    quality_score: float | None = None
    flags_json: dict[str, Any] | None = None


@router.post("/{session_id}/metrics", status_code=201)
async def add_session_metric(
    session_id: uuid.UUID,
    body: SessionMetricBody,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_sub: Annotated[str, Depends(require_user_id)],
) -> dict[str, str]:
    try:
        uid = uuid.UUID(user_sub)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id in token") from exc
    q = await session.execute(select(SessionORM).where(SessionORM.id == session_id, SessionORM.user_id == uid))
    row = q.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    m = SessionMetricORM(
        session_id=session_id,
        frame_index=body.frame_index,
        rep_count=body.rep_count,
        avg_confidence=body.avg_confidence,
        quality_score=body.quality_score,
        flags_json=body.flags_json,
    )
    session.add(m)
    await session.commit()
    return {"status": "ok"}


@router.post("/{session_id}/end", response_model=SessionOut)
async def end_session(
    session_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_sub: Annotated[str, Depends(require_user_id)],
) -> SessionORM:
    try:
        uid = uuid.UUID(user_sub)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id in token") from exc
    q = await session.execute(select(SessionORM).where(SessionORM.id == session_id, SessionORM.user_id == uid))
    row = q.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    row.ended_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(row)
    return row

