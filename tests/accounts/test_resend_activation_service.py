"""Tests for ``resend_activation``."""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import ActivationToken
from src.accounts.service import build_activation_link, resend_activation
from src.core.config import settings
from tests.accounts.conftest import CreateUser


async def add_old_token(db_session: AsyncSession, user_id: int, *, hours: int) -> None:
    """Store an activation token that expires in ``hours`` hours (negative = expired)."""
    db_session.add(
        ActivationToken(
            user_id=user_id,
            token="old-token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=hours),
        )
    )
    await db_session.commit()
    db_session.expunge_all()


async def test_resend_activation_replaces_expired_token_and_sends_link(
    db_session: AsyncSession, create_user: CreateUser, sent_emails: list[dict[str, Any]]
) -> None:
    created = await create_user(is_active=False)
    await add_old_token(db_session, created.id, hours=-1)

    await resend_activation(db_session, "user@test.com")

    tokens = (await db_session.scalars(select(ActivationToken))).all()
    assert len(tokens) == 1
    new_token = tokens[0]
    assert new_token.token != "old-token"
    assert new_token.user_id == created.id
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "user@test.com"
    assert sent_emails[0]["context"] == {"link": build_activation_link(new_token.token)}


async def test_resend_activation_gives_new_token_full_lifetime(
    db_session: AsyncSession, create_user: CreateUser, sent_emails: list[dict[str, Any]]
) -> None:
    created = await create_user(is_active=False)
    await add_old_token(db_session, created.id, hours=1)

    await resend_activation(db_session, "user@test.com")

    token = await db_session.scalar(select(ActivationToken))
    assert token is not None
    expected = datetime.now(timezone.utc) + timedelta(hours=settings.ACTIVATION_TOKEN_TTL_HOURS)
    actual = token.expires_at.replace(tzinfo=None)
    assert abs((actual - expected.replace(tzinfo=None)).total_seconds()) < 5


async def test_resend_activation_creates_token_when_none_exists(
    db_session: AsyncSession, create_user: CreateUser, sent_emails: list[dict[str, Any]]
) -> None:
    await create_user(is_active=False)

    await resend_activation(db_session, "user@test.com")

    assert await db_session.scalar(select(ActivationToken)) is not None
    assert len(sent_emails) == 1


async def test_resend_activation_ignores_unknown_email(
    db_session: AsyncSession, sent_emails: list[dict[str, Any]]
) -> None:
    await resend_activation(db_session, "nobody@test.com")

    assert await db_session.scalar(select(ActivationToken)) is None
    assert sent_emails == []


async def test_resend_activation_ignores_already_active_account(
    db_session: AsyncSession, create_user: CreateUser, sent_emails: list[dict[str, Any]]
) -> None:
    await create_user(is_active=True)

    await resend_activation(db_session, "user@test.com")

    assert await db_session.scalar(select(ActivationToken)) is None
    assert sent_emails == []
