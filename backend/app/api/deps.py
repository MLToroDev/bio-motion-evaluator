from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token_safe

_bearer = HTTPBearer(auto_error=False)


async def optional_user_id(
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str | None:
    if cred is None or not cred.credentials:
        return None
    payload = decode_token_safe(cred.credentials)
    if payload is None:
        return None
    sub = payload.get("sub")
    return str(sub) if sub is not None else None


async def require_user_id(
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    if cred is None or not cred.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token_safe(cred.credentials)
    if payload is None or payload.get("sub") is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return str(payload["sub"])

