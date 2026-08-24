"""The event-type catalog: payload schemas for everything that can be appended
to the event log. A breaking payload change means a new event type, never an
edit to an existing schema (additive changes only)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class PreferenceEvidence(_Payload):
    preference_id: str
    direction: Literal[1, -1]  # +1 confirms the preference, -1 contradicts it
    context: str | None = None
    note: str | None = None


class ObservationRecorded(_Payload):
    mood: int | None = Field(default=None, ge=1, le=5)
    regulation: int | None = Field(default=None, ge=1, le=5)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    text: str | None = None

    @model_validator(mode="after")
    def _not_empty(self) -> "ObservationRecorded":
        if all(
            value is None
            for value in (self.mood, self.regulation, self.sleep_hours, self.sleep_quality)
        ) and not (self.text and self.text.strip()):
            raise ValueError("an observation needs at least one rating, sleep value, or text")
        return self


class IncidentRecorded(_Payload):
    antecedent: str = Field(min_length=1)
    behavior: str = Field(min_length=1)
    consequence: str = Field(min_length=1)
    intensity: int = Field(ge=1, le=5)
    duration_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    location: str | None = None


class ActivityRun(_Payload):
    activity_id: str
    context: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)  # how it went
    note: str | None = None


EVENT_PAYLOADS: dict[str, type[_Payload]] = {
    "schedule_item_completed": ScheduleItemCompleted,
    "schedule_item_skipped": ScheduleItemSkipped,
    "note_added": NoteAdded,
    "preference_evidence": PreferenceEvidence,
    "observation_recorded": ObservationRecorded,
    "incident_recorded": IncidentRecorded,
    "activity_run": ActivityRun,
}

RETRACTED_PAYLOAD = {"retracted": True}


def validate_payload(event_type: str, payload: dict) -> dict:
    """Validate and normalize a payload for its event type; raises ValueError
    for unknown types (pydantic.ValidationError for bad payloads)."""
    schema = EVENT_PAYLOADS.get(event_type)
    if schema is None:
        raise ValueError(f"unknown event_type: {event_type}")
    return schema.model_validate(payload).model_dump(mode="json")
