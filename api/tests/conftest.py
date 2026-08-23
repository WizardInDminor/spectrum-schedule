from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import models
from app.db import Base
from app.deps import get_db
from app.main import app
from app.security import hash_password

PARENT_EMAIL = "parent@example.com"
CAREGIVER_EMAIL = "caregiver@example.com"
PASSWORD = "correct-horse-9"


@pytest.fixture
async def db_sessionmaker():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


@pytest.fixture(autouse=True)
def _override_db(db_sessionmaker):
    async def override() -> AsyncIterator:
        async with db_sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture
async def caregiver_client() -> AsyncIterator[AsyncClient]:
    """Separate cookie jar so a caregiver session can coexist with the
    parent session on `client` within one test."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


async def create_user(
    db_sessionmaker, email: str, role: str, password: str = PASSWORD
) -> models.User:
    async with db_sessionmaker() as db:
        user = models.User(
            email=email,
            password_hash=hash_password(password),
            display_name="Test User",
            role=role,
        )
        db.add(user)
        await db.commit()
        return user


async def login(client: AsyncClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    """Log in and return the CSRF header mutating requests must carry."""
    response = await client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": client.cookies["csrf"]}


@pytest.fixture
async def parent(db_sessionmaker) -> models.User:
    return await create_user(db_sessionmaker, PARENT_EMAIL, "parent")


@pytest.fixture
async def caregiver(db_sessionmaker) -> models.User:
    return await create_user(db_sessionmaker, CAREGIVER_EMAIL, "caregiver")


@pytest.fixture
async def parent_headers(client, parent) -> dict[str, str]:
    return await login(client, PARENT_EMAIL)


@pytest.fixture
async def caregiver_headers(caregiver_client, caregiver) -> dict[str, str]:
    return await login(caregiver_client, CAREGIVER_EMAIL)


@pytest.fixture
async def child(db_sessionmaker) -> models.Child:
    async with db_sessionmaker() as db:
        row = models.Child(display_name="Test Child A", timezone="America/New_York")
        db.add(row)
        await db.commit()
        return row
