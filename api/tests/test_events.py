from tests.test_schedules import DATE, generate
from tests.test_templates import add_step, make_template


async def append_note(client, headers, child_id: str, text: str = "Great morning") -> dict:
    response = await client.post(
        f"/v1/children/{child_id}/events",
        headers=headers,
        json={"event_type": "note_added", "payload": {"text": text}, "tags": ["morning"]},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_append_note(client, parent_headers, child):
    body = await append_note(client, parent_headers, child.id)
    assert body["event_type"] == "note_added"
    assert body["payload"] == {"text": "Great morning", "subject_type": None, "subject_id": None}
    assert body["tags"] == ["morning"]
    assert body["corrects_event_id"] is None


async def test_unknown_event_type_rejected(client, parent_headers, child):
    response = await client.post(
        f"/v1/children/{child.id}/events",
        headers=parent_headers,
        json={"event_type": "made_up_thing", "payload": {}},
    )
    assert response.status_code == 422


async def test_bad_payload_rejected(client, parent_headers, child):
    response = await client.post(
        f"/v1/children/{child.id}/events",
        headers=parent_headers,
        json={"event_type": "note_added", "payload": {"nope": True}},
    )
    assert response.status_code == 422


async def test_caregiver_reads_timeline_but_cannot_append(
    client, parent_headers, caregiver_client, caregiver_headers, child
):
    await append_note(client, parent_headers, child.id)

    listed = await caregiver_client.get(
        f"/v1/children/{child.id}/events", headers=caregiver_headers
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    response = await caregiver_client.post(
        f"/v1/children/{child.id}/events",
        headers=caregiver_headers,
        json={"event_type": "note_added", "payload": {"text": "hi"}},
    )
    assert response.status_code == 403


async def test_timeline_filters(client, parent_headers, child):
    await append_note(client, parent_headers, child.id)
    schedule = (await generate(client, parent_headers, child.id))["schedule"]
    item_resp = await client.post(
        f"/v1/schedules/{schedule['id']}/items", headers=parent_headers, json={"title": "Lunch"}
    )
    item = item_resp.json()["items"][0]
    await client.post(
        f"/v1/children/{child.id}/events",
        headers=parent_headers,
        json={
            "event_type": "schedule_item_skipped",
            "payload": {"schedule_item_id": item["id"], "planned_date": DATE},
        },
    )

    all_events = await client.get(f"/v1/children/{child.id}/events", headers=parent_headers)
    assert len(all_events.json()) == 2

    notes = await client.get(
        f"/v1/children/{child.id}/events", params={"type": "note_added"}, headers=parent_headers
    )
    assert [e["event_type"] for e in notes.json()] == ["note_added"]

    tagged = await client.get(
        f"/v1/children/{child.id}/events", params={"tag": "morning"}, headers=parent_headers
    )
    assert len(tagged.json()) == 1


async def test_correction_supersedes_and_retraction_clears(client, parent_headers, child):
    template = await make_template(client, parent_headers, child.id)
    await add_step(client, parent_headers, template["id"], "Wake up")
    schedule = (await generate(client, parent_headers, child.id, template_id=template["id"]))[
        "schedule"
    ]
    item = schedule["items"][0]

    done = await client.post(
        f"/v1/children/{child.id}/events",
        headers=parent_headers,
        json={
            "event_type": "schedule_item_completed",
            "payload": {"schedule_item_id": item["id"], "planned_date": DATE},
        },
    )
    done_id = done.json()["id"]

    # correcting into a skip is done by retracting and re-logging; here we
    # correct the same completion's payload (e.g. fixed occurred_at)
    corrected = await client.post(
        f"/v1/events/{done_id}/correct",
        headers=parent_headers,
        json={
            "payload": {"schedule_item_id": item["id"], "planned_date": DATE},
            "occurred_at": "2026-08-24T13:00:00Z",
        },
    )
    assert corrected.status_code == 201
    assert corrected.json()["corrects_event_id"] == done_id

    got = await client.get(
        f"/v1/children/{child.id}/schedule", params={"date": DATE}, headers=parent_headers
    )
    status = got.json()["schedule"]["items"][0]["item_status"]
    assert status["status"] == "done"
    assert status["event_id"] == corrected.json()["id"]

    # undo: retract the correction chain head → item back to pending
    retract = await client.post(
        f"/v1/events/{corrected.json()['id']}/correct",
        headers=parent_headers,
        json={"retracted": True},
    )
    assert retract.status_code == 201

    got = await client.get(
        f"/v1/children/{child.id}/schedule", params={"date": DATE}, headers=parent_headers
    )
    assert got.json()["schedule"]["items"][0]["item_status"] is None


async def test_correct_missing_event_404(client, parent_headers):
    response = await client.post(
        "/v1/events/nope/correct", headers=parent_headers, json={"retracted": True}
    )
    assert response.status_code == 404


async def test_correct_requires_payload_or_retraction(client, parent_headers, child):
    note = await append_note(client, parent_headers, child.id)
    response = await client.post(
        f"/v1/events/{note['id']}/correct", headers=parent_headers, json={}
    )
    assert response.status_code == 422
