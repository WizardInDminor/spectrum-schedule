"""Preference confidence: what the accumulated evidence currently says.

Each resolved `preference_evidence` event contributes its direction (+1
confirms the preference as defined, -1 contradicts it) weighted by
exponential recency decay, so a preference that stopped being confirmed
fades over months instead of staying "strong" forever.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.projections.resolve import resolve_corrections

HALF_LIFE_DAYS = 90.0

# score thresholds → human label (by absolute value)
_LABELS = [(3.0, "strong"), (1.0, "moderate"), (0.0, "emerging")]


class EvidenceEventLike(Protocol):
    id: str
    event_type: str
    corrects_event_id: str | None
    payload: dict
    occurred_at: datetime
    recorded_at: datetime


@dataclass(frozen=True)
class PreferenceConfidence:
    score: float  # signed; positive = evidence confirms the preference
    label: str  # emerging | moderate | strong ("mixed" when contested)
    evidence_count: int
    last_observed: datetime | None


def _label(score: float, positives: int, negatives: int) -> str:
    if positives and negatives and min(positives, negatives) / (positives + negatives) >= 0.3:
        return "mixed"
    for threshold, label in _LABELS:
        if abs(score) >= threshold:
            return label
    return "emerging"


def preference_confidences(
    preference_ids: Sequence[str],
    events: Sequence[EvidenceEventLike],
    now: datetime,
    half_life_days: float = HALF_LIFE_DAYS,
) -> dict[str, PreferenceConfidence]:
    """Map preference_id → confidence, from the raw preference_evidence
    stream (corrections included; resolution happens here). Preferences with
    no surviving evidence are absent from the result."""
    wanted = set(preference_ids)
    tallies: dict[str, dict] = {}

    for event in resolve_corrections(list(events)):
        if event.event_type != "preference_evidence":
            continue
        preference_id = event.payload.get("preference_id")
        if preference_id not in wanted:
            continue
        direction = event.payload.get("direction", 0)
        age_days = max((now - event.occurred_at).total_seconds() / 86400, 0.0)
        weight = 2 ** (-age_days / half_life_days)
        tally = tallies.setdefault(
            preference_id, {"score": 0.0, "count": 0, "pos": 0, "neg": 0, "last": None}
        )
        tally["score"] += direction * weight
        tally["count"] += 1
        if direction > 0:
            tally["pos"] += 1
        elif direction < 0:
            tally["neg"] += 1
        if tally["last"] is None or event.occurred_at > tally["last"]:
            tally["last"] = event.occurred_at

    return {
        preference_id: PreferenceConfidence(
            score=round(tally["score"], 3),
            label=_label(tally["score"], tally["pos"], tally["neg"]),
            evidence_count=tally["count"],
            last_observed=tally["last"],
        )
        for preference_id, tally in tallies.items()
    }
