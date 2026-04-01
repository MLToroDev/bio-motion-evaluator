# ARCH-T13 — Autenticación JWT básica (ampliar OAuth2 después).
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_access_token
from app.db.models import UserORM
from app.db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StubLogin(BaseModel):
    """Login de desarrollo: crea o reutiliza usuario por email."""

    email: str = Field(default_factory=lambda: settings.stub_user_email)


@router.post("/token", response_model=TokenResponse)
async def login_stub(
    body: StubLogin,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    q = await session.execute(select(UserORM).where(UserORM.email == body.email))
    user = q.scalar_one_or_none()
    if user is None:
        user = UserORM(id=uuid.uuid4(), email=body.email)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    token = create_access_token(str(user.id), {"email": user.email})
    return TokenResponse(access_token=token)

