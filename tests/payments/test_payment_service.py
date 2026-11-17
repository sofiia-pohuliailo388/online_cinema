import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.core.pagination import PaginationParams
from src.orders.models import StatusEnum
from src.payments.models import PaymentStatus
from src.payments.services import payments_service as service
from tests.payments.helpers import (
    count_payments,
    create_movie,
    create_order,
    create_user,
    get_payment,
    make_stripe_session,
)

PAGINATION = PaginationParams(page=1, per_page=20)


async def test_create_checkout_returns_url(db_session, user, pending_order, monkeypatch):
    mocked = AsyncMock(return_value=SimpleNamespace(url="https://checkout.stripe.com/s"))
    monkeypatch.setattr(service.stripe_client, "create_checkout_session", mocked)

    url = await service.create_checkout(db_session, user.id, user.email, pending_order.id)

    assert url == "https://checkout.stripe.com/s"
    kwargs = mocked.await_args.kwargs
    assert kwargs["order_id"] == pending_order.id
    assert kwargs["customer_email"] == user.email


async def test_create_checkout_recalculates_total(
    db_session, user, movie, pending_order, monkeypatch
):
    movie.price = Decimal("12.50")
    await db_session.commit()
    mocked = AsyncMock(return_value=SimpleNamespace(url="https://x"))
    monkeypatch.setattr(service.stripe_client, "create_checkout_session", mocked)

    await service.create_checkout(db_session, user.id, user.email, pending_order.id)

    line_items = mocked.await_args.kwargs["line_items"]
    assert line_items[0]["price_data"]["unit_amount"] == 1250
    assert line_items[0]["price_data"]["product_data"]["name"] == "Movie 1"
    await db_session.refresh(pending_order)
    assert pending_order.total_amount == Decimal("12.50")


async def test_create_checkout_multiple_items(db_session, user, monkeypatch):
    movies = [
        await create_movie(db_session, "A", "5.00"),
        await create_movie(db_session, "B", "7.50"),
    ]
    order = await create_order(db_session, user, movies)
    mocked = AsyncMock(return_value=SimpleNamespace(url="https://x"))
    monkeypatch.setattr(service.stripe_client, "create_checkout_session", mocked)

    await service.create_checkout(db_session, user.id, user.email, order.id)

    amounts = sorted(i["price_data"]["unit_amount"] for i in mocked.await_args.kwargs["line_items"])
    assert amounts == [500, 750]


async def test_create_checkout_order_not_found(db_session, user, monkeypatch):
    mocked = AsyncMock()
    monkeypatch.setattr(service.stripe_client, "create_checkout_session", mocked)

    with pytest.raises(NotFoundError):
        await service.create_checkout(db_session, user.id, user.email, 9999)

    mocked.assert_not_awaited()


async def test_create_checkout_foreign_order(db_session, pending_order, monkeypatch):
    other = await create_user(db_session, "other@example.com")
    await db_session.commit()
    mocked = AsyncMock()
    monkeypatch.setattr(service.stripe_client, "create_checkout_session", mocked)

    with pytest.raises(NotFoundError):
        await service.create_checkout(db_session, other.id, other.email, pending_order.id)

    mocked.assert_not_awaited()


@pytest.mark.parametrize("status", [StatusEnum.PAID, StatusEnum.CANCELED])
async def test_create_checkout_not_pending(db_session, user, movie, status, monkeypatch):
    order = await create_order(db_session, user, [movie], status=status)
    mocked = AsyncMock()
    monkeypatch.setattr(service.stripe_client, "create_checkout_session", mocked)

    with pytest.raises(ConflictError):
        await service.create_checkout(db_session, user.id, user.email, order.id)

    mocked.assert_not_awaited()


async def test_create_checkout_without_url(db_session, user, pending_order, monkeypatch):
    monkeypatch.setattr(
        service.stripe_client,
        "create_checkout_session",
        AsyncMock(return_value=SimpleNamespace(url=None)),
    )

    with pytest.raises(BadRequestError):
        await service.create_checkout(db_session, user.id, user.email, pending_order.id)


# ---------- handle_checkout_completed ----------

