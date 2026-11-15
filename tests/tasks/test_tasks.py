"""Background jobs: expired token cleanup and email queueing (spec, section 1)."""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.enums import UserGroupEnum
from src.accounts.models import ActivationToken, PasswordResetToken, User, UserGroup
from src.notifications import service as notifications_service
from src.tasks import service as tasks_service


async def _create_user(db: AsyncSession, email: str) -> User:
    group = await db.scalar(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))
    if group is None:
        group = UserGroup(name=UserGroupEnum.USER)
        db.add(group)
        await db.flush()
    user = User(email=email, hashed_password="hash", group_id=group.id)
    db.add(user)
    await db.flush()
    return user


async def test_delete_expired_tokens_removes_only_expired(db_session: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    old_user = await _create_user(db_session, "old@test.com")
    new_user = await _create_user(db_session, "new@test.com")
    db_session.add_all(
        [
            ActivationToken(
                user_id=old_user.id, token="a-old", expires_at=now - timedelta(hours=1)
            ),
            ActivationToken(
                user_id=new_user.id, token="a-new", expires_at=now + timedelta(hours=23)
            ),
            PasswordResetToken(
                user_id=old_user.id, token="r-old", expires_at=now - timedelta(minutes=1)
            ),
            PasswordResetToken(
                user_id=new_user.id, token="r-new", expires_at=now + timedelta(hours=1)
            ),
        ]
    )
    await db_session.commit()

    deleted = await tasks_service.delete_expired_tokens(db_session)

    assert deleted == (1, 1)
    assert list(await db_session.scalars(select(ActivationToken.token))) == ["a-new"]
    assert list(await db_session.scalars(select(PasswordResetToken.token))) == ["r-new"]


async def test_delete_expired_tokens_with_nothing_expired(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, "user@test.com")
    db_session.add(
        ActivationToken(
            user_id=user.id,
            token="a-new",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    )
    await db_session.commit()

    deleted = await tasks_service.delete_expired_tokens(db_session)

    assert deleted == (0, 0)


class FakeTask:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.error = error

    def delay(self, **kwargs: Any) -> None:
        if self.error:
            raise self.error
        self.calls.append(kwargs)


def test_send_email_queues_celery_task(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_task = FakeTask()
    monkeypatch.setattr(tasks_service, "send_email_task", fake_task)

    notifications_service.send_email(
        to="user@test.com", subject="Hi", template="activation.html", context={"link": "x"}
    )

    assert fake_task.calls == [
        {
            "to": "user@test.com",
            "subject": "Hi",
            "template": "activation.html",
            "context": {"link": "x"},
        }
    ]


def test_send_email_does_not_fail_when_queue_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tasks_service, "send_email_task", FakeTask(error=ConnectionError()))

    notifications_service.send_email(
        to="user@test.com", subject="Hi", template="activation.html", context={"link": "x"}
    )


def test_deliver_email_uses_smtp_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[tuple[str, int, str, list[str]]] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int) -> None:
            self.host, self.port = host, port

        def __enter__(self) -> "FakeSMTP":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def sendmail(self, from_addr: str, to_addrs: list[str], msg: str) -> None:
            sent.append((self.host, self.port, from_addr, to_addrs))

    monkeypatch.setattr(notifications_service.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(notifications_service.settings, "SMTP_HOST", "mailhog")
    monkeypatch.setattr(notifications_service.settings, "SMTP_PORT", 1025)

    notifications_service.deliver_email(
        to="user@test.com", subject="Hi", template="activation.html", context={"link": "x"}
    )

    assert sent == [("mailhog", 1025, notifications_service.settings.EMAIL_FROM, ["user@test.com"])]
