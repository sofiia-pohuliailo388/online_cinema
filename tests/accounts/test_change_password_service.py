"""Tests for ``change_password``."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import User
from src.accounts.security import verify_password
from src.accounts.service import change_password
from src.core.exceptions import BadRequestError, UnauthorizedError
from tests.accounts.conftest import CreateUser

OLD_PASSWORD = "0ld!Str0ngPass"
NEW_PASSWORD = "N3w!Str0ngPass"


async def stored_hash(db_session: AsyncSession, user_id: int) -> str:
    """Read the password hash from the DB as a fresh query (not from the session cache)."""
    db_session.expunge_all()
    user = await db_session.scalar(select(User).where(User.id == user_id))
    assert user is not None
    return user.hashed_password


async def test_change_password_saves_new_hash(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user(password=OLD_PASSWORD)

    await change_password(db_session, created.id, OLD_PASSWORD, NEW_PASSWORD)

    hashed = await stored_hash(db_session, created.id)
    assert verify_password(NEW_PASSWORD, hashed)
    assert not verify_password(OLD_PASSWORD, hashed)


async def test_change_password_rejects_wrong_old_password(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user(password=OLD_PASSWORD)

    with pytest.raises(BadRequestError, match="Old password is incorrect"):
        await change_password(db_session, created.id, "Wr0ng!Pass", NEW_PASSWORD)

    assert verify_password(OLD_PASSWORD, await stored_hash(db_session, created.id))


async def test_change_password_rejects_unknown_user(db_session: AsyncSession) -> None:
    with pytest.raises(UnauthorizedError, match="User not found"):
        await change_password(db_session, 999, OLD_PASSWORD, NEW_PASSWORD)
