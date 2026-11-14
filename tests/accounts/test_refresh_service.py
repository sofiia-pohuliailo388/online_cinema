"""Tests for ``_is_expired``, ``refresh_access_token`` and ``logout_user``."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.enums import UserGroupEnum
from src.accounts.models import RefreshToken
from src.accounts.security import decode_token
from src.accounts.service import _is_expired, logout_user, refresh_access_token
from src.core.exceptions import PermissionDeniedError, UnauthorizedError
from tests.accounts.conftest import CreateUser


async def add_refresh_token(
    db_session: AsyncSession, user_id: int, *, token: str = "refresh-token", days: int = 7
) -> None:
    """Store a refresh token that expires in ``days`` days (negative = already expired)."""
    db_session.add(
        RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=days),
        )
    )
    await db_session.commit()
    # Detach everything: the service must load the token from the DB like in production.
    db_session.expunge_all()


# --- _is_expired ---


@pytest.mark.parametrize(
    ("delta", "naive", "expected"),
    [
        (timedelta(hours=-1), False, True),
        (timedelta(hours=1), False, False),
        (timedelta(hours=-1), True, True),
        (timedelta(hours=1), True, False),
    ],
    ids=["past_aware", "future_aware", "past_naive", "future_naive"],
)
def test_is_expired(delta: timedelta, naive: bool, expected: bool) -> None:
    moment = datetime.now(timezone.utc) + delta
    if naive:
        moment = moment.replace(tzinfo=None)

    assert _is_expired(moment) is expected


# --- refresh_access_token ---


async def test_refresh_access_token_returns_valid_access_token(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user(UserGroupEnum.MODERATOR)
    await add_refresh_token(db_session, created.id)

    access_token = await refresh_access_token(db_session, "refresh-token")

    payload = decode_token(access_token)
    assert payload["user_id"] == created.id
    assert payload["group"] == "MODERATOR"


async def test_refresh_access_token_keeps_the_refresh_token(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user()
    await add_refresh_token(db_session, created.id)

    await refresh_access_token(db_session, "refresh-token")

    assert await db_session.scalar(select(RefreshToken)) is not None


async def test_refresh_access_token_rejects_unknown_token(db_session: AsyncSession) -> None:
    with pytest.raises(UnauthorizedError, match="Invalid or expired refresh token"):
        await refresh_access_token(db_session, "no-such-token")


async def test_refresh_access_token_rejects_expired_token(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user()
    await add_refresh_token(db_session, created.id, days=-1)

    with pytest.raises(UnauthorizedError, match="Invalid or expired refresh token"):
        await refresh_access_token(db_session, "refresh-token")


async def test_refresh_access_token_rejects_inactive_user(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user(is_active=False)
    await add_refresh_token(db_session, created.id)

    with pytest.raises(PermissionDeniedError, match="not activated"):
        await refresh_access_token(db_session, "refresh-token")


# --- logout_user ---


async def test_logout_user_deletes_only_the_given_token(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user()
    await add_refresh_token(db_session, created.id, token="phone")
    await add_refresh_token(db_session, created.id, token="laptop")

    await logout_user(db_session, "phone")

    remaining = (await db_session.scalars(select(RefreshToken.token))).all()
    assert remaining == ["laptop"]


async def test_logout_user_ignores_unknown_token(db_session: AsyncSession) -> None:
    await logout_user(db_session, "no-such-token")


async def test_refresh_fails_after_logout(
    db_session: AsyncSession, create_user: CreateUser
) -> None:
    created = await create_user()
    await add_refresh_token(db_session, created.id)

    await logout_user(db_session, "refresh-token")

    with pytest.raises(UnauthorizedError):
        await refresh_access_token(db_session, "refresh-token")
