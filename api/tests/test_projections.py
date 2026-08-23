"""Projection unit tests: pure functions over fixture events, no database."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.projections.resolve import resolve_corrections
from app.projections.schedule_status import schedule_item_statuses


@dataclass
class FakeEvent:
    id: str
    event_type: str = "schedule_item_completed"
    payload: dict = field(default_factory=dict)
    corrects_event_id: str | None = None
    occurred_at: datetime = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
    recorded_at: datetime = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 24, hour, minute, tzinfo=UTC)


# --- resolve_corrections ---


def test_uncorrected_events_pass_through():
    events = [FakeEvent(id="a"), FakeEvent(id="b")]
    assert [e.id for e in resolve_corrections(events)] == ["a", "b"]


def test_correction_replaces_root():
    events = [
        FakeEvent(id="a", payload={"v": 1}),
        FakeEvent(id="b", payload={"v": 2}, corrects_event_id="a", recorded_at=at(13)),
    ]
    resolved = resolve_corrections(events)
    assert [e.id for e in resolved] == ["b"]
    assert resolved[0].payload == {"v": 2}


def test_latest_of_competing_corrections_wins():
    events = [
        FakeEvent(id="a"),
        FakeEvent(id="b", corrects_event_id="a", recorded_at=at(13)),
        FakeEvent(id="c", corrects_event_id="a", recorded_at=at(14)),
    ]
    assert [e.id for e in resolve_corrections(events)] == ["c"]


def test_correction_chain_follows_to_head():
    events = [
        FakeEvent(id="a"),
        FakeEvent(id="b", corrects_event_id="a", recorded_at=at(13)),
        FakeEvent(id="c", corrects_event_id="b", recorded_at=at(14)),
    ]
    assert [e.id for e in resolve_corrections(events)] == ["c"]


def test_retracted_head_drops_chain():
    events = [
        FakeEvent(id="a"),
        FakeEvent(id="b", payload={"retracted": True}, corrects_event_id="a", recorded_at=at(13)),
        FakeEvent(id="other"),
    ]
    assert [e.id for e in resolve_corrections(events)] == ["other"]


# --- schedule_item_statuses ---


def done(event_id: str, item_id: str, **kw) -> FakeEvent:
    return FakeEvent(
        id=event_id,
        event_type="schedule_item_completed",
        payload={"schedule_item_id": item_id, "planned_date": "2026-08-24"},
        **kw,
    )


def skipped(event_id: str, item_id: str, reason: str | None = None, **kw) -> FakeEvent:
    payload = {"schedule_item_id": item_id, "planned_date": "2026-08-24"}
    if reason is not None:
        payload["reason"] = reason
    return FakeEvent(id=event_id, event_type="schedule_item_skipped", payload=payload, **kw)


def test_done_and_skipped_statuses():
    statuses = schedule_item_statuses(
        ["item-1", "item-2", "item-3"],
        [done("e1", "item-1"), skipped("e2", "item-2", reason="meltdown recovery")],
    )
    assert statuses["item-1"].status == "done"
    assert statuses["item-2"].status == "skipped"
    assert statuses["item-2"].reason == "meltdown recovery"
    assert "item-3" not in statuses


def test_events_for_other_items_ignored():
    statuses = schedule_item_statuses(["item-1"], [done("e1", "other-item")])
    assert statuses == {}


def test_later_event_wins_per_item():
    statuses = schedule_item_statuses(
        ["item-1"],
        [
            done("e1", "item-1", occurred_at=at(12)),
            skipped("e2", "item-1", occurred_at=at(13)),
        ],
    )
    assert statuses["item-1"].status == "skipped"


def test_retraction_returns_item_to_pending():
    events = [
        done("e1", "item-1"),
        FakeEvent(
            id="e2",
            payload={"retracted": True},
            corrects_event_id="e1",
            recorded_at=at(13),
        ),
    ]
    assert schedule_item_statuses(["item-1"], events) == {}


def test_note_events_do_not_affect_status():
    events = [FakeEvent(id="n1", event_type="note_added", payload={"text": "hi"})]
    assert schedule_item_statuses(["item-1"], events) == {}
