"""Starter routine templates a family can load once and tweak in the editor.

Step titles are generic activity names — no PII. Clock anchoring (e.g. school
at noon) happens day-of on schedule items, since template steps only carry
order, duration, and transition warnings.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models


@dataclass(frozen=True)
class StarterStep:
    title: str
    icon: str
    duration_minutes: int | None = None
    transition_warning_minutes: int | None = None


STARTER_TEMPLATES: dict[str, list[StarterStep]] = {
    "School Day": [
        StarterStep("Wake up", "☀️"),
        StarterStep("Potty practice", "🚽", 10),
        StarterStep("Breakfast", "🥣", 25, 5),
        StarterStep("Music time", "🎵", 20, 5),
        StarterStep("Sensory play", "🖐️", 25, 5),
        StarterStep("Outside play", "🌳", 30, 5),
        StarterStep("Drive to school", "🚗", 20),
        StarterStep("School", "🏫", 180),
        StarterStep("Drive home", "🚗", 20),
        StarterStep("Screen time", "📱", 30, 5),
        StarterStep("Dinner", "🍽️", 30, 5),
        StarterStep("Quiet time", "🧸", 30, 5),
        StarterStep("Bath", "🛁", 20, 5),
        StarterStep("Bedtime", "🌙"),
    ],
    "Home Day": [
        StarterStep("Wake up", "☀️"),
        StarterStep("Potty practice", "🚽", 10),
        StarterStep("Breakfast", "🥣", 25, 5),
        StarterStep("Music time", "🎵", 20, 5),
        StarterStep("Sensory play", "🖐️", 25, 5),
        StarterStep("Outside play", "🌳", 45, 5),
        StarterStep("Lunch", "🥪", 30, 5),
        StarterStep("Quiet time", "🧸", 45, 5),
        StarterStep("Screen time", "📱", 30, 5),
        StarterStep("Outside play", "🌳", 30, 5),
        StarterStep("Dinner", "🍽️", 30, 5),
        StarterStep("Quiet time", "🧸", 30, 5),
        StarterStep("Bath", "🛁", 20, 5),
        StarterStep("Bedtime", "🌙"),
    ],
}


async def seed_starter_templates(db: AsyncSession, child_id: str) -> list[str]:
    """Create the starter templates for a child; returns the names created.
    Templates whose name already exists for the child are left untouched."""
    child = await db.get(models.Child, child_id)
    if child is None:
        raise ValueError(f"child not found: {child_id}")

    result = await db.execute(
        select(models.RoutineTemplate.name).where(models.RoutineTemplate.child_id == child_id)
    )
    existing_names = set(result.scalars())

    created: list[str] = []
    for name, steps in STARTER_TEMPLATES.items():
        if name in existing_names:
            continue
        db.add(
            models.RoutineTemplate(
                child_id=child_id,
                name=name,
                steps=[
                    models.RoutineStep(
                        position=position,
                        title=step.title,
                        icon=step.icon,
                        duration_minutes=step.duration_minutes,
                        transition_warning_minutes=step.transition_warning_minutes,
                    )
                    for position, step in enumerate(steps)
                ],
            )
        )
        created.append(name)
    await db.commit()
    return created
