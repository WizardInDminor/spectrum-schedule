from tests.conftest import PARENT_EMAIL, login


async def test_parent_creates_and_lists_users(client, parent_headers):
    created = await client.post(
        "/v1/users",
        headers=parent_headers,
        json={
            "email": "second@example.com",
            "password": "another-pass-1",
            "display_name": "Second Parent",
            "role": "parent",
        },
    )
    assert created.status_code == 201

    listed = await client.get("/v1/users", headers=parent_headers)
    assert listed.status_code == 200
    assert {u["email"] for u in listed.json()} == {PARENT_EMAIL, "second@example.com"}


async def test_duplicate_email_conflict(client, parent_headers):
    body = {
        "email": PARENT_EMAIL,
        "password": "another-pass-1",
        "display_name": "Duplicate",
        "role": "caregiver",
    }
    response = await client.post("/v1/users", headers=parent_headers, json=body)
    assert response.status_code == 409


async def test_caregiver_cannot_manage_users(caregiver_client, caregiver_headers):
    assert (await caregiver_client.get("/v1/users", headers=caregiver_headers)).status_code == 403
    response = await caregiver_client.post(
        "/v1/users",
        headers=caregiver_headers,
        json={
            "email": "x@example.com",
            "password": "whatever-pass",
            "display_name": "X",
            "role": "caregiver",
        },
    )
    assert response.status_code == 403


async def test_deactivated_user_cannot_log_in(client, parent_headers, caregiver):
    response = await client.patch(
        f"/v1/users/{caregiver.id}", headers=parent_headers, json={"is_active": False}
    )
    assert response.status_code == 200
    login_attempt = await client.post(
        "/v1/auth/login", json={"email": caregiver.email, "password": "correct-horse-9"}
    )
    assert login_attempt.status_code == 401


async def test_cannot_deactivate_self(client, parent, parent_headers):
    response = await client.patch(
        f"/v1/users/{parent.id}", headers=parent_headers, json={"is_active": False}
    )
    assert response.status_code == 400


async def test_password_change_takes_effect(client, parent_headers, caregiver):
    await client.patch(
        f"/v1/users/{caregiver.id}", headers=parent_headers, json={"password": "new-pass-word-1"}
    )
    assert (
        await client.post(
            "/v1/auth/login", json={"email": caregiver.email, "password": "new-pass-word-1"}
        )
    ).status_code == 200


async def test_second_parent_can_log_in(client, parent_headers):
    await client.post(
        "/v1/users",
        headers=parent_headers,
        json={
            "email": "second@example.com",
            "password": "another-pass-1",
            "display_name": "Second Parent",
            "role": "parent",
        },
    )
    headers = await login(client, "second@example.com", "another-pass-1")
    assert (await client.get("/v1/users", headers=headers)).status_code == 200
