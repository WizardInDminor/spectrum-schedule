from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import select

from app import models, schemas
from app.deps import DB, CurrentUser, ParentUser, get_child_or_404, verify_csrf
from app.event_types import RETRACTED_PAYLOAD, validate_payload
from app.projections.resolve import resolve_corrections

router = APIRouter(tags=["events"], dependencies=[Depends(verify_csrf)])


@router.post("/children/{child_id}/events", response_model=schemas.EventOut, status_code=201)
async def append_event(
    child_id: str, body: schemas.EventCreate, db: DB, user: ParentUser
) -> models.Event:
    await get_child_or_404(child_id, db)
    try:
        payload = validate_payload(body.event_type, body.payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc

    event = models.Event(
        child_id=child_id,
        event_type=body.event_type,
        occurred_at=body.occurred_at or models.utcnow(),
        recorded_by=user.id,
        payload=payload,
        tags=body.tags,
    )
    db.add(event)
    await db.commit()
    return event


@router.get("/children/{child_id}/events", response_model=list[schemas.EventOut])
async def list_events(
    child_id: str,
    db: DB,
    _user: CurrentUser,
    type: str | None = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
    tag: str | None = None,
    resolved: bool = False,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[models.Event]:
    """Timeline. `resolved=true` collapses correction chains to their
    effective heads (dropping retractions) — what the timeline screen shows;
    the default raw stream keeps the full audit trail visible."""
    await get_child_or_404(child_id, db)
    query = (
        select(models.Event)
        .where(models.Event.child_id == child_id)
        .order_by(models.Event.occurred_at.desc(), models.Event.recorded_at.desc())
        .limit(limit)
    )
    if type is not None:
        query = query.where(models.Event.event_type == type)
    if from_ is not None:
        query = query.where(models.Event.occurred_at >= from_)
    if to is not None:
        query = query.where(models.Event.occurred_at < to)
    result = await db.execute(query)
    events = list(result.scalars())
    if resolved:
        heads = resolve_corrections(events)
        heads.sort(key=lambda e: (e.occurred_at, e.recorded_at), reverse=True)
        events = heads
    if tag is not None:
        # JSON-array containment is dialect-specific; the stream is small, filter here
        events = [e for e in events if tag in (e.tags or [])]
    return events


@router.post("/events/{event_id}/correct", response_model=schemas.EventOut, status_code=201)
async def correct_event(
    event_id: str, body: schemas.EventCorrect, db: DB, user: ParentUser
) -> models.Event:
    """Append a correction: same event type, pointing at the superseded event.
    `retracted: true` voids the chain; otherwise a full replacement payload is
    validated against the original's event type."""
    original = await db.get(models.Event, event_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Event not found")

    if body.retracted:
        payload = dict(RETRACTED_PAYLOAD)
    elif body.payload is not None:
        try:
            payload = validate_payload(original.event_type, body.payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc
    else:
        raise HTTPException(status_code=422, detail="Provide a payload or retracted=true")

    correction = models.Event(
        child_id=original.child_id,
        event_type=original.event_type,
        occurred_at=body.occurred_at or original.occurred_at,
        recorded_by=user.id,
        payload=payload,
        tags=original.tags,
        corrects_event_id=original.id,
    )
    db.add(correction)
    await db.commit()
    return correction