async def test_completed_creates_payment_and_marks_order_paid(db_session, user, pending_order):
    result = await service.handle_checkout_completed(db_session, make_stripe_session(pending_order))

    assert result is not None
    assert result.order_id == pending_order.id
    assert result.user_id == user.id
    assert result.amount == Decimal("9.99")

    payment = await get_payment(db_session, "pi_1")
    assert payment.status == PaymentStatus.successful
    assert payment.amount == Decimal("9.99")
    assert payment.user_id == user.id
    await db_session.refresh(pending_order)
    assert pending_order.status == StatusEnum.PAID


async def test_completed_creates_payment_items(db_session, user):
    movies = [
        await create_movie(db_session, "A", "5.00"),
        await create_movie(db_session, "B", "7.50"),
    ]
    order = await create_order(db_session, user, movies)

    await service.handle_checkout_completed(db_session, make_stripe_session(order))

    payments, total = await service.get_user_payments(db_session, user.id, PAGINATION)
    assert total == 1
    assert sorted(i.price_at_payment for i in payments[0].items) == [
        Decimal("5.00"),
        Decimal("7.50"),
    ]


async def test_completed_is_idempotent(db_session, pending_order):
    session = make_stripe_session(pending_order)

    first = await service.handle_checkout_completed(db_session, session)
    second = await service.handle_checkout_completed(db_session, session)

    assert first is not None
    assert second is None
    assert await count_payments(db_session) == 1


async def test_completed_second_intent_for_paid_order_is_ignored(
    db_session, pending_order, caplog
):
    await service.handle_checkout_completed(db_session, make_stripe_session(pending_order, "pi_1"))

    with caplog.at_level(logging.ERROR):
        result = await service.handle_checkout_completed(
            db_session, make_stripe_session(pending_order, "pi_2")
        )

    assert result is None
    assert await count_payments(db_session) == 1
    assert "manual refund required" in caplog.text


async def test_completed_unpaid_session_is_skipped(db_session, pending_order):
    result = await service.handle_checkout_completed(
        db_session, make_stripe_session(pending_order, payment_status="unpaid")
    )

    assert result is None
    assert await count_payments(db_session) == 0
    await db_session.refresh(pending_order)
    assert pending_order.status == StatusEnum.PENDING


async def test_completed_order_not_found(db_session):
    session = {
        "payment_status": "paid",
        "payment_intent": "pi_x",
        "amount_total": 100,
        "metadata": {"order_id": "9999"},
    }

    with pytest.raises(NotFoundError):
        await service.handle_checkout_completed(db_session, session)


@pytest.mark.parametrize("status", [StatusEnum.CANCELED, StatusEnum.PAID])
async def test_completed_non_pending_order_creates_no_payment(db_session, user, movie, status):
    order = await create_order(db_session, user, [movie], status=status)

    result = await service.handle_checkout_completed(db_session, make_stripe_session(order))

    assert result is None
    assert await count_payments(db_session) == 0


async def test_completed_amount_mismatch_is_logged_and_stripe_amount_stored(
    db_session, pending_order, caplog
):
    with caplog.at_level(logging.WARNING):
        result = await service.handle_checkout_completed(
            db_session, make_stripe_session(pending_order, amount_cents=500)
        )

    assert result.amount == Decimal("5.00")
    assert "Amount mismatch" in caplog.text
    assert (await get_payment(db_session, "pi_1")).amount == Decimal("5.00")


# ---------- payment history ----------

async def _paid(db_session, user, name, intent):
    movie = await create_movie(db_session, name)
    order = await create_order(db_session, user, [movie])
    await service.handle_checkout_completed(db_session, make_stripe_session(order, intent))
    return await get_payment(db_session, intent)


async def test_user_payments_only_own(db_session, user):
    other = await create_user(db_session, "other@example.com")
    await db_session.commit()
    await _paid(db_session, user, "Mine", "pi_mine")
    await _paid(db_session, other, "Theirs", "pi_theirs")

    payments, total = await service.get_user_payments(db_session, user.id, PAGINATION)

    assert total == 1
    assert payments[0].external_payment_id == "pi_mine"


async def test_user_payments_empty(db_session, user):
    payments, total = await service.get_user_payments(db_session, user.id, PAGINATION)

    assert payments == []
    assert total == 0


