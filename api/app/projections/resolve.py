"""Correction-chain resolution: the first step of every projection.

Works on any objects exposing `id`, `corrects_event_id`, `payload`, and
`recorded_at` — ORM rows in production, plain dataclasses in tests.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol


class EventLike(Protocol):
    id: str
    corrects_event_id: str | None
    payload: dict
    recorded_at: datetime


def is_retracted(payload: dict) -> bool:
    return bool(payload.get("retracted"))


def resolve_corrections[E: EventLike](events: Sequence[E]) -> list[E]:
    """Collapse each correction chain to its effective head.

    - Chain roots are events with no `corrects_event_id`.
    - If several corrections target the same event, the latest `recorded_at`
      wins (ties broken by id for determinism).
    - A head whose payload is `{"retracted": true}` drops the whole chain.
    - Corrections whose target is not in `events` are ignored (the caller
      filtered the stream; the chain is out of view).
    """
    correctors: dict[str, list[E]] = {}
    for event in events:
        if event.corrects_event_id is not None:
            correctors.setdefault(event.corrects_event_id, []).append(event)
    for chain in correctors.values():
        chain.sort(key=lambda e: (e.recorded_at, e.id))

    resolved: list[E] = []
    for root in events:
        if root.corrects_event_id is not None:
            continue
        head = root
        seen = {head.id}
        while head.id in correctors:
            head = correctors[head.id][-1]
            if head.id in seen:  # defensive: a cycle would mean corrupt data
                break
            seen.add(head.id)
        if is_retracted(head.payload):
            continue
        resolved.append(head)
    return resolved
