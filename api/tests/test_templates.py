async def make_template(client, headers, child_id: str, name: str = "School Morning") -> dict:
    response = await client.post(
        f"/v1/children/{child_id}/templates", headers=headers, json={"name": name}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def add_step(client, headers, template_id: str, title: str, **extra) -> dict:
    response = await client.post(
        f"/v1/templates/{template_id}/steps", headers=headers, json={"title": title, **extra}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_template_with_ordered_steps(client, parent_headers, child):
    template = await make_template(client, parent_headers, child.id)
    await add_step(client, parent_headers, template["id"], "Wake up", icon="☀️")
    await add_step(
        client,
        parent_headers,
        template["id"],
        "Breakfast",
        duration_minutes=20,
        transition_warning_minutes=5,
    )
    body = await add_step(client, parent_headers, template["id"], "Brush teeth")

    assert [s["title"] for s in body["steps"]] == ["Wake up", "Breakfast", "Brush teeth"]
    assert [s["position"] for s in body["steps"]] == [0, 1, 2]


async def test_step_reorder_and_delete(client, parent_headers, child):
    template = await make_template(client, parent_headers, child.id)
    await add_step(client, parent_headers, template["id"], "A")
    await add_step(client, parent_headers, template["id"], "B")
    body = await add_step(client, parent_headers, template["id"], "C")
    step_c = body["steps"][2]

    moved = await client.patch(
        f"/v1/steps/{step_c['id']}", headers=parent_headers, json={"position": 0}
    )
    assert [s["title"] for s in moved.json()["steps"]] == ["C", "A", "B"]

    deleted = await client.delete(f"/v1/steps/{step_c['id']}", headers=parent_headers)
    assert [s["title"] for s in deleted.json()["steps"]] == ["A", "B"]
    assert [s["position"] for s in deleted.json()["steps"]] == [0, 1]


async def test_caregiver_reads_templates_but_cannot_write(
    client, parent_headers, caregiver_client, caregiver_headers, child
):
    template = await make_template(client, parent_headers, child.id)

    listed = await caregiver_client.get(
        f"/v1/children/{child.id}/templates", headers=caregiver_headers
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    response = await caregiver_client.post(
        f"/v1/children/{child.id}/templates", headers=caregiver_headers, json={"name": "Nope"}
    )
    assert response.status_code == 403
    response = await caregiver_client.patch(
        f"/v1/templates/{template['id']}", headers=caregiver_headers, json={"name": "Nope"}
    )
    assert response.status_code == 403


async def test_weekday_defaults_roundtrip(client, parent_headers, child):
    template = await make_template(client, parent_headers, child.id)
    put = await client.put(
        f"/v1/children/{child.id}/weekday-defaults",
        headers=parent_headers,
        json={"defaults": {"0": template["id"], "5": template["id"]}},
    )
    assert put.status_code == 200
    got = await client.get(f"/v1/children/{child.id}/weekday-defaults", headers=parent_headers)
    defaults = got.json()["defaults"]
    assert defaults["0"] == template["id"]
    assert defaults["5"] == template["id"]
    assert defaults["2"] is None

    cleared = await client.put(
        f"/v1/children/{child.id}/weekday-defaults",
        headers=parent_headers,
        json={"defaults": {"5": None}},
    )
    assert cleared.json()["defaults"]["5"] is None
    assert cleared.json()["defaults"]["0"] == template["id"]


async def test_weekday_defaults_reject_foreign_template(client, parent_headers, child):
    response = await client.put(
        f"/v1/children/{child.id}/weekday-defaults",
        headers=parent_headers,
        json={"defaults": {"0": "not-a-template"}},
    )
    assert response.status_code == 422


async def test_step_edit_in_place_and_clear_fields(client, parent_headers, child):
    template = await make_template(client, parent_headers, child.id)
    body = await add_step(
        client,
        parent_headers,
        template["id"],
        "Breakfast",
        icon="🥣",
        duration_minutes=20,
        transition_warning_minutes=5,
    )
    step = body["steps"][0]

    edited = await client.patch(
        f"/v1/steps/{step['id']}",
        headers=parent_headers,
        json={"title": "Big breakfast", "duration_minutes": 30},
    )
    updated = edited.json()["steps"][0]
    assert updated["title"] == "Big breakfast"
    assert updated["duration_minutes"] == 30
    assert updated["transition_warning_minutes"] == 5  # omitted → untouched

    cleared = await client.patch(
        f"/v1/steps/{step['id']}",
        headers=parent_headers,
        json={"duration_minutes": None, "transition_warning_minutes": None, "icon": None},
    )
    updated = cleared.json()["steps"][0]
    assert updated["duration_minutes"] is None  # explicit null → cleared
    assert updated["transition_warning_minutes"] is None
    assert updated["icon"] is None
    assert updated["title"] == "Big breakfast"
