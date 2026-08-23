from tests.conftest import PARENT_EMAIL, PASSWORD, login


async def test_login_sets_session_and_returns_user(client, parent):
    response = await client.post(
        "/v1/auth/login", json={"email": PARENT_EMAIL, "password": PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["email"] == PARENT_EMAIL
    assert "session" in client.cookies
    assert "csrf" in client.cookies


async def test_login_wrong_password(client, parent):
    response = await client.post(
        "/v1/auth/login", json={"email": PARENT_EMAIL, "password": "wrong-password"}
    )
    assert response.status_code == 401


async def test_login_unknown_email(client):
    response = await client.post(
        "/v1/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )
    assert response.status_code == 401


async def test_me_requires_auth(client):
    assert (await client.get("/v1/auth/me")).status_code == 401


async def test_me_after_login(client, parent):
    await login(client, PARENT_EMAIL)
    response = await client.get("/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["role"] == "parent"


async def test_logout_invalidates_session(client, parent):
    headers = await login(client, PARENT_EMAIL)
    assert (await client.post("/v1/auth/logout", headers=headers)).status_code == 204
    assert (await client.get("/v1/auth/me")).status_code == 401


async def test_mutation_without_csrf_header_rejected(client, parent_headers):
    response = await client.post(
        "/v1/children", json={"display_name": "Test Child B", "timezone": "UTC"}
    )
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]
