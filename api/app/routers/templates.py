from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.deps import DB, CurrentUser, ParentUser, get_child_or_404, verify_csrf

router = APIRouter(tags=["templates"], dependencies=[Depends(verify_csrf)])


async def _get_template(db, template_id: str, with_steps: bool = True) -> models.RoutineTemplate:
    # populate_existing: mutated in-session objects must reload so the steps
    # collection comes back in fresh position order
    query = (
        select(models.RoutineTemplate)
        .where(models.RoutineTemplate.id == template_id)
        .execution_options(populate_existing=True)
    )
    if with_steps:
        query = query.options(selectinload(models.RoutineTemplate.steps))
    result = await db.execute(query)
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.get("/children/{child_id}/templates", response_model=list[schemas.TemplateOut])
async def list_templates(child_id: str, db: DB, _user: CurrentUser) -> list[models.RoutineTemplate]:
    await get_child_or_404(child_id, db)
    result = await db.execute(
        select(models.RoutineTemplate)
        .where(models.RoutineTemplate.child_id == child_id)
        .options(selectinload(models.RoutineTemplate.steps))
        .order_by(models.RoutineTemplate.created_at)
    )
    return list(result.scalars())


@router.post("/children/{child_id}/templates", response_model=schemas.TemplateOut, status_code=201)
async def create_template(
    child_id: str, body: schemas.TemplateCreate, db: DB, _user: ParentUser
) -> models.RoutineTemplate:
    await get_child_or_404(child_id, db)
    template = models.RoutineTemplate(child_id=child_id, name=body.name, steps=[])
    db.add(template)
    await db.commit()
    return await _get_template(db, template.id)


@router.patch("/templates/{template_id}", response_model=schemas.TemplateOut)
async def update_template(
    template_id: str, body: schemas.TemplateUpdate, db: DB, _user: ParentUser
) -> models.RoutineTemplate:
    template = await _get_template(db, template_id)
    if body.name is not None:
        template.name = body.name
    if body.is_active is not None:
        template.is_active = body.is_active
    await db.commit()
    return await _get_template(db, template_id)


def _renumber(steps: list[models.RoutineStep]) -> None:
    for index, step in enumerate(sorted(steps, key=lambda s: s.position)):
        step.position = index


@router.post("/templates/{template_id}/steps", response_model=schemas.TemplateOut, status_code=201)
async def add_step(
    template_id: str, body: schemas.StepCreate, db: DB, _user: ParentUser
) -> models.RoutineTemplate:
    template = await _get_template(db, template_id)
    position = body.position if body.position is not None else len(template.steps)
    step = models.RoutineStep(
        template_id=template_id,
        position=position,
        title=body.title,
        icon=body.icon,
        duration_minutes=body.duration_minutes,
        transition_warning_minutes=body.transition_warning_minutes,
        notes=body.notes,
    )
    # shift steps at/after the requested slot, then renumber densely
    for existing in template.steps:
        if existing.position >= position:
            existing.position += 1
    template.steps.append(step)
    _renumber(template.steps)
    await db.commit()
    return await _get_template(db, template_id)


@router.patch("/steps/{step_id}", response_model=schemas.TemplateOut)
async def update_step(
    step_id: str, body: schemas.StepUpdate, db: DB, _user: ParentUser
) -> models.RoutineTemplate:
    step = await db.get(models.RoutineStep, step_id)
    if step is None:
        raise HTTPException(status_code=404, detail="Step not found")
    template = await _get_template(db, step.template_id)
    step = next(s for s in template.steps if s.id == step_id)

    if body.position is not None and body.position != step.position:
        target = min(body.position, len(template.steps) - 1)
        others = [s for s in template.steps if s.id != step_id]
        others.sort(key=lambda s: s.position)
        others.insert(target, step)
        for index, ordered in enumerate(others):
            ordered.position = index
    # model_fields_set distinguishes "omitted" from "explicitly null" so that
    # nullable fields (icon, durations, notes) can be cleared while dialing in
    provided = body.model_fields_set
    if body.title is not None:
        step.title = body.title
    if "icon" in provided:
        step.icon = body.icon
    if "duration_minutes" in provided:
        step.duration_minutes = body.duration_minutes
    if "transition_warning_minutes" in provided:
        step.transition_warning_minutes = body.transition_warning_minutes
    if "notes" in provided:
        step.notes = body.notes
    await db.commit()
    return await _get_template(db, step.template_id)


@router.delete("/steps/{step_id}", response_model=schemas.TemplateOut)
async def delete_step(step_id: str, db: DB, _user: ParentUser) -> models.RoutineTemplate:
    step = await db.get(models.RoutineStep, step_id)
    if step is None:
        raise HTTPException(status_code=404, detail="Step not found")
    template = await _get_template(db, step.template_id)
    template.steps.remove(next(s for s in template.steps if s.id == step_id))
    _renumber(template.steps)
    await db.commit()
    return await _get_template(db, template.id)


@router.get("/children/{child_id}/weekday-defaults", response_model=schemas.WeekdayDefaultsOut)
async def get_weekday_defaults(
    child_id: str, db: DB, _user: CurrentUser
) -> schemas.WeekdayDefaultsOut:
    await get_child_or_404(child_id, db)
    result = await db.execute(
        select(models.WeekdayDefault).where(models.WeekdayDefault.child_id == child_id)
    )
    defaults: dict[int, str | None] = {day: None for day in range(7)}
    for row in result.scalars():
        defaults[row.weekday] = row.template_id
    return schemas.WeekdayDefaultsOut(defaults=defaults)


@router.put("/children/{child_id}/weekday-defaults", response_model=schemas.WeekdayDefaultsOut)
async def put_weekday_defaults(
    child_id: str, body: schemas.WeekdayDefaultsIn, db: DB, _user: ParentUser
) -> schemas.WeekdayDefaultsOut:
    await get_child_or_404(child_id, db)
    template_ids = {tid for tid in body.defaults.values() if tid is not None}
    for template_id in template_ids:
        template = await db.get(models.RoutineTemplate, template_id)
        if template is None or template.child_id != child_id:
            raise HTTPException(status_code=422, detail=f"Template not found: {template_id}")

    result = await db.execute(
        select(models.WeekdayDefault).where(models.WeekdayDefault.child_id == child_id)
    )
    existing = {row.weekday: row for row in result.scalars()}
    for weekday, template_id in body.defaults.items():
        row = existing.get(weekday)
        if template_id is None:
            if row is not None:
                await db.delete(row)
        elif row is None:
            db.add(
                models.WeekdayDefault(child_id=child_id, weekday=weekday, template_id=template_id)
            )
        else:
            row.template_id = template_id
    await db.commit()
    return await get_weekday_defaults(child_id, db, _user)
