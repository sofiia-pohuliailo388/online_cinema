"""Admin management of users (spec, section 1): list, change group, manual activation."""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.enums import UserGroupEnum
from src.accounts.models import ActivationToken

URL = "/api/v1/admin/users"


@pytest.mark.parametrize("group", [UserGroupEnum.USER, UserGroupEnum.MODERATOR])
async def test_not_admin_is_forbidden(
    client: AsyncClient, login_as: Any, group: UserGroupEnum
) -> None:
    login_as(group)

    response = await client.get(URL)

    assert response.status_code == 403


async def test_unauthenticated(client: AsyncClient) -> None:
    response = await client.get(URL)

    assert response.status_code == 401


async def test_list_users_with_filters(
    client: AsyncClient, login_as: Any, create_user: Any
) -> None:
    await create_user(email="active@test.com")
    await create_user(email="inactive@test.com", is_active=False)
    await create_user(UserGroupEnum.MODERATOR, email="mod@test.com")
    login_as(UserGroupEnum.ADMIN, user_id=999)

    all_users = (await client.get(URL)).json()
    inactive = (await client.get(URL, params={"is_active": False})).json()
    moderators = (await client.get(URL, params={"group": "MODERATOR"})).json()
    by_email = (await client.get(URL, params={"email": "mod@"})).json()

    assert all_users["total"] == 3
    assert [u["email"] for u in inactive["items"]] == ["inactive@test.com"]
    assert [u["email"] for u in moderators["items"]] == ["mod@test.com"]
    assert [u["email"] for u in by_email["items"]] == ["mod@test.com"]


async def test_get_user_not_found(client: AsyncClient, login_as: Any) -> None:
    login_as(UserGroupEnum.ADMIN)

    response = await client.get(f"{URL}/999")

    assert response.status_code == 404


async def test_change_group(client: AsyncClient, login_as: Any, create_user: Any) -> None:
    user = await create_user()
    login_as(UserGroupEnum.ADMIN, user_id=999)

    response = await client.patch(f"{URL}/{user.id}/group", json={"group": "MODERATOR"})

    assert response.status_code == 200
    assert response.json()["group"] == "MODERATOR"


async def test_admin_cannot_change_own_group(
    client: AsyncClient, login_as: Any, create_user: Any
) -> None:
    admin = await create_user(UserGroupEnum.ADMIN, email="admin@test.com")
    login_as(UserGroupEnum.ADMIN, user_id=admin.id)

    response = await client.patch(f"{URL}/{admin.id}/group", json={"group": "USER"})

    assert response.status_code == 409


async def test_change_group_user_not_found(client: AsyncClient, login_as: Any) -> None:
    login_as(UserGroupEnum.ADMIN)

    response = await client.patch(f"{URL}/999/group", json={"group": "USER"})

    assert response.status_code == 404


async def test_change_group_invalid_group(
    client: AsyncClient, login_as: Any, create_user: Any
) -> None:
    user = await create_user()
    login_as(UserGroupEnum.ADMIN, user_id=999)

    response = await client.patch(f"{URL}/{user.id}/group", json={"group": "SUPERUSER"})

    assert response.status_code == 422


async def test_activate_user_manually(
    client: AsyncClient, login_as: Any, create_user: Any, db_session: AsyncSession
) -> None:
    user = await create_user(is_active=False)
    db_session.add(
        ActivationToken(
            user_id=user.id,
            token="activation-token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
    )
    await db_session.commit()
    login_as(UserGroupEnum.ADMIN, user_id=999)

    response = await client.post(f"{URL}/{user.id}/activate")

    assert response.status_code == 200
    assert response.json()["is_active"] is True
    assert await db_session.scalar(select(ActivationToken)) is None


async def test_activate_user_not_found(client: AsyncClient, login_as: Any) -> None:
    login_as(UserGroupEnum.ADMIN)

    response = await client.post(f"{URL}/999/activate")

    assert response.status_code == 404
