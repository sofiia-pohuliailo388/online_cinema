"""API endpoints of the payments domain (spec, section 5)."""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request

from src.accounts.dependencies import AdminUser, CurrentUser
from src.core.database import DbSession
from src.core.exceptions import ConflictError
from src.core.pagination import Page, PaginationParams
from src.payments.services import payments_service as service
from src.payments.models import PaymentStatus
from src.payments.schemas import CheckoutResponseSchema, PaymentHintSchema, PaymentReadSchema
from src.payments.services.stripe_client import verify_stripe_webhook

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Payments"], prefix="/payments")


@router.post("/checkout/{order_id}", response_model=CheckoutResponseSchema)
async def checkout(order_id: int, db: DbSession, user: CurrentUser) -> CheckoutResponseSchema:
    """Create a Stripe Checkout Session for the user's pending order."""
    url = await service.create_checkout(db, user.id, user.email, order_id)
    return CheckoutResponseSchema(checkout_url=url)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: DbSession) -> dict:
    """Receive Stripe events. The signature is verified before anything is processed."""
    payload = await request.body()
    event = verify_stripe_webhook(payload, request.headers.get("Stripe-Signature"))

    if event["type"] == "checkout.session.completed":
        try:
            result = await service.handle_checkout_completed(db, event["data"]["object"])
        except ConflictError:
            # Order was canceled but the money was charged: needs a manual refund.
            logger.error("Paid event for a canceled order, event id %s", event["id"])
            result = None

        if result is not None:
            # TODO: send the payment confirmation email here via EmailSender
            #       (use result.user_id / result.order_id / result.amount).
            #       Email failures must be logged and must NOT fail the webhook.
            pass

    return {"status": "success"}


@router.get("/failed", response_model=PaymentHintSchema)
async def payment_failed_hint() -> PaymentHintSchema:
    """Hint shown to the user after a declined or canceled payment (Stripe ``cancel_url``)."""
    return PaymentHintSchema(message=service.DECLINED_HINT)


@router.get("/me", response_model=Page[PaymentReadSchema])
async def my_payments(
    db: DbSession, user: CurrentUser, pagination: PaginationParams = Depends()
) -> Page[PaymentReadSchema]:
    """List the authenticated user's payment history."""
    payments, total = await service.get_user_payments(db, user.id, pagination)
    items = [PaymentReadSchema.model_validate(p) for p in payments]
    return Page.create(items=items, total=total, params=pagination)


@router.get("", response_model=Page[PaymentReadSchema])
async def all_payments(
    db: DbSession,
    admin: AdminUser,
    pagination: PaginationParams = Depends(),
    user_id: int | None = None,
    status: PaymentStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Page[PaymentReadSchema]:
    """List and filter all payments. Accessible to administrators only."""
    payments, total = await service.get_all_payments(
        db, pagination, user_id, status, date_from, date_to
    )
    items = [PaymentReadSchema.model_validate(p) for p in payments]
    return Page.create(items=items, total=total, params=pagination)


@router.post("/{payment_id}/refund", response_model=PaymentReadSchema)
async def refund(payment_id: int, db: DbSession, admin: AdminUser) -> PaymentReadSchema:
    """Refund a successful payment through Stripe. Accessible to administrators only."""
    payment = await service.refund_payment(db, payment_id)
    return PaymentReadSchema.model_validate(payment)
