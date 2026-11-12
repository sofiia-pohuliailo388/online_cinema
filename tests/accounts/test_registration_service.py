"""Tests for ``register_user``."""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import ActivationToken, UserGroup
from src.accounts.security import verify_password
from src.accounts.service import register_user, build_activation_link
from src.core.config import settings
from src.core.exceptions import ConflictError


async def test_register_user_creates_inactive_user_with_hashed_password(
    db_session: AsyncSession,
    user_group: UserGroup,
) -> None:
    user = await register_user(db_session, "user@example.com", "Str0ng!Pass")

    assert user.id is not None
    assert user.email == "user@example.com"
    assert user.is_active is False
    assert user.group_id == user_group.id
    assert user.hashed_password != "Str0ng!Pass"
    assert verify_password("Str0ng!Pass", user.hashed_password)


async def test_register_user_creates_activation_token_with_configured_ttl(
    db_session: AsyncSession,
    user_group: UserGroup,
) -> None:
    user = await register_user(db_session, "user@example.com", "Str0ng!Pass")

    token = await db_session.scalar(
        select(ActivationToken).where(ActivationToken.user_id == user.id),
    )

    assert token is not None
    assert len(token.token) >= 32
    # SQLite returns naive datetimes, Postgres aware ones: compare as naive UTC.
    expected = datetime.now(timezone.utc) + timedelta(hours=settings.ACTIVATION_TOKEN_TTL_HOURS)
    actual = token.expires_at.replace(tzinfo=None)
    assert abs((actual - expected.replace(tzinfo=None)).total_seconds()) < 5


async def test_register_user_rejects_duplicate_email(
    db_session: AsyncSession,
    user_group: UserGroup,
) -> None:
    await register_user(db_session, "user@example.com", "Str0ng!Pass")

    with pytest.raises(ConflictError, match="already exists"):
        await register_user(db_session, "user@example.com", "Str0ng!Pass")


async def test_register_user_fails_without_default_group(db_session: AsyncSession) -> None:
    with pytest.raises(RuntimeError, match="Default user group"):
        await register_user(db_session, "user@example.com", "Str0ng!Pass")


async def test_register_user_turns_integrity_error_into_conflict(
    db_session: AsyncSession,
    user_group: UserGroup,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_commit(self: AsyncSession) -> None:
        raise IntegrityError("INSERT", {}, Exception("duplicate key"))

    monkeypatch.setattr(AsyncSession, "commit", failing_commit)

    with pytest.raises(ConflictError, match="already exists"):
        await register_user(db_session, "user@example.com", "Str0ng!Pass")


@pytest.fixture
def sent_emails(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Replace ``send_email`` used by the service and collect everything it was asked to send."""
    sent: list[dict[str, Any]] = []

    def fake_send_email(**kwargs: Any) -> None:
        sent.append(kwargs)

    monkeypatch.setattr("src.accounts.service.send_email", fake_send_email)
    return sent


def test_build_activation_link_contains_token() -> None:
    link = build_activation_link("abc123")

    assert link == f"{settings.APP_BASE_URL}/api/v1/accounts/activate?token=abc123"


async def test_register_user_sends_activation_email(
    db_session: AsyncSession,
    user_group: UserGroup,
    sent_emails: list[dict[str, Any]],
) -> None:
    await register_user(db_session, "user@example.com", "Str0ng!Pass")

    token = await db_session.scalar(select(ActivationToken))
    assert token is not None
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "user@example.com"
    assert sent_emails[0]["template"] == "activation.html"
    assert sent_emails[0]["context"] == {"link": build_activation_link(token.token)}


async def test_register_user_does_not_send_email_for_duplicate(
    db_session: AsyncSession,
    user_group: UserGroup,
    sent_emails: list[dict[str, Any]],
) -> None:
    await register_user(db_session, "user@example.com", "Str0ng!Pass")

    with pytest.raises(ConflictError):
        await register_user(db_session, "user@example.com", "Str0ng!Pass")

    assert len(sent_emails) == 1
