async def test_parent_creates_child(client, parent_headers):
    response = await client.post(
        "/v1/children",
        headers=parent_headers,
        json={"display_name": "Test Child A", "timezone": "America/New_York"},
    )
    assert response.status_code == 201
    assert response.json()["timezone"] == "America/New_York"


async def test_invalid_timezone_rejected(client, parent_headers):
    response = await client.post(
        "/v1/children",
        headers=parent_headers,
        json={"display_name": "Test Child A", "timezone": "Mars/Olympus_Mons"},
    )
    assert response.status_code == 422


async def test_caregiver_can_list_but_not_create(caregiver_client, caregiver_headers, child):
    listed = await caregiver_client.get("/v1/children", headers=caregiver_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    response = await caregiver_client.post(
        "/v1/children",
        headers=caregiver_headers,
        json={"display_name": "Test Child B", "timezone": "UTC"},
    )
    assert response.status_code == 403


async def test_update_child(client, parent_headers, child):
    response = await client.patch(
        f"/v1/children/{child.id}",
        headers=parent_headers,
        json={"birth_date": "2020-05-04", "timezone": "America/Chicago"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["birth_date"] == "2020-05-04"
    assert body["timezone"] == "America/Chicago"


async def test_update_missing_child_404(client, parent_headers):
    response = await client.patch(
        "/v1/children/does-not-exist", headers=parent_headers, json={"display_name": "X"}
    )
    assert response.status_code == 404
