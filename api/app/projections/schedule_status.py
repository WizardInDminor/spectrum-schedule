"""Per-item status of a daily schedule, projected from the event stream."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.projections.resolve import resolve_corrections

STATUS_EVENT_TYPES = ("schedule_item_completed", "schedule_item_skipped")


class StatusEventLike(Protocol):
    id: str
    event_type: str
    corrects_event_id: str | None
    payload: dict
    occurred_at: datetime
    recorded_at: datetime


@dataclass(frozen=True)
class ItemStatus:
    status: str  # "done" | "skipped"
    event_id: str
    occurred_at: datetime
    reason: str | None = None


def schedule_item_statuses(
    item_ids: Sequence[str], events: Sequence[StatusEventLike]
) -> dict[str, ItemStatus]:
    """Map schedule_item_id → effective status.

    `events` is the raw stream filtered to completed/skipped types for the
    child (corrections included); resolution happens here so callers cannot
    forget it. When multiple resolved events touch one item, the latest
    `occurred_at` (then `recorded_at`) wins.
    """
    statuses: dict[str, tuple[datetime, datetime, ItemStatus]] = {}
    wanted = set(item_ids)

    for event in resolve_corrections(list(events)):
        if event.event_type not in STATUS_EVENT_TYPES:
            continue
        item_id = event.payload.get("schedule_item_id")
        if item_id not in wanted:
            continue
        key = (event.occurred_at, event.recorded_at)
        current = statuses.get(item_id)
        if current is not None and (current[0], current[1]) >= key:
            continue
        statuses[item_id] = (
            event.occurred_at,
            event.recorded_at,
            ItemStatus(
                status="done" if event.event_type == "schedule_item_completed" else "skipped",
                event_id=event.id,
                occurred_at=event.occurred_at,
                reason=event.payload.get("reason"),
            ),
        )

    return {item_id: entry[2] for item_id, entry in statuses.items()}
