from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app import models, schemas
from app.deps import DB, ParentUser, verify_csrf
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(verify_csrf)])


@router.get("", response_model=list[schemas.UserOut])
async def list_users(db: DB, _user: ParentUser) -> list[models.User]:
    result = await db.execute(select(models.User).order_by(models.User.created_at))
    return list(result.scalars())


@router.post("", response_model=schemas.UserOut, status_code=201)
async def create_user(body: schemas.UserCreate, db: DB, _user: ParentUser) -> models.User:
    email = body.email.lower()
    existing = await db.execute(select(models.User).where(models.User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already in use")
    user = models.User(
        email=email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        role=body.role,
    )
    db.add(user)
    await db.commit()
    return user


@router.patch("/{user_id}", response_model=schemas.UserOut)
async def update_user(
    user_id: str, body: schemas.UserUpdate, db: DB, actor: ParentUser
) -> models.User:
    user = await db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if body.is_active is False and user.id == actor.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    await db.commit()
    return user
