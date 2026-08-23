from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app import models, schemas
from app.deps import DB, CurrentUser, ParentUser, get_child_or_404, verify_csrf
from app.projections.preference_confidence import preference_confidences

router = APIRouter(tags=["preferences"], dependencies=[Depends(verify_csrf)])


@router.get("/children/{child_id}/preferences", response_model=list[schemas.PreferenceOut])
async def list_preferences(
    child_id: str, db: DB, _user: CurrentUser
) -> list[schemas.PreferenceOut]:
    await get_child_or_404(child_id, db)
    result = await db.execute(
        select(models.Preference)
        .where(models.Preference.child_id == child_id)
        .order_by(models.Preference.created_at)
    )
    preferences = list(result.scalars())

    events = await db.execute(
        select(models.Event).where(
            models.Event.child_id == child_id,
            models.Event.event_type == "preference_evidence",
        )
    )
    confidences = preference_confidences(
        [p.id for p in preferences], list(events.scalars()), now=models.utcnow()
    )

    out = []
    for preference in preferences:
        row = schemas.PreferenceOut.model_validate(preference)
        confidence = confidences.get(preference.id)
        if confidence is not None:
            row.confidence = schemas.ConfidenceOut(
                score=confidence.score,
                label=confidence.label,
                evidence_count=confidence.evidence_count,
                last_observed=confidence.last_observed,
            )
        out.append(row)
    # strongest current signal first; undefined/no-evidence last
    out.sort(key=lambda p: abs(p.confidence.score) if p.confidence else -1, reverse=True)
    return out


@router.post(
    "/children/{child_id}/preferences", response_model=schemas.PreferenceOut, status_code=201
)
async def create_preference(
    child_id: str, body: schemas.PreferenceCreate, db: DB, _user: ParentUser
) -> models.Preference:
    await get_child_or_404(child_id, db)
    preference = models.Preference(
        child_id=child_id,
        kind=body.kind,
        category=body.category,
        label=body.label,
        context=body.context,
    )
    db.add(preference)
    await db.commit()
    return preference


@router.patch("/preferences/{preference_id}", response_model=schemas.PreferenceOut)
async def update_preference(
    preference_id: str, body: schemas.PreferenceUpdate, db: DB, _user: ParentUser
) -> models.Preference:
    preference = await db.get(models.Preference, preference_id)
    if preference is None:
        raise HTTPException(status_code=404, detail="Preference not found")
    provided = body.model_fields_set
    if body.kind is not None:
        preference.kind = body.kind
    if body.category is not None:
        preference.category = body.category
    if body.label is not None:
        preference.label = body.label
    if "context" in provided:
        preference.context = body.context
    await db.commit()
    return preference
