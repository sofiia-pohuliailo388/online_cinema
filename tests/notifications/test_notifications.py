"""In-app notifications of the current user (spec, section 2)."""

from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.enums import UserGroupEnum
from src.accounts.models import User, UserGroup
from src.notifications.models import Notification

URL = "/api/v1/notifications"


async def _setup(db: AsyncSession) -> tuple[User, User, list[Notification]]:
    group = UserGroup(name=UserGroupEnum.USER)
    db.add(group)
    await db.flush()
    me = User(email="me@test.com", hashed_password="hash", is_active=True, group_id=group.id)
    other = User(
        email="other@test.com", hashed_password="hash", is_active=True, group_id=group.id
    )
    db.add_all([me, other])
    await db.flush()
    notifications = [
        Notification(user_id=me.id, text="Old reply", is_read=True),
        Notification(user_id=me.id, text="New like", is_read=False),
        Notification(user_id=me.id, text="New reply", is_read=False),
        Notification(user_id=other.id, text="Not mine", is_read=False),
    ]
    for notification in notifications:  # one by one: ids grow in this order
        db.add(notification)
        await db.flush()
    await db.commit()
    return me, other, notifications


async def test_list_only_my_notifications_newest_first(
    client: AsyncClient, login_as: Any, db_session: AsyncSession
) -> None:
    me, _, _ = await _setup(db_session)
    login_as(user_id=me.id)

    response = await client.get(URL)

    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 3
    assert [n["text"] for n in body["items"]] == ["New reply", "New like", "Old reply"]


async def test_list_unread_only(
    client: AsyncClient, login_as: Any, db_session: AsyncSession
) -> None:
    me, _, _ = await _setup(db_session)
    login_as(user_id=me.id)

    response = await client.get(URL, params={"unread_only": True})

    assert [n["text"] for n in response.json()["items"]] == ["New reply", "New like"]


async def test_unread_count(client: AsyncClient, login_as: Any, db_session: AsyncSession) -> None:
    me, _, _ = await _setup(db_session)
    login_as(user_id=me.id)

    response = await client.get(f"{URL}/unread-count")

    assert response.json() == {"unread": 2}


async def test_mark_as_read(client: AsyncClient, login_as: Any, db_session: AsyncSession) -> None:
    me, _, notifications = await _setup(db_session)
    login_as(user_id=me.id)

    response = await client.patch(f"{URL}/{notifications[1].id}/read")

    assert response.status_code == 200
    assert response.json()["is_read"] is True
    assert (await client.get(f"{URL}/unread-count")).json() == {"unread": 1}


async def test_cannot_mark_someone_elses_notification(
    client: AsyncClient, login_as: Any, db_session: AsyncSession
) -> None:
    me, _, notifications = await _setup(db_session)
    login_as(user_id=me.id)

    response = await client.patch(f"{URL}/{notifications[3].id}/read")

    assert response.status_code == 404


async def test_mark_all_as_read(
    client: AsyncClient, login_as: Any, db_session: AsyncSession
) -> None:
    me, other, _ = await _setup(db_session)
    login_as(user_id=me.id)

    response = await client.post(f"{URL}/read-all")

    assert response.json() == {"updated": 2}
    assert (await client.get(f"{URL}/unread-count")).json() == {"unread": 0}
    login_as(user_id=other.id)
    assert (await client.get(f"{URL}/unread-count")).json() == {"unread": 1}


async def test_unauthenticated(client: AsyncClient) -> None:
    response = await client.get(URL)

    assert response.status_code == 401
