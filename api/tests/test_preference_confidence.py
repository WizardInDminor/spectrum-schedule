"""Unit tests for the confidence projection — pure fixtures, no DB."""

from datetime import UTC, datetime, timedelta

from app.projections.preference_confidence import preference_confidences
from tests.test_projections import FakeEvent

NOW = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)


def evidence(event_id: str, preference_id: str, direction: int, days_ago: float = 0, **kw):
    return FakeEvent(
        id=event_id,
        event_type="preference_evidence",
        payload={"preference_id": preference_id, "direction": direction},
        occurred_at=NOW - timedelta(days=days_ago),
        recorded_at=NOW - timedelta(days=days_ago),
        **kw,
    )


def test_fresh_evidence_counts_fully():
    result = preference_confidences(
        ["p1"], [evidence("e1", "p1", 1), evidence("e2", "p1", 1)], now=NOW
    )
    assert result["p1"].score == 2.0
    assert result["p1"].evidence_count == 2


def test_half_life_decay():
    result = preference_confidences(["p1"], [evidence("e1", "p1", 1, days_ago=90)], now=NOW)
    assert abs(result["p1"].score - 0.5) < 0.001  # one half-life → half weight


def test_negative_evidence_subtracts():
    result = preference_confidences(
        ["p1"], [evidence("e1", "p1", 1), evidence("e2", "p1", -1)], now=NOW
    )
    assert abs(result["p1"].score) < 0.001


def test_mixed_label_when_contested():
    events = [evidence(f"e{i}", "p1", 1) for i in range(3)]
    events += [evidence(f"n{i}", "p1", -1) for i in range(2)]
    result = preference_confidences(["p1"], events, now=NOW)
    assert result["p1"].label == "mixed"


def test_labels_scale_with_score():
    one = preference_confidences(["p1"], [evidence("e1", "p1", 1)], now=NOW)
    assert one["p1"].label == "moderate"  # score 1.0 crosses the moderate threshold

    faded = preference_confidences(["p1"], [evidence("e1", "p1", 1, days_ago=200)], now=NOW)
    assert faded["p1"].label == "emerging"

    strong = preference_confidences(["p1"], [evidence(f"e{i}", "p1", 1) for i in range(4)], now=NOW)
    assert strong["p1"].label == "strong"


def test_retraction_removes_contribution():
    events = [
        evidence("e1", "p1", 1),
        FakeEvent(
            id="e2",
            event_type="preference_evidence",
            payload={"retracted": True},
            corrects_event_id="e1",
            occurred_at=NOW,
            recorded_at=NOW,
        ),
    ]
    assert preference_confidences(["p1"], events, now=NOW) == {}


def test_unknown_preferences_and_other_events_ignored():
    events = [
        evidence("e1", "other", 1),
        FakeEvent(id="n1", event_type="note_added", payload={"text": "hi"}),
    ]
    assert preference_confidences(["p1"], events, now=NOW) == {}


def test_last_observed_is_newest_event():
    result = preference_confidences(
        ["p1"],
        [evidence("e1", "p1", 1, days_ago=10), evidence("e2", "p1", 1, days_ago=2)],
        now=NOW,
    )
    assert result["p1"].last_observed == NOW - timedelta(days=2)
