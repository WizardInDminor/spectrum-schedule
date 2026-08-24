from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.deps import DB, CurrentUser, ParentUser, get_child_or_404, verify_csrf
from app.projections.schedule_status import STATUS_EVENT_TYPES, schedule_item_statuses
from app.routers.activities import get_activity_for_child_or_422

router = APIRouter(tags=["schedules"], dependencies=[Depends(verify_csrf)])


async def _weekday_default_template_id(
    db: AsyncSession, child_id: str, schedule_date: date
) -> str | None:
    result = await db.execute(
        select(models.WeekdayDefault.template_id).where(
            models.WeekdayDefault.child_id == child_id,
            models.WeekdayDefault.weekday == schedule_date.weekday(),
        )
    )
    return result.scalar_one_or_none()


async def _load_schedule(
    db: AsyncSession, child_id: str, schedule_date: date
) -> models.DailySchedule | None:
    result = await db.execute(
        select(models.DailySchedule)
        .where(
            models.DailySchedule.child_id == child_id,
            models.DailySchedule.schedule_date == schedule_date,
        )
        .options(selectinload(models.DailySchedule.items))
        # reload in-session objects so items come back in fresh position order
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def _schedule_with_status(
    db: AsyncSession, schedule: models.DailySchedule
) -> schemas.ScheduleOut:
    result = await db.execute(
        select(models.Event).where(
            models.Event.child_id == schedule.child_id,
            models.Event.event_type.in_(STATUS_EVENT_TYPES),
        )
    )
    statuses = schedule_item_statuses([i.id for i in schedule.items], list(result.scalars()))
    items = []
    for item in schedule.items:
        out = schemas.ScheduleItemWithStatus.model_validate(item)
        status = statuses.get(item.id)
        if status is not None:
            out.item_status = schemas.ItemStatusOut(
                status=status.status,
                event_id=status.event_id,
                occurred_at=status.occurred_at,
                reason=status.reason,
            )
        items.append(out)
    return schemas.ScheduleOut(
        id=schedule.id,
        child_id=schedule.child_id,
        schedule_date=schedule.schedule_date,
        template_id=schedule.template_id,
        items=items,
    )


@router.get("/children/{child_id}/schedule", response_model=schemas.ScheduleEnvelope)
async def get_schedule(
    child_id: str, date: date, db: DB, _user: CurrentUser
) -> schemas.ScheduleEnvelope:
    await get_child_or_404(child_id, db)
    default_template_id = await _weekday_default_template_id(db, child_id, date)
    schedule = await _load_schedule(db, child_id, date)
    return schemas.ScheduleEnvelope(
        schedule=None if schedule is None else await _schedule_with_status(db, schedule),
        default_template_id=default_template_id,
    )


@router.post(
    "/children/{child_id}/schedule", response_model=schemas.ScheduleEnvelope, status_code=201
)
async def generate_schedule(
    child_id: str, body: schemas.ScheduleGenerate, db: DB, _user: ParentUser
) -> schemas.ScheduleEnvelope:
    """Generate (or one-tap regenerate) a day's schedule. Template resolution:
    explicit template_id, else the child's weekday default, else an empty
    schedule for ad-hoc items. Regeneration replaces the schedule config;
    the event history it pointed at is untouched (events are append-only)."""
    await get_child_or_404(child_id, db)

    template_id = body.template_id
    if template_id is None:
        template_id = await _weekday_default_template_id(db, child_id, body.schedule_date)
    template: models.RoutineTemplate | None = None
    if template_id is not None:
        result = await db.execute(
            select(models.RoutineTemplate)
            .where(models.RoutineTemplate.id == template_id)
            .options(selectinload(models.RoutineTemplate.steps))
        )
        template = result.scalar_one_or_none()
        if template is None or template.child_id != child_id:
            raise HTTPException(status_code=422, detail="Template not found for this child")

    existing = await _load_schedule(db, child_id, body.schedule_date)
    if existing is not None:
        await db.delete(existing)
        await db.flush()

    schedule = models.DailySchedule(
        child_id=child_id,
        schedule_date=body.schedule_date,
        template_id=template.id if template else None,
        items=[],
    )
    if template is not None:
        for step in template.steps:
            schedule.items.append(
                models.ScheduleItem(
                    source_step_id=step.id,
                    position=step.position,
                    title=step.title,
                    icon=step.icon,
                    duration_minutes=step.duration_minutes,
                    transition_warning_minutes=step.transition_warning_minutes,
                    activity_id=step.activity_id,
                )
            )
    db.add(schedule)
    await db.commit()

    schedule = await _load_schedule(db, child_id, body.schedule_date)
    assert schedule is not None
    return schemas.ScheduleEnvelope(
        schedule=await _schedule_with_status(db, schedule),
        default_template_id=await _weekday_default_template_id(db, child_id, body.schedule_date),
    )


@router.post("/schedules/{schedule_id}/items", response_model=schemas.ScheduleOut, status_code=201)
async def add_item(
    schedule_id: str, body: schemas.ScheduleItemCreate, db: DB, _user: ParentUser
) -> schemas.ScheduleOut:
    result = await db.execute(
        select(models.DailySchedule)
        .where(models.DailySchedule.id == schedule_id)
        .options(selectinload(models.DailySchedule.items))
    )
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if body.activity_id is not None:
        await get_activity_for_child_or_422(db, body.activity_id, schedule.child_id)
    position = body.position if body.position is not None else len(schedule.items)
    for existing in schedule.items:
        if existing.position >= position:
            existing.position += 1
    schedule.items.append(
        models.ScheduleItem(
            position=position,
            title=body.title,
            icon=body.icon,
            planned_start=body.planned_start,
            duration_minutes=body.duration_minutes,
            transition_warning_minutes=body.transition_warning_minutes,
            activity_id=body.activity_id,
        )
    )
    for index, item in enumerate(sorted(schedule.items, key=lambda i: i.position)):
        item.position = index
    await db.commit()
    schedule = await _load_schedule(db, schedule.child_id, schedule.schedule_date)
    assert schedule is not None
    return await _schedule_with_status(db, schedule)


@router.patch("/schedule-items/{item_id}", response_model=schemas.ScheduleOut)
async def update_item(
    item_id: str, body: schemas.ScheduleItemUpdate, db: DB, _user: ParentUser
) -> schemas.ScheduleOut:
    item = await db.get(models.ScheduleItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule item not found")
    result = await db.execute(
        select(models.DailySchedule)
        .where(models.DailySchedule.id == item.schedule_id)
        .options(selectinload(models.DailySchedule.items))
    )
    schedule = result.scalar_one()
    item = next(i for i in schedule.items if i.id == item_id)

    if body.position is not None and body.position != item.position:
        target = min(body.position, len(schedule.items) - 1)
        others = [i for i in schedule.items if i.id != item_id]
        others.sort(key=lambda i: i.position)
        others.insert(target, item)
        for index, ordered in enumerate(others):
            ordered.position = index
    # model_fields_set distinguishes "omitted" from "explicitly null" so that
    # nullable fields (icon, time, durations) can be cleared while dialing in
    provided = body.model_fields_set
    if body.title is not None:
        item.title = body.title
    if "icon" in provided:
        item.icon = body.icon
    if "planned_start" in provided:
        item.planned_start = body.planned_start
    if "duration_minutes" in provided:
        item.duration_minutes = body.duration_minutes
    if "transition_warning_minutes" in provided:
        item.transition_warning_minutes = body.transition_warning_minutes
    if "activity_id" in provided:
        if body.activity_id is not None:
            await get_activity_for_child_or_422(db, body.activity_id, schedule.child_id)
        item.activity_id = body.activity_id
    await db.commit()
    schedule = await _load_schedule(db, schedule.child_id, schedule.schedule_date)
    assert schedule is not None
    return await _schedule_with_status(db, schedule)


@router.delete("/schedule-items/{item_id}", response_model=schemas.ScheduleOut)
async def delete_item(item_id: str, db: DB, _user: ParentUser) -> schemas.ScheduleOut:
    item = await db.get(models.ScheduleItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule item not found")
    result = await db.execute(
        select(models.DailySchedule)
        .where(models.DailySchedule.id == item.schedule_id)
        .options(selectinload(models.DailySchedule.items))
    )
    schedule = result.scalar_one()
    schedule.items.remove(next(i for i in schedule.items if i.id == item_id))
    for index, ordered in enumerate(sorted(schedule.items, key=lambda i: i.position)):
        ordered.position = index
    await db.commit()
    schedule = await _load_schedule(db, schedule.child_id, schedule.schedule_date)
    assert schedule is not None
    return await _schedule_with_status(db, schedule)
