"""Tests for ``get_user_by_email``, ``forgot_password`` and ``reset_password``."""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.enums import UserGroupEnum
from src.accounts.models import PasswordResetToken, RefreshToken, User
from src.accounts.security import verify_password
from src.accounts.service import (
    PASSWORD_RESET_TOKEN_TTL,
    build_password_reset_link,
    forgot_password,
    get_user_by_email,
    reset_password,
)
from src.core.exceptions import BadRequestError
from tests.accounts.conftest import CreateUser

OLD_PASSWORD = "0ld!Str0ngPass"
NEW_PASSWORD = "N3w!Str0ngPass"


async def add_reset_token(
    db_session: AsyncSession, user_id: int, *, token: str = "reset-token", hours: int = 1
) -> None:
    """Store a reset token that expires in ``hours`` hours (negative = already expired)."""
    db_session.add(
        PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=hours),
        )
    )
    await db_session.commit()
    db_session.expunge_all()


async def add_refresh_token(db_session: AsyncSession, user_id: int, token: str) -> None:
    db_session.add(
        RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
    )
    await db_session.commit()
    db_session.expunge_all()


async def stored_user(db_session: AsyncSession, user_id: int) -> User:
    """Read the user from the DB as a fresh query (not from the session cache)."""
    db_session.expunge_all()
    user = await db_session.scalar(select(User).where(User.id == user_id))
    assert user is not None
    return user


# --- get_user_by_email ---


async def test_get_user_by_email_returns_user_with_group_loaded(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    await create_user(UserGroupEnum.MODERATOR)

    user = await get_user_by_email(db_session, "user@test.com")

    assert user is not None
    assert user.group.name == UserGroupEnum.MODERATOR


async def test_get_user_by_email_returns_none_for_unknown_email(
    db_session: AsyncSession,
) -> None:
    assert await get_user_by_email(db_session, "nobody@test.com") is None


# --- forgot_password ---


async def test_forgot_password_creates_token_and_sends_link(
    db_session: AsyncSession, create_user: CreateUser, sent_emails: list[dict[str, Any]]
) -> None:
    created = await create_user()

    await forgot_password(db_session, "user@test.com")

    token = await db_session.scalar(select(PasswordResetToken))
    assert token is not None
    assert token.user_id == created.id
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "user@test.com"
    assert sent_emails[0]["template"] == "password_reset.html"
    assert sent_emails[0]["context"] == {"link": build_password_reset_link(token.token)}


async def test_forgot_password_token_lives_for_the_configured_time_in_utc(
    db_session: AsyncSession, create_user: CreateUser, sent_emails: list[dict[str, Any]]
) -> None:
    await create_user()

    await forgot_password(db_session, "user@test.com")

    token = await db_session.scalar(select(PasswordResetToken))
    assert token is not None
    expected = datetime.now(timezone.utc) + PASSWORD_RESET_TOKEN_TTL
    actual = token.expires_at.replace(tzinfo=None)
    assert abs((actual - expected.replace(tzinfo=None)).total_seconds()) < 5


async def test_forgot_password_replaces_old_token(
    db_session: AsyncSession, create_user: CreateUser, sent_emails: list[dict[str, Any]]
) -> None:
    created = await create_user()
    await add_reset_token(db_session, created.id, token="old-token")

    await forgot_password(db_session, "user@test.com")

    tokens = (await db_session.scalars(select(PasswordResetToken.token))).all()
    assert len(tokens) == 1
    assert tokens[0] != "old-token"


async def test_forgot_password_does_nothing_for_unknown_email(
    db_session: AsyncSession, sent_emails: list[dict[str, Any]]
) -> None:
    await forgot_password(db_session, "nobody@test.com")

    assert await db_session.scalar(select(PasswordResetToken)) is None
    assert sent_emails == []


async def test_forgot_password_does_nothing_for_inactive_account(
    db_session: AsyncSession, create_user: CreateUser, sent_emails: list[dict[str, Any]]
) -> None:
    await create_user(is_active=False)

    await forgot_password(db_session, "user@test.com")

    assert await db_session.scalar(select(PasswordResetToken)) is None
    assert sent_emails == []


# --- reset_password ---


async def test_reset_password_changes_password_and_deletes_token(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user(password=OLD_PASSWORD)
    await add_reset_token(db_session, created.id)

    await reset_password(db_session, "reset-token", NEW_PASSWORD)

    user = await stored_user(db_session, created.id)
    assert verify_password(NEW_PASSWORD, user.hashed_password)
    assert not verify_password(OLD_PASSWORD, user.hashed_password)
    assert await db_session.scalar(select(PasswordResetToken)) is None


async def test_reset_password_revokes_all_refresh_tokens_of_the_user(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user()
    other = await create_user(email="other@test.com")
    await add_reset_token(db_session, created.id)
    await add_refresh_token(db_session, created.id, "phone")
    await add_refresh_token(db_session, created.id, "laptop")
    await add_refresh_token(db_session, other.id, "other-device")

    await reset_password(db_session, "reset-token", NEW_PASSWORD)

    remaining = (await db_session.scalars(select(RefreshToken.token))).all()
    assert remaining == ["other-device"]


async def test_reset_password_rejects_unknown_token(db_session: AsyncSession) -> None:
    with pytest.raises(BadRequestError, match="Invalid or expired reset token"):
        await reset_password(db_session, "no-such-token", NEW_PASSWORD)


async def test_reset_password_rejects_expired_token(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user(password=OLD_PASSWORD)
    await add_reset_token(db_session, created.id, hours=-1)

    with pytest.raises(BadRequestError, match="Invalid or expired reset token"):
        await reset_password(db_session, "reset-token", NEW_PASSWORD)

    user = await stored_user(db_session, created.id)
    assert verify_password(OLD_PASSWORD, user.hashed_password)


async def test_reset_token_cannot_be_used_twice(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user()
    await add_reset_token(db_session, created.id)
    await reset_password(db_session, "reset-token", NEW_PASSWORD)

    with pytest.raises(BadRequestError):
        await reset_password(db_session, "reset-token", "An0ther!Str0ngPass")
