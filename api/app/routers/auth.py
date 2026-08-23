from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select

from app import models, schemas
from app.config import settings
from app.deps import CSRF_COOKIE, DB, SESSION_COOKIE, CurrentUser, verify_csrf
from app.security import (
    hash_session_token,
    new_csrf_token,
    new_session_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, raw_token: str, csrf_token: str) -> None:
    max_age = settings.session_ttl_days * 24 * 3600
    response.set_cookie(
        SESSION_COOKIE,
        raw_token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    # Readable by JS on purpose: the double-submit half of the CSRF check.
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/login", response_model=schemas.UserOut)
async def login(body: schemas.LoginIn, db: DB, response: Response) -> models.User:
    result = await db.execute(select(models.User).where(models.User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account inactive")

    raw_token, token_hash = new_session_token()
    db.add(
        models.AuthSession(
            id=token_hash,
            user_id=user.id,
            expires_at=models.utcnow() + timedelta(days=settings.session_ttl_days),
        )
    )
    await db.commit()
    _set_auth_cookies(response, raw_token, new_csrf_token())
    return user


@router.post("/logout", status_code=204, dependencies=[Depends(verify_csrf)])
async def logout(request: Request, db: DB, response: Response, _user: CurrentUser) -> None:
    raw = request.cookies.get(SESSION_COOKIE)
    if raw:
        await db.execute(
            delete(models.AuthSession).where(models.AuthSession.id == hash_session_token(raw))
        )
        await db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


@router.get("/me", response_model=schemas.UserOut)
async def me(user: CurrentUser) -> models.User:
    return user
