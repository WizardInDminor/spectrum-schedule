"""The event-type catalog: payload schemas for everything that can be appended
to the event log. A breaking payload change means a new event type, never an
edit to an existing schema (additive changes only)."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScheduleItemCompleted(_Payload):
    schedule_item_id: str
    planned_date: date


class ScheduleItemSkipped(_Payload):
    schedule_item_id: str
    planned_date: date
    reason: str | None = None


class NoteAdded(_Payload):
    text: str
    subject_type: str | None = None
    subject_id: str | None = None


EVENT_PAYLOADS: dict[str, type[_Payload]] = {
    "schedule_item_completed": ScheduleItemCompleted,
    "schedule_item_skipped": ScheduleItemSkipped,
    "note_added": NoteAdded,
}

RETRACTED_PAYLOAD = {"retracted": True}


def validate_payload(event_type: str, payload: dict) -> dict:
    """Validate and normalize a payload for its event type; raises ValueError
    for unknown types (pydantic.ValidationError for bad payloads)."""
    schema = EVENT_PAYLOADS.get(event_type)
    if schema is None:
        raise ValueError(f"unknown event_type: {event_type}")
    return schema.model_validate(payload).model_dump(mode="json")
