"""Shared test fixtures (owner: P1).

* Tests run against in-memory SQLite: no Docker or Postgres needed.
* ``client``   - async HTTP client bound to the app with a fresh empty DB per test.
* ``db_session`` - the same session, for preparing data directly.
* ``login_as`` - pretend a user of a given group is logged in (no real JWT needed)::

      async def test_x(client, login_as):
          login_as(UserGroupEnum.MODERATOR)
          response = await client.post(...)
"""
from collections.abc import AsyncGenerator, Callable
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import src.models  # noqa: F401  (registers all tables in Base.metadata)
from src.accounts.dependencies import get_current_user
from src.accounts.enums import UserGroupEnum
from src.core.database import get_db
from src.core.models import Base
from src.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        TEST_DATABASE_URL, poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def make_fake_user(group: UserGroupEnum, user_id: int = 1) -> Any:
    """Object with the same attributes routers use from a real ``User``."""
    return SimpleNamespace(
        id=user_id,
        email=f"{group.value.lower()}{user_id}@test.com",
        is_active=True,
        group=SimpleNamespace(name=group),
    )


@pytest.fixture
def login_as() -> Callable[..., Any]:
    def _login(group: UserGroupEnum = UserGroupEnum.USER, user_id: int = 1) -> Any:
        user = make_fake_user(group, user_id)
        app.dependency_overrides[get_current_user] = lambda: user
        return user

    return _login
