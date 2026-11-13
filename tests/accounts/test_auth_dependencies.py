"""Tests for ``get_user_by_id``, ``get_current_user`` and ``require_roles``."""

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from fastapi import FastAPI
from fastapi.security import HTTPAuthorizationCredentials
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.dependencies import CurrentUser, get_current_user, require_roles
from src.accounts.enums import UserGroupEnum
from src.accounts.security import create_access_token
from src.accounts.service import get_user_by_id
from src.core.config import settings
from src.core.database import get_db
from src.core.exceptions import (
    PermissionDeniedError,
    UnauthorizedError,
    register_exception_handlers,
)
from tests.accounts.conftest import CreateUser


def bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.fixture
async def auth_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Client of a tiny app with one endpoint protected by ``CurrentUser``."""
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/me")
    async def me(user: CurrentUser) -> dict[str, Any]:
        return {"id": user.id, "group": user.group.name.value}

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        yield ac


# --- get_user_by_id ---


async def test_get_user_by_id_returns_user_with_group_loaded(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user(UserGroupEnum.MODERATOR)

    user = await get_user_by_id(db_session, created.id)

    assert user is not None
    assert user.email == "user@test.com"
    assert user.group.name == UserGroupEnum.MODERATOR


async def test_get_user_by_id_returns_none_for_unknown_id(db_session: AsyncSession) -> None:
    assert await get_user_by_id(db_session, 999) is None


# --- get_current_user ---


async def test_get_current_user_returns_user_for_valid_token(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user()
    token = create_access_token(created.id, UserGroupEnum.USER)

    user = await get_current_user(db_session, bearer(token))

    assert user.id == created.id
    assert user.group.name == UserGroupEnum.USER


async def test_get_current_user_rejects_missing_credentials(db_session: AsyncSession) -> None:
    with pytest.raises(UnauthorizedError, match="Not authenticated"):
        await get_current_user(db_session, None)


async def test_get_current_user_rejects_garbage_token(db_session: AsyncSession) -> None:
    with pytest.raises(UnauthorizedError, match="Invalid or expired token"):
        await get_current_user(db_session, bearer("not-a-jwt"))


async def test_get_current_user_rejects_token_without_user_id(db_session: AsyncSession) -> None:
    payload = {"group": "USER", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    with pytest.raises(UnauthorizedError, match="Invalid token payload"):
        await get_current_user(db_session, bearer(token))


async def test_get_current_user_rejects_unknown_user(db_session: AsyncSession) -> None:
    token = create_access_token(999, UserGroupEnum.USER)

    with pytest.raises(UnauthorizedError, match="not found or inactive"):
        await get_current_user(db_session, bearer(token))


async def test_get_current_user_rejects_inactive_user(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user(is_active=False)
    token = create_access_token(created.id, UserGroupEnum.USER)

    with pytest.raises(UnauthorizedError, match="not found or inactive"):
        await get_current_user(db_session, bearer(token))


# --- require_roles ---


@pytest.mark.parametrize(
    ("group", "allowed"),
    [
        (UserGroupEnum.USER, False),
        (UserGroupEnum.MODERATOR, True),
        (UserGroupEnum.ADMIN, True),
    ],
    ids=["user_denied", "moderator_allowed", "admin_inherits_permissions"],
)
async def test_require_roles_moderator(group: UserGroupEnum, allowed: bool) -> None:
    checker = require_roles(UserGroupEnum.MODERATOR)
    user = SimpleNamespace(group=SimpleNamespace(name=group))

    if allowed:
        assert await checker(user) is user
    else:
        with pytest.raises(PermissionDeniedError):
            await checker(user)


# --- the whole chain through HTTP ---


async def test_protected_endpoint_returns_current_user(
    auth_client: AsyncClient, create_user: CreateUser
) -> None:
    created = await create_user(UserGroupEnum.MODERATOR)
    token = create_access_token(created.id, UserGroupEnum.MODERATOR)

    response = await auth_client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"id": created.id, "group": "MODERATOR"}


async def test_protected_endpoint_without_header_returns_401(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


async def test_protected_endpoint_with_invalid_token_returns_401(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/me", headers={"Authorization": "Bearer garbage"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
