from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Declarative base; all models must be Postgres-compatible (no SQLite-only
    types, UUID PKs as String(36), timezone-aware UTC datetimes)."""


engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, expire_on_commit=False)
