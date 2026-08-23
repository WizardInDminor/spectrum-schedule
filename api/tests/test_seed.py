import pytest

from app.seed import STARTER_TEMPLATES, seed_starter_templates


async def test_seed_creates_starter_templates(db_sessionmaker, child):
    async with db_sessionmaker() as db:
        created = await seed_starter_templates(db, child.id)
    assert set(created) == set(STARTER_TEMPLATES)


async def test_seed_is_idempotent_per_name(db_sessionmaker, child):
    async with db_sessionmaker() as db:
        await seed_starter_templates(db, child.id)
    async with db_sessionmaker() as db:
        created_again = await seed_starter_templates(db, child.id)
    assert created_again == []


async def test_seed_unknown_child_raises(db_sessionmaker):
    async with db_sessionmaker() as db:
        with pytest.raises(ValueError):
            await seed_starter_templates(db, "does-not-exist")


async def test_seeded_templates_visible_via_api(db_sessionmaker, client, parent_headers, child):
    async with db_sessionmaker() as db:
        await seed_starter_templates(db, child.id)

    response = await client.get(f"/v1/children/{child.id}/templates", headers=parent_headers)
    templates = {t["name"]: t for t in response.json()}
    assert set(templates) == set(STARTER_TEMPLATES)
    school = templates["School Day"]
    assert [s["title"] for s in school["steps"]][:3] == ["Wake up", "Potty practice", "Breakfast"]
    assert [s["position"] for s in school["steps"]] == list(range(len(school["steps"])))
