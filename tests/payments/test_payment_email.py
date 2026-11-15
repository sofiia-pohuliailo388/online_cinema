"""Payment confirmation email after a successful payment (spec, sections 4 and 5)."""

from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.enums import UserGroupEnum
from src.accounts.models import User, UserGroup
from src.movies.models import Certification, Movie
from src.orders.models import Order, OrderItem, StatusEnum
from src.payments.services import payments_service
from src.payments.services.payments_service import PaymentResult


@pytest.fixture
async def paid_order(db_session: AsyncSession) -> PaymentResult:
    group = UserGroup(name=UserGroupEnum.USER)
    certification = Certification(name="PG-13")
    db_session.add_all([group, certification])
    await db_session.flush()

    user = User(email="buyer@test.com", hashed_password="hash", is_active=True, group_id=group.id)
    movies = [
        Movie(
            name=name,
            year=2020,
            time=100,
            imdb=7.0,
            votes=10,
            description="Description",
            price=Decimal("5.00"),
            certification_id=certification.id,
        )
        for name in ["Matrix", "Inception"]
    ]
    db_session.add_all([user, *movies])
    await db_session.flush()

    order = Order(user_id=user.id, status=StatusEnum.PAID, total_amount=Decimal("10.00"))
    db_session.add(order)
    await db_session.flush()
    db_session.add_all(
        [OrderItem(order_id=order.id, movie_id=m.id, price_at_order=m.price) for m in movies]
    )
    await db_session.commit()

    return PaymentResult(
        payment_id=1, order_id=order.id, user_id=user.id, amount=Decimal("10.00")
    )


@pytest.fixture
def sent_emails(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    emails: list[dict[str, Any]] = []
    monkeypatch.setattr(
        payments_service, "send_email", lambda **kwargs: emails.append(kwargs)
    )
    return emails


async def test_confirmation_email_is_sent(
    db_session: AsyncSession, paid_order: PaymentResult, sent_emails: list[dict[str, Any]]
) -> None:
    await payments_service.send_payment_confirmation(db_session, paid_order)

    assert sent_emails == [
        {
            "to": "buyer@test.com",
            "subject": "Payment confirmation",
            "template": "payment_success.html",
            "context": {"movie_title": "Inception, Matrix", "amount": "$10.00"},
        }
    ]


async def test_no_email_for_unknown_user(
    db_session: AsyncSession, paid_order: PaymentResult, sent_emails: list[dict[str, Any]]
) -> None:
    result = paid_order._replace(user_id=999999)

    await payments_service.send_payment_confirmation(db_session, result)

    assert sent_emails == []


async def test_email_error_does_not_fail_webhook(
    db_session: AsyncSession, paid_order: PaymentResult, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_send_email(**kwargs: Any) -> None:
        raise RuntimeError("SMTP is down")

    monkeypatch.setattr(payments_service, "send_email", broken_send_email)

    await payments_service.send_payment_confirmation(db_session, paid_order)
