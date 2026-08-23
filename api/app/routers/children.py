from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app import models, schemas
from app.deps import DB, CurrentUser, ParentUser, verify_csrf

router = APIRouter(prefix="/children", tags=["children"], dependencies=[Depends(verify_csrf)])


@router.get("", response_model=list[schemas.ChildOut])
async def list_children(db: DB, _user: CurrentUser) -> list[models.Child]:
    result = await db.execute(select(models.Child).order_by(models.Child.created_at))
    return list(result.scalars())


@router.post("", response_model=schemas.ChildOut, status_code=201)
async def create_child(body: schemas.ChildCreate, db: DB, _user: ParentUser) -> models.Child:
    child = models.Child(
        display_name=body.display_name,
        birth_date=body.birth_date,
        timezone=body.timezone,
    )
    db.add(child)
    await db.commit()
    return child


@router.patch("/{child_id}", response_model=schemas.ChildOut)
async def update_child(
    child_id: str, body: schemas.ChildUpdate, db: DB, _user: ParentUser
) -> models.Child:
    child = await db.get(models.Child, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child not found")
    if body.display_name is not None:
        child.display_name = body.display_name
    if body.birth_date is not None:
        child.birth_date = body.birth_date
    if body.timezone is not None:
        child.timezone = body.timezone
    await db.commit()
    return child
