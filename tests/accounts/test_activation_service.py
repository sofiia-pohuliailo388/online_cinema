"""Tests for ``activate_user``."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import ActivationToken, User
from src.accounts.service import activate_user
from src.core.exceptions import BadRequestError
from tests.accounts.conftest import CreateUser


async def add_token(
    db_session: AsyncSession, user_id: int, *, token: str = "valid-token", hours: int = 24
) -> None:
    """Store an activation token that expires in ``hours`` hours (negative = already expired)."""
    db_session.add(
        ActivationToken(
            user_id=user_id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=hours),
        )
    )
    await db_session.commit()
    # Detach everything: the service must load the token from the DB like in production.
    db_session.expunge_all()


async def test_activate_user_activates_account_and_deletes_token(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user(is_active=False)
    await add_token(db_session, created.id)

    user = await activate_user(db_session, "valid-token")

    assert user.is_active is True
    db_session.expunge_all()
    stored = await db_session.scalar(select(User).where(User.id == created.id))
    assert stored is not None and stored.is_active is True
    assert await db_session.scalar(select(ActivationToken)) is None


async def test_activate_user_rejects_unknown_token(db_session: AsyncSession) -> None:
    with pytest.raises(BadRequestError, match="Invalid activation token"):
        await activate_user(db_session, "no-such-token")


async def test_activate_user_rejects_expired_token(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user(is_active=False)
    await add_token(db_session, created.id, hours=-1)

    with pytest.raises(BadRequestError, match="expired"):
        await activate_user(db_session, "valid-token")

    stored = await db_session.scalar(select(User).where(User.id == created.id))
    assert stored is not None and stored.is_active is False


async def test_activation_token_cannot_be_used_twice(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user(is_active=False)
    await add_token(db_session, created.id)
    await activate_user(db_session, "valid-token")

    with pytest.raises(BadRequestError, match="Invalid activation token"):
        await activate_user(db_session, "valid-token")
