"""Fixtures for the accounts tests."""

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.enums import UserGroupEnum
from src.accounts.models import User, UserGroup

CreateUser = Callable[..., Awaitable[User]]


@pytest.fixture
def create_user(db_session: AsyncSession) -> CreateUser:
    """Factory that inserts a user (and its group, if missing) into the test DB."""

    async def _create(
        group: UserGroupEnum = UserGroupEnum.USER,
        *,
        email: str = "user@test.com",
        is_active: bool = True,
    ) -> User:
        result = await db_session.execute(select(UserGroup).where(UserGroup.name == group))
        user_group = result.scalar_one_or_none()
        if user_group is None:
            user_group = UserGroup(name=group)
            db_session.add(user_group)
            await db_session.flush()
        user = User(
            email=email,
            hashed_password="not-a-real-hash",
            is_active=is_active,
            group_id=user_group.id,
        )
        db_session.add(user)
        await db_session.commit()
        # Detach everything, so the code under test has to load ``user.group`` itself.
        db_session.expunge_all()
        return user

    return _create


@pytest.fixture
async def user_group(db_session: AsyncSession) -> UserGroup:
    """The default ``USER`` group, as created by the ``seed user groups`` migration."""
    group = UserGroup(name=UserGroupEnum.USER)
    db_session.add(group)
    await db_session.commit()
    return group


@pytest.fixture
def sent_emails(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Replace ``send_email`` used by the service and collect everything it was asked to send."""
    sent: list[dict[str, Any]] = []

    def fake_send_email(**kwargs: Any) -> None:
        sent.append(kwargs)

    monkeypatch.setattr("src.accounts.service.send_email", fake_send_email)
    return sent
