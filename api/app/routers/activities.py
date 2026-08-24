from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.deps import DB, CurrentUser, ParentUser, get_child_or_404, verify_csrf

router = APIRouter(tags=["activities"], dependencies=[Depends(verify_csrf)])


async def get_activity_for_child_or_422(
    db: AsyncSession, activity_id: str, child_id: str
) -> models.Activity:
    """Shared by routers that accept an activity link on another resource."""
    activity = await db.get(models.Activity, activity_id)
    if activity is None or activity.child_id != child_id:
        raise HTTPException(status_code=422, detail="Activity not found for this child")
    return activity


@router.get("/children/{child_id}/activities", response_model=list[schemas.ActivityOut])
async def list_activities(
    child_id: str, db: DB, _user: CurrentUser, include_archived: bool = False
) -> list[models.Activity]:
    await get_child_or_404(child_id, db)
    query = (
        select(models.Activity)
        .where(models.Activity.child_id == child_id)
        .order_by(models.Activity.title)
    )
    if not include_archived:
        query = query.where(models.Activity.is_archived.is_(False))
    result = await db.execute(query)
    return list(result.scalars())


@router.post("/children/{child_id}/activities", response_model=schemas.ActivityOut, status_code=201)
async def create_activity(
    child_id: str, body: schemas.ActivityCreate, db: DB, _user: ParentUser
) -> models.Activity:
    await get_child_or_404(child_id, db)
    activity = models.Activity(
        child_id=child_id,
        title=body.title,
        icon=body.icon,
        description=body.description,
        materials=body.materials,
        skill_tags=body.skill_tags,
        context_tags=body.context_tags,
        duration_minutes=body.duration_minutes,
    )
    db.add(activity)
    await db.commit()
    return activity


@router.patch("/activities/{activity_id}", response_model=schemas.ActivityOut)
async def update_activity(
    activity_id: str, body: schemas.ActivityUpdate, db: DB, _user: ParentUser
) -> models.Activity:
    activity = await db.get(models.Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    provided = body.model_fields_set
    if body.title is not None:
        activity.title = body.title
    if "icon" in provided:
        activity.icon = body.icon
    if "description" in provided:
        activity.description = body.description
    if "materials" in provided:
        activity.materials = body.materials
    if body.skill_tags is not None:
        activity.skill_tags = body.skill_tags
    if body.context_tags is not None:
        activity.context_tags = body.context_tags
    if "duration_minutes" in provided:
        activity.duration_minutes = body.duration_minutes
    if body.is_archived is not None:
        activity.is_archived = body.is_archived
    await db.commit()
    return activity
