import uuid
from datetime import UTC, date, datetime, time

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class TZDateTime(TypeDecorator):
    """UTC-aware datetimes on both sides of the driver, even on SQLite
    (which stores and returns naive values)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime rejected; all datetimes must be UTC-aware")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('parent', 'caregiver')", name="ck_users_role"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, onupdate=utcnow)


class AuthSession(Base):
    __tablename__ = "sessions"

    # id is the SHA-256 hex of the session token; the raw token lives only in the cookie
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(TZDateTime)

    user: Mapped[User] = relationship()


class Child(Base):
    __tablename__ = "children"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    display_name: Mapped[str] = mapped_column(String(120))  # PII: DB values only
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64))  # IANA name
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, onupdate=utcnow)


class RoutineTemplate(Base):
    __tablename__ = "routine_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    child_id: Mapped[str] = mapped_column(String(36), ForeignKey("children.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, onupdate=utcnow)

    steps: Mapped[list["RoutineStep"]] = relationship(
        cascade="all, delete-orphan", order_by="RoutineStep.position"
    )


class RoutineStep(Base):
    __tablename__ = "routine_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("routine_templates.id"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    icon: Mapped[str | None] = mapped_column(String(60), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transition_warning_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("activities.id"), nullable=True
    )


class WeekdayDefault(Base):
    __tablename__ = "weekday_defaults"
    __table_args__ = (
        UniqueConstraint("child_id", "weekday", name="uq_weekday_defaults_child_weekday"),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_weekday_defaults_weekday"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    child_id: Mapped[str] = mapped_column(String(36), ForeignKey("children.id"), index=True)
    weekday: Mapped[int] = mapped_column(Integer)  # ISO: 0=Monday … 6=Sunday
    template_id: Mapped[str] = mapped_column(String(36), ForeignKey("routine_templates.id"))


class DailySchedule(Base):
    __tablename__ = "daily_schedules"
    __table_args__ = (
        UniqueConstraint("child_id", "schedule_date", name="uq_daily_schedules_child_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    child_id: Mapped[str] = mapped_column(String(36), ForeignKey("children.id"), index=True)
    schedule_date: Mapped[date] = mapped_column(Date)  # in the child's timezone
    template_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("routine_templates.id"), nullable=True
    )
    generated_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)

    items: Mapped[list["ScheduleItem"]] = relationship(
        cascade="all, delete-orphan", order_by="ScheduleItem.position"
    )


class ScheduleItem(Base):
    __tablename__ = "schedule_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    schedule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("daily_schedules.id"), index=True
    )
    source_step_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("routine_steps.id"), nullable=True
    )
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    icon: Mapped[str | None] = mapped_column(String(60), nullable=True)
    planned_start: Mapped[time | None] = mapped_column(Time, nullable=True)  # child-local
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transition_warning_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activity_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("activities.id"), nullable=True
    )


class Activity(Base):
    """A designed, reusable activity: the documented 'how' (a game, an
    exercise, a coping routine) that can be linked into routine steps and
    schedule items, pulled from the stash by context, and logged as
    activity_run events when used."""

    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    child_id: Mapped[str] = mapped_column(String(36), ForeignKey("children.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    icon: Mapped[str | None] = mapped_column(String(60), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # setup, rules, variations
    materials: Mapped[str | None] = mapped_column(Text, nullable=True)
    skill_tags: Mapped[list] = mapped_column(JSON, default=list)  # attention, counting, …
    context_tags: Mapped[list] = mapped_column(JSON, default=list)  # grandparents, car, …
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, onupdate=utcnow)


class Preference(Base):
    """A preference *definition* (e.g. "crunchy textures", sensory_seeking,
    category texture). Confidence is never stored — it is projected from
    preference_evidence events with recency decay."""

    __tablename__ = "preferences"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('like', 'dislike', 'sensory_seeking', 'sensory_avoiding')",
            name="ck_preferences_kind",
        ),
        CheckConstraint(
            "category IN ('food', 'sound', 'texture', 'activity', 'place', 'social', 'other')",
            name="ck_preferences_category",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    child_id: Mapped[str] = mapped_column(String(36), ForeignKey("children.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(20))
    label: Mapped[str] = mapped_column(String(200))
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, onupdate=utcnow)


class Event(Base):
    """Append-only. No endpoint or migration may UPDATE or DELETE rows here;
    fixes are new rows pointing at the superseded one via corrects_event_id."""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    child_id: Mapped[str] = mapped_column(String(36), ForeignKey("children.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    occurred_at: Mapped[datetime] = mapped_column(TZDateTime, index=True)
    recorded_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    recorded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    corrects_event_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("events.id"), nullable=True, index=True
    )
