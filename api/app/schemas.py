from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Deliberately not pydantic's EmailStr: that requires the email-validator
# package, and a shape check is enough for a family-sized user table.
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- auth / users ---


class LoginIn(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN)
    password: str


class UserOut(ORMModel):
    id: str
    email: str
    display_name: str
    role: str
    is_active: bool


class UserCreate(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=120)
    role: str = Field(pattern="^(parent|caregiver)$")


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: str | None = Field(default=None, pattern="^(parent|caregiver)$")
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)


# --- children ---


def _validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"unknown IANA timezone: {value}") from exc
    return value


class ChildOut(ORMModel):
    id: str
    display_name: str
    birth_date: date | None
    timezone: str


class ChildCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    birth_date: date | None = None
    timezone: str

    _tz = field_validator("timezone")(_validate_timezone)


class ChildUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    birth_date: date | None = None
    timezone: str | None = None

    @field_validator("timezone")
    @classmethod
    def _tz(cls, value: str | None) -> str | None:
        return None if value is None else _validate_timezone(value)


# --- routine templates ---


class StepOut(ORMModel):
    id: str
    position: int
    title: str
    icon: str | None
    duration_minutes: int | None
    transition_warning_minutes: int | None
    notes: str | None


class StepCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    icon: str | None = Field(default=None, max_length=60)
    duration_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    transition_warning_minutes: int | None = Field(default=None, ge=1, le=120)
    notes: str | None = None
    position: int | None = Field(default=None, ge=0)


class StepUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    icon: str | None = Field(default=None, max_length=60)
    duration_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    transition_warning_minutes: int | None = Field(default=None, ge=1, le=120)
    notes: str | None = None
    position: int | None = Field(default=None, ge=0)


class TemplateOut(ORMModel):
    id: str
    child_id: str
    name: str
    is_active: bool
    steps: list[StepOut]


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_active: bool | None = None


class WeekdayDefaultsOut(BaseModel):
    # weekday (ISO 0=Mon … 6=Sun) → template id or null
    defaults: dict[int, str | None]


class WeekdayDefaultsIn(BaseModel):
    defaults: dict[int, str | None]

    @field_validator("defaults")
    @classmethod
    def _weekday_range(cls, value: dict[int, str | None]) -> dict[int, str | None]:
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("weekday keys must be 0–6 (ISO, 0=Monday)")
        return value


# --- daily schedules ---


class ScheduleItemOut(ORMModel):
    id: str
    source_step_id: str | None
    position: int
    title: str
    icon: str | None
    planned_start: time | None
    duration_minutes: int | None
    transition_warning_minutes: int | None


class ItemStatusOut(BaseModel):
    status: str
    event_id: str
    occurred_at: datetime
    reason: str | None = None


class ScheduleItemWithStatus(ScheduleItemOut):
    item_status: ItemStatusOut | None = None


class ScheduleOut(BaseModel):
    id: str
    child_id: str
    schedule_date: date
    template_id: str | None
    items: list[ScheduleItemWithStatus]


class ScheduleEnvelope(BaseModel):
    schedule: ScheduleOut | None
    default_template_id: str | None


class ScheduleGenerate(BaseModel):
    schedule_date: date
    template_id: str | None = None


class ScheduleItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    icon: str | None = Field(default=None, max_length=60)
    planned_start: time | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    transition_warning_minutes: int | None = Field(default=None, ge=1, le=120)
    position: int | None = Field(default=None, ge=0)


class ScheduleItemUpdate(ScheduleItemCreate):
    title: str | None = Field(default=None, min_length=1, max_length=200)  # type: ignore[assignment]


# --- preferences ---

PREFERENCE_KINDS = "^(like|dislike|sensory_seeking|sensory_avoiding)$"
PREFERENCE_CATEGORIES = "^(food|sound|texture|activity|place|social|other)$"


class ConfidenceOut(BaseModel):
    score: float
    label: str
    evidence_count: int
    last_observed: datetime | None


class PreferenceOut(ORMModel):
    id: str
    child_id: str
    kind: str
    category: str
    label: str
    context: str | None
    confidence: ConfidenceOut | None = None


class PreferenceCreate(BaseModel):
    kind: str = Field(pattern=PREFERENCE_KINDS)
    category: str = Field(pattern=PREFERENCE_CATEGORIES)
    label: str = Field(min_length=1, max_length=200)
    context: str | None = None


class PreferenceUpdate(BaseModel):
    kind: str | None = Field(default=None, pattern=PREFERENCE_KINDS)
    category: str | None = Field(default=None, pattern=PREFERENCE_CATEGORIES)
    label: str | None = Field(default=None, min_length=1, max_length=200)
    context: str | None = None


# --- events ---


class EventOut(ORMModel):
    id: str
    child_id: str
    event_type: str
    occurred_at: datetime
    recorded_at: datetime
    recorded_by: str
    payload: dict
    tags: list
    corrects_event_id: str | None


class EventCreate(BaseModel):
    event_type: str
    occurred_at: datetime | None = None
    payload: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    @field_validator("occurred_at")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value


class EventCorrect(BaseModel):
    retracted: bool = False
    payload: dict | None = None
    occurred_at: datetime | None = None

    @field_validator("occurred_at")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value
