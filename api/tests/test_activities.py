from tests.test_schedules import generate
from tests.test_templates import make_template


async def make_activity(client, headers, child_id: str, **overrides) -> dict:
    body = {
        "title": "Count the cart",
        "icon": "🛒",
        "description": "At checkout, count items as they go on the belt. "
        "Variation: count only the red ones.",
        "skill_tags": ["counting", "attention"],
        "context_tags": ["grocery-store"],
        "duration_minutes": 5,
        **overrides,
    }
    response = await client.post(f"/v1/children/{child_id}/activities", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def test_create_and_list_activities(client, parent_headers, child):
    await make_activity(client, parent_headers, child.id)
    await make_activity(
        client, parent_headers, child.id, title="Animal walk race", context_tags=["grandparents"]
    )

    listed = await client.get(f"/v1/children/{child.id}/activities", headers=parent_headers)
    assert listed.status_code == 200
    titles = [a["title"] for a in listed.json()]
    assert titles == sorted(titles)
    assert len(titles) == 2


async def test_update_and_clear_fields(client, parent_headers, child):
    activity = await make_activity(client, parent_headers, child.id)
    updated = await client.patch(
        f"/v1/activities/{activity['id']}",
        headers=parent_headers,
        json={
            "description": "New rules",
            "duration_minutes": None,
            "skill_tags": ["counting"],
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["description"] == "New rules"
    assert body["duration_minutes"] is None
    assert body["skill_tags"] == ["counting"]
    assert body["title"] == "Count the cart"  # untouched


async def test_archive_hides_from_default_list(client, parent_headers, child):
    activity = await make_activity(client, parent_headers, child.id)
    await client.patch(
        f"/v1/activities/{activity['id']}", headers=parent_headers, json={"is_archived": True}
    )

    default = await client.get(f"/v1/children/{child.id}/activities", headers=parent_headers)
    assert default.json() == []

    with_archived = await client.get(
        f"/v1/children/{child.id}/activities",
        params={"include_archived": "true"},
        headers=parent_headers,
    )
    assert len(with_archived.json()) == 1


async def test_caregiver_reads_but_cannot_write(
    client, parent_headers, caregiver_client, caregiver_headers, child
):
    await make_activity(client, parent_headers, child.id)
    listed = await caregiver_client.get(
        f"/v1/children/{child.id}/activities", headers=caregiver_headers
    )
    assert listed.status_code == 200

    response = await caregiver_client.post(
        f"/v1/children/{child.id}/activities",
        headers=caregiver_headers,
        json={"title": "Nope"},
    )
    assert response.status_code == 403


async def test_activity_run_event(client, parent_headers, child):
    activity = await make_activity(client, parent_headers, child.id)
    response = await client.post(
        f"/v1/children/{child.id}/events",
        headers=parent_headers,
        json={
            "event_type": "activity_run",
            "payload": {
                "activity_id": activity["id"],
                "context": "grocery-store",
                "rating": 4,
                "note": "Made it through the whole line",
            },
        },
    )
    assert response.status_code == 201

    bad_rating = await client.post(
        f"/v1/children/{child.id}/events",
        headers=parent_headers,
        json={
            "event_type": "activity_run",
            "payload": {"activity_id": activity["id"], "rating": 9},
        },
    )
    assert bad_rating.status_code == 422


async def test_schedule_item_links_activity(client, parent_headers, child):
    activity = await make_activity(client, parent_headers, child.id)
    schedule = (await generate(client, parent_headers, child.id))["schedule"]

    added = await client.post(
        f"/v1/schedules/{schedule['id']}/items",
        headers=parent_headers,
        json={"title": activity["title"], "icon": activity["icon"], "activity_id": activity["id"]},
    )
    assert added.status_code == 201
    item = added.json()["items"][0]
    assert item["activity_id"] == activity["id"]

    unlinked = await client.patch(
        f"/v1/schedule-items/{item['id']}", headers=parent_headers, json={"activity_id": None}
    )
    assert unlinked.json()["items"][0]["activity_id"] is None


async def test_step_links_activity_and_flows_into_schedule(client, parent_headers, child):
    activity = await make_activity(client, parent_headers, child.id)
    template = await make_template(client, parent_headers, child.id)
    step_resp = await client.post(
        f"/v1/templates/{template['id']}/steps",
        headers=parent_headers,
        json={"title": "Checkout game", "activity_id": activity["id"]},
    )
    assert step_resp.status_code == 201
    assert step_resp.json()["steps"][0]["activity_id"] == activity["id"]

    body = await generate(client, parent_headers, child.id, template_id=template["id"])
    assert body["schedule"]["items"][0]["activity_id"] == activity["id"]


async def test_foreign_activity_rejected(client, parent_headers, child, db_sessionmaker):
    from app import models

    async with db_sessionmaker() as db:
        other = models.Child(display_name="Test Child B", timezone="UTC")
        db.add(other)
        await db.commit()
        other_id = other.id
    foreign = await make_activity(client, parent_headers, other_id, title="Foreign")

    schedule = (await generate(client, parent_headers, child.id))["schedule"]
    response = await client.post(
        f"/v1/schedules/{schedule['id']}/items",
        headers=parent_headers,
        json={"title": "X", "activity_id": foreign["id"]},
    )
    assert response.status_code == 422
