async def make_preference(client, headers, child_id: str, **overrides) -> dict:
    body = {
        "kind": "sensory_seeking",
        "category": "texture",
        "label": "Crunchy textures",
        **overrides,
    }
    response = await client.post(f"/v1/children/{child_id}/preferences", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def log_evidence(client, headers, child_id: str, preference_id: str, direction: int) -> dict:
    response = await client.post(
        f"/v1/children/{child_id}/events",
        headers=headers,
        json={
            "event_type": "preference_evidence",
            "payload": {"preference_id": preference_id, "direction": direction},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_create_and_list_preferences(client, parent_headers, child):
    await make_preference(client, parent_headers, child.id)
    await make_preference(
        client, parent_headers, child.id, kind="dislike", category="sound", label="Hand dryers"
    )

    listed = await client.get(f"/v1/children/{child.id}/preferences", headers=parent_headers)
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 2
    assert all(p["confidence"] is None for p in body)  # no evidence yet


async def test_invalid_kind_rejected(client, parent_headers, child):
    response = await client.post(
        f"/v1/children/{child.id}/preferences",
        headers=parent_headers,
        json={"kind": "loves", "category": "food", "label": "X"},
    )
    assert response.status_code == 422


async def test_evidence_builds_confidence(client, parent_headers, child):
    preference = await make_preference(client, parent_headers, child.id)
    for _ in range(3):
        await log_evidence(client, parent_headers, child.id, preference["id"], 1)

    listed = await client.get(f"/v1/children/{child.id}/preferences", headers=parent_headers)
    confidence = listed.json()[0]["confidence"]
    assert confidence is not None
    assert confidence["evidence_count"] == 3
    assert confidence["score"] > 2.9  # fresh evidence, negligible decay
    assert confidence["label"] == "moderate"
    assert confidence["last_observed"] is not None


async def test_contradicting_evidence_reads_mixed(client, parent_headers, child):
    preference = await make_preference(client, parent_headers, child.id)
    for direction in (1, 1, -1, -1):
        await log_evidence(client, parent_headers, child.id, preference["id"], direction)

    listed = await client.get(f"/v1/children/{child.id}/preferences", headers=parent_headers)
    assert listed.json()[0]["confidence"]["label"] == "mixed"


async def test_retracted_evidence_drops_out(client, parent_headers, child):
    preference = await make_preference(client, parent_headers, child.id)
    event = await log_evidence(client, parent_headers, child.id, preference["id"], 1)
    await client.post(
        f"/v1/events/{event['id']}/correct", headers=parent_headers, json={"retracted": True}
    )

    listed = await client.get(f"/v1/children/{child.id}/preferences", headers=parent_headers)
    assert listed.json()[0]["confidence"] is None


async def test_strongest_signal_sorts_first(client, parent_headers, child):
    weak = await make_preference(client, parent_headers, child.id, label="Weak signal")
    strong = await make_preference(client, parent_headers, child.id, label="Strong signal")
    await log_evidence(client, parent_headers, child.id, weak["id"], 1)
    for _ in range(4):
        await log_evidence(client, parent_headers, child.id, strong["id"], 1)

    listed = await client.get(f"/v1/children/{child.id}/preferences", headers=parent_headers)
    assert [p["label"] for p in listed.json()] == ["Strong signal", "Weak signal"]


async def test_update_preference_and_clear_context(client, parent_headers, child):
    preference = await make_preference(client, parent_headers, child.id, context="At mealtimes")
    updated = await client.patch(
        f"/v1/preferences/{preference['id']}",
        headers=parent_headers,
        json={"label": "Very crunchy textures", "context": None},
    )
    assert updated.status_code == 200
    assert updated.json()["label"] == "Very crunchy textures"
    assert updated.json()["context"] is None


async def test_caregiver_reads_but_cannot_write(
    client, parent_headers, caregiver_client, caregiver_headers, child
):
    await make_preference(client, parent_headers, child.id)
    listed = await caregiver_client.get(
        f"/v1/children/{child.id}/preferences", headers=caregiver_headers
    )
    assert listed.status_code == 200

    response = await caregiver_client.post(
        f"/v1/children/{child.id}/preferences",
        headers=caregiver_headers,
        json={"kind": "like", "category": "food", "label": "Nope"},
    )
    assert response.status_code == 403