async def test_user_payments_pagination(db_session, user):
    for i in range(3):
        await _paid(db_session, user, f"M{i}", f"pi_{i}")

    page, total = await service.get_user_payments(
        db_session, user.id, PaginationParams(page=1, per_page=2)
    )

    assert total == 3
    assert len(page) == 2


async def test_all_payments_filter_by_user(db_session, user):
    other = await create_user(db_session, "other@example.com")
    await db_session.commit()
    await _paid(db_session, user, "Mine", "pi_mine")
    await _paid(db_session, other, "Theirs", "pi_theirs")

    _, total_all = await service.get_all_payments(db_session, PAGINATION)
    by_user, total_user = await service.get_all_payments(db_session, PAGINATION, user_id=user.id)

    assert total_all == 2
    assert total_user == 1
    assert by_user[0].external_payment_id == "pi_mine"


async def test_all_payments_filter_by_status(db_session, user):
    refunded = await _paid(db_session, user, "A", "pi_a")
    await _paid(db_session, user, "B", "pi_b")
    refunded.status = PaymentStatus.refunded
    await db_session.commit()

    r_items, r_total = await service.get_all_payments(
        db_session, PAGINATION, status=PaymentStatus.refunded
    )
    _, s_total = await service.get_all_payments(
        db_session, PAGINATION, status=PaymentStatus.successful
    )

    assert r_total == 1 and r_items[0].id == refunded.id
    assert s_total == 1


async def test_all_payments_filter_by_dates(db_session, user):
    await _paid(db_session, user, "A", "pi_a")
    now = datetime.now(timezone.utc)

    _, inside = await service.get_all_payments(
        db_session,
        PAGINATION,
        date_from=now - timedelta(days=1),
        date_to=now + timedelta(days=1),
    )
    _, future = await service.get_all_payments(
        db_session, PAGINATION, date_from=now + timedelta(days=1)
    )
    _, past = await service.get_all_payments(
        db_session, PAGINATION, date_to=now - timedelta(days=1)
    )

    assert inside == 1
    assert future == 0
    assert past == 0


# ---------- refund ----------

async def test_refund_success(db_session, pending_order, monkeypatch):
    payment = await _paid_for(db_session, pending_order, "pi_r")
    mocked = AsyncMock()
    monkeypatch.setattr(service.stripe_client, "create_refund", mocked)

    refunded = await service.refund_payment(db_session, payment.id)

    mocked.assert_awaited_once_with("pi_r")
    assert refunded.status == PaymentStatus.refunded
    assert len(refunded.items) == 1
    await db_session.refresh(pending_order)
    assert pending_order.status == StatusEnum.CANCELED


async def test_refund_twice_conflicts(db_session, pending_order, monkeypatch):
    payment = await _paid_for(db_session, pending_order, "pi_r")
    mocked = AsyncMock()
    monkeypatch.setattr(service.stripe_client, "create_refund", mocked)

    await service.refund_payment(db_session, payment.id)
    with pytest.raises(ConflictError):
        await service.refund_payment(db_session, payment.id)

    mocked.assert_awaited_once()


async def test_refund_not_found(db_session):
    with pytest.raises(NotFoundError):
        await service.refund_payment(db_session, 9999)


async def test_refund_without_external_id(db_session, pending_order, monkeypatch):
    payment = await _paid_for(db_session, pending_order, "pi_r")
    payment.external_payment_id = None
    await db_session.commit()
    mocked = AsyncMock()
    monkeypatch.setattr(service.stripe_client, "create_refund", mocked)

    with pytest.raises(ConflictError):
        await service.refund_payment(db_session, payment.id)

    mocked.assert_not_awaited()


async def test_refund_stripe_error_keeps_statuses(db_session, pending_order, monkeypatch):
    payment = await _paid_for(db_session, pending_order, "pi_r")
    monkeypatch.setattr(
        service.stripe_client, "create_refund", AsyncMock(side_effect=BadRequestError("fail"))
    )

    with pytest.raises(BadRequestError):
        await service.refund_payment(db_session, payment.id)

    await db_session.refresh(payment)
    await db_session.refresh(pending_order)
    assert payment.status == PaymentStatus.successful
    assert pending_order.status == StatusEnum.PAID


async def _paid_for(db_session, order, intent):
    await service.handle_checkout_completed(db_session, make_stripe_session(order, intent))
    return await get_payment(db_session, intent)
