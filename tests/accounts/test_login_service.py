"""Tests for ``login_user``."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.enums import UserGroupEnum
from src.accounts.models import RefreshToken
from src.accounts.security import decode_token
from src.accounts.service import login_user
from src.core.config import settings
from src.core.exceptions import PermissionDeniedError, UnauthorizedError
from tests.accounts.conftest import CreateUser

PASSWORD = "Str0ng!Pass"


async def test_login_user_returns_access_token_with_agreed_payload(
    db_session: AsyncSession,
    create_user: CreateUser,
) -> None:
    created = await create_user(UserGroupEnum.MODERATOR, password=PASSWORD)

    access_token, _ = await login_user(db_session, "user@test.com", PASSWORD)

    payload = decode_token(access_token)
    assert payload["user_id"] == created.id
    assert payload["group"] == "MODERATOR"


async def test_login_user_stores_refresh_token_in_db(
    db_session: AsyncSession,
    create_user: CreateUser,
) -> None:
    created = await create_user(password=PASSWORD)

    _, refresh_token = await login_user(db_session, "user@test.com", PASSWORD)

    stored = await db_session.scalar(
        select(RefreshToken).where(RefreshToken.token == refresh_token)
    )
    assert stored is not None
    assert stored.user_id == created.id
    expected = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS)
    actual = stored.expires_at.replace(tzinfo=None)
    assert abs((actual - expected.replace(tzinfo=None)).total_seconds()) < 5


async def test_login_user_allows_several_sessions(
    db_session: AsyncSession,
    create_user: CreateUser,
) -> None:
    await create_user(password=PASSWORD)

    _, first = await login_user(db_session, "user@test.com", PASSWORD)
    _, second = await login_user(db_session, "user@test.com", PASSWORD)

    assert first != second
    stored = (await db_session.scalars(select(RefreshToken))).all()
    assert len(stored) == 2


@pytest.mark.parametrize(
    ("email", "password"),
    [("user@test.com", "Wr0ng!Pass"), ("nobody@test.com", PASSWORD)],
    ids=["wrong_password", "unknown_email"],
)
async def test_login_user_rejects_bad_credentials(
    db_session: AsyncSession,
    create_user: CreateUser,
    email: str,
    password: str,
) -> None:
    await create_user(password=PASSWORD)

    with pytest.raises(UnauthorizedError, match="Invalid email or password"):
        await login_user(db_session, email, password)

    assert await db_session.scalar(select(RefreshToken)) is None


async def test_login_user_rejects_inactive_account(
    db_session: AsyncSession,
    create_user: CreateUser,
) -> None:
    await create_user(is_active=False, password=PASSWORD)

    with pytest.raises(PermissionDeniedError, match="not activated"):
        await login_user(db_session, "user@test.com", PASSWORD)

    assert await db_session.scalar(select(RefreshToken)) is None


async def test_login_user_does_not_reveal_inactive_account_to_wrong_password(
    db_session: AsyncSession,
    create_user: CreateUser,
) -> None:
    await create_user(is_active=False, password=PASSWORD)

    with pytest.raises(UnauthorizedError, match="Invalid email or password"):
        await login_user(db_session, "user@test.com", "Wr0ng!Pass")
