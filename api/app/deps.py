import hmac
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import async_session
from app.security import hash_session_token

SESSION_COOKIE = "session"
CSRF_COOKIE = "csrf"
CSRF_HEADER = "x-csrf-token"


async def get_db() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session


DB = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(request: Request, db: DB) -> models.User:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await db.execute(
        select(models.AuthSession).where(models.AuthSession.id == hash_session_token(raw))
    )
    auth_session = result.scalar_one_or_none()
    if auth_session is None or auth_session.expires_at <= models.utcnow():
        raise HTTPException(status_code=401, detail="Session expired")
    user = await db.get(models.User, auth_session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account inactive")
    return user


CurrentUser = Annotated[models.User, Depends(get_current_user)]


async def require_parent(user: CurrentUser) -> models.User:
    if user.role != "parent":
        raise HTTPException(status_code=403, detail="Parent role required")
    return user


ParentUser = Annotated[models.User, Depends(require_parent)]


async def verify_csrf(request: Request) -> None:
    """Double-submit CSRF check on mutating requests (login is exempt: no
    csrf cookie exists yet and credentials are the proof)."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get(CSRF_HEADER)
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise HTTPException(status_code=403, detail="CSRF check failed")


async def get_child_or_404(child_id: str, db: DB) -> models.Child:
    child = await db.get(models.Child, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child not found")
    return child
