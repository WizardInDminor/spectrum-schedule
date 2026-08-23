from tests.test_templates import add_step, make_template

DATE = "2026-08-24"  # a Monday


async def generate(client, headers, child_id: str, **body) -> dict:
    response = await client.post(
        f"/v1/children/{child_id}/schedule",
        headers=headers,
        json={"schedule_date": DATE, **body},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_generate_from_explicit_template(client, parent_headers, child):
    template = await make_template(client, parent_headers, child.id)
    await add_step(client, parent_headers, template["id"], "Wake up", icon="☀️")
    await add_step(client, parent_headers, template["id"], "Breakfast", duration_minutes=20)

    body = await generate(client, parent_headers, child.id, template_id=template["id"])
    schedule = body["schedule"]
    assert schedule["template_id"] == template["id"]
    assert [i["title"] for i in schedule["items"]] == ["Wake up", "Breakfast"]
    assert all(i["item_status"] is None for i in schedule["items"])
    assert schedule["items"][0]["source_step_id"] is not None


async def test_generate_resolves_weekday_default(client, parent_headers, child):
    template = await make_template(client, parent_headers, child.id)
    await add_step(client, parent_headers, template["id"], "Wake up")
    await client.put(
        f"/v1/children/{child.id}/weekday-defaults",
        headers=parent_headers,
        json={"defaults": {"0": template["id"]}},  # DATE is a Monday
    )
    body = await generate(client, parent_headers, child.id)
    assert body["schedule"]["template_id"] == template["id"]
    assert body["default_template_id"] == template["id"]


async def test_generate_without_template_creates_empty_schedule(client, parent_headers, child):
    body = await generate(client, parent_headers, child.id)
    assert body["schedule"]["template_id"] is None
    assert body["schedule"]["items"] == []


async def test_regenerate_replaces_items(client, parent_headers, child):
    first = await make_template(client, parent_headers, child.id, name="Version 1")
    await add_step(client, parent_headers, first["id"], "Old step")
    await generate(client, parent_headers, child.id, template_id=first["id"])

    second = await make_template(client, parent_headers, child.id, name="Version 2")
    await add_step(client, parent_headers, second["id"], "New step")
    body = await generate(client, parent_headers, child.id, template_id=second["id"])

    assert [i["title"] for i in body["schedule"]["items"]] == ["New step"]

    got = await client.get(
        f"/v1/children/{child.id}/schedule", params={"date": DATE}, headers=parent_headers
    )
    assert [i["title"] for i in got.json()["schedule"]["items"]] == ["New step"]


async def test_get_missing_schedule_returns_null_envelope(client, parent_headers, child):
    response = await client.get(
        f"/v1/children/{child.id}/schedule", params={"date": DATE}, headers=parent_headers
    )
    assert response.status_code == 200
    assert response.json() == {"schedule": None, "default_template_id": None}


async def test_ad_hoc_item_add_update_delete(client, parent_headers, child):
    body = await generate(client, parent_headers, child.id)
    schedule_id = body["schedule"]["id"]

    added = await client.post(
        f"/v1/schedules/{schedule_id}/items",
        headers=parent_headers,
        json={"title": "Dentist", "planned_start": "14:30:00", "duration_minutes": 45},
    )
    assert added.status_code == 201
    item = added.json()["items"][0]
    assert item["source_step_id"] is None
    assert item["planned_start"] == "14:30:00"

    patched = await client.patch(
        f"/v1/schedule-items/{item['id']}", headers=parent_headers, json={"title": "Dentist visit"}
    )
    assert patched.json()["items"][0]["title"] == "Dentist visit"

    deleted = await client.delete(f"/v1/schedule-items/{item['id']}", headers=parent_headers)
    assert deleted.json()["items"] == []


async def test_caregiver_reads_schedule_but_cannot_generate(
    client, parent_headers, caregiver_client, caregiver_headers, child
):
    await generate(client, parent_headers, child.id)
    got = await caregiver_client.get(
        f"/v1/children/{child.id}/schedule", params={"date": DATE}, headers=caregiver_headers
    )
    assert got.status_code == 200

    response = await caregiver_client.post(
        f"/v1/children/{child.id}/schedule",
        headers=caregiver_headers,
        json={"schedule_date": DATE},
    )
    assert response.status_code == 403


async def test_schedule_reflects_completion_events(client, parent_headers, child):
    template = await make_template(client, parent_headers, child.id)
    await add_step(client, parent_headers, template["id"], "Wake up")
    body = await generate(client, parent_headers, child.id, template_id=template["id"])
    item = body["schedule"]["items"][0]

    event = await client.post(
        f"/v1/children/{child.id}/events",
        headers=parent_headers,
        json={
            "event_type": "schedule_item_completed",
            "payload": {"schedule_item_id": item["id"], "planned_date": DATE},
        },
    )
    assert event.status_code == 201

    got = await client.get(
        f"/v1/children/{child.id}/schedule", params={"date": DATE}, headers=parent_headers
    )
    status = got.json()["schedule"]["items"][0]["item_status"]
    assert status["status"] == "done"
    assert status["event_id"] == event.json()["id"]
