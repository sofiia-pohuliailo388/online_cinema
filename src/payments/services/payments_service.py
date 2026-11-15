"""Business logic of the payments domain."""
import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ConflictError, NotFoundError
from src.core.pagination import PaginationParams, paginate
from src.orders.models import Order, OrderItem, StatusEnum
from src.orders.service import mark_order_paid
from src.payments.models import Payment, PaymentItem, PaymentStatus
from src.payments.services import stripe_client

logger = logging.getLogger(__name__)

DECLINED_HINT = "The payment was declined. Please try a different payment method."


class PaymentResult(NamedTuple):
    """Plain values captured before commit (safe to use after the session expires objects)."""

    payment_id: int
    order_id: int
    user_id: int
    amount: Decimal


def _to_cents(amount: Decimal) -> int:
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


async def create_checkout(db: AsyncSession, user_id: int, email: str, order_id: int) -> str:
    """Recalculate the order total from current movie prices and open a Stripe Checkout Session.

    Returns:
        The Stripe-hosted payment page URL.

    Raises:
        NotFoundError: If the order does not exist or belongs to another user.
        ConflictError: If the order is not pending.
    """
    order = await db.scalar(
        select(Order)
        .where(Order.id == order_id, Order.user_id == user_id)
        .options(selectinload(Order.order_items).selectinload(OrderItem.movie))
    )
    if order is None:
        raise NotFoundError(f"Order {order_id} is not found")
    if order.status != StatusEnum.PENDING:
        raise ConflictError("Only pending orders can be paid")

    total = Decimal("0.00")
    line_items = []
    for item in order.order_items:
        item.price_at_order = item.movie.price
        total += item.price_at_order
        line_items.append(
            {
                "quantity": 1,
                "price_data": {
                    "currency": "usd",
                    "unit_amount": _to_cents(item.price_at_order),
                    "product_data": {"name": item.movie.name},
                },
            }
        )
    order.total_amount = total
    await db.commit()

    session = await stripe_client.create_checkout_session(
        order_id=order_id, customer_email=email, line_items=line_items
    )
    return session.url


async def handle_checkout_completed(db: AsyncSession, session) -> PaymentResult | None:
    """Create Payment and PaymentItems for a completed Checkout Session and mark the order paid.

    Idempotent: a repeated event creates nothing and returns ``None``.

    Raises:
        NotFoundError: If the order from the metadata does not exist.
        ConflictError: If the order was canceled while the payment was in progress.
    """
    if session["payment_status"] != "paid":
        logger.info("Checkout session is not paid yet, skipping")
        return None

    external_id = session["payment_intent"]
    if await db.scalar(select(Payment.id).where(Payment.external_payment_id == external_id)):
        logger.info("Duplicate webhook for payment intent %s, skipping", external_id)
        return None

    order_id = int(session["metadata"]["order_id"])
    order = await db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.order_items))
        .with_for_update()
    )

    if order is None:
        raise NotFoundError(f"Order {order_id} is not found")

    if order.status != StatusEnum.PENDING:
        logger.error(
            "Payment intent %s received for order %s in status %s, manual refund required",
            external_id, order_id, order.status,
        )
        await db.rollback()
        return None

    amount = Decimal(session["amount_total"]) / 100
    if amount != order.total_amount:
        logger.warning(
            "Amount mismatch for order %s: stripe=%s, order=%s",
            order_id,
            amount,
            order.total_amount
        )

    user_id = order.user_id
    payment = Payment(
        user_id=user_id,
        order_id=order.id,
        amount=amount,
        status=PaymentStatus.successful,
        external_payment_id=external_id,
        items=[
            PaymentItem(order_item_id=i.id, price_at_payment=i.price_at_order)
            for i in order.order_items
        ],
    )
    db.add(payment)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        logger.info("Concurrent duplicate webhook for %s, skipping", external_id)
        return None

    payment_id = payment.id
    try:
        await mark_order_paid(db, order_id)
    except ConflictError:
        await db.rollback()
        raise

    logger.info("Payment %s created for order %s", payment_id, order_id)
    return PaymentResult(payment_id=payment_id, order_id=order_id, user_id=user_id, amount=amount)


async def get_user_payments(
        db: AsyncSession, user_id: int, pagination: PaginationParams
) -> tuple[list[Payment], int]:
    """Return the user's payment history (newest first) and the total count."""
    stmt = (
        select(Payment)
        .where(Payment.user_id == user_id)
        .options(selectinload(Payment.items))
        .order_by(Payment.created_at.desc())
    )
    return await paginate(db, stmt, pagination)


async def get_all_payments(
        db: AsyncSession,
        pagination: PaginationParams,
        user_id: int | None = None,
        status: PaymentStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
) -> tuple[list[Payment], int]:
    """Return all payments with optional admin filters (user, status, date range)."""
    stmt = select(Payment)
    if user_id is not None:
        stmt = stmt.where(Payment.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Payment.status == status)
    if date_from is not None:
        stmt = stmt.where(Payment.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Payment.created_at <= date_to)
    stmt = stmt.options(selectinload(Payment.items)).order_by(Payment.created_at.desc())
    return await paginate(db, stmt, pagination)


async def refund_payment(db: AsyncSession, payment_id: int) -> Payment:
    """Refund a successful payment through Stripe, mark it ``refunded`` and release the order.

    Raises:
        NotFoundError: If the payment does not exist.
        ConflictError: If the payment is not successful or has no Stripe id.
        BadRequestError: If Stripe rejects the refund.
    """

    payment = await db.scalar(
        select(Payment)
        .where(Payment.id == payment_id)
        .options(selectinload(Payment.order))
        .with_for_update()
    )
    if payment is None:
        raise NotFoundError(f"Payment {payment_id} is not found")
    if payment.status != PaymentStatus.successful:
        raise ConflictError("Only successful payments can be refunded")
    if not payment.external_payment_id:
        raise ConflictError("Payment has no external Stripe id")

    await stripe_client.create_refund(payment.external_payment_id)
    payment.status = PaymentStatus.refunded
    payment.order.status = StatusEnum.CANCELED
    await db.commit()
    logger.info("Payment %s refunded, order %s marked refunded", payment_id, payment.order_id)

    return await db.scalar(
        select(Payment)
        .where(Payment.id == payment_id)
        .options(selectinload(Payment.items))
        .execution_options(populate_existing=True)
    )
