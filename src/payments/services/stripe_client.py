"""Thin wrapper around the Stripe SDK."""
import asyncio
import logging
from typing import Any

import stripe

from src.core.config import settings
from src.core.exceptions import BadRequestError

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


async def create_checkout_session(
    *, order_id: int, customer_email: str, line_items: list[Any]
) -> stripe.checkout.Session:
    """Create a Stripe Checkout Session with ``order_id`` stored in metadata.

    Raises:
        BadRequestError: If Stripe rejects the request.
    """
    try:
        return await asyncio.to_thread(
            stripe.checkout.Session.create,
            mode="payment",
            line_items=line_items,
            customer_email=customer_email,
            metadata={"order_id": str(order_id)},
            success_url=f"{settings.FRONTEND_URL}/payments/success",
            cancel_url=f"{settings.FRONTEND_URL}/payments/failed",
        )
    except stripe.StripeError as exc:
        logger.error("Stripe checkout session creation failed for order %s: %s", order_id, exc)
        raise BadRequestError("Could not create a payment session") from exc


async def create_refund(payment_intent_id: str) -> stripe.Refund:
    """Refund the full amount of a payment intent.

    Raises:
        BadRequestError: If Stripe rejects the refund.
    """
    try:
        return await asyncio.to_thread(
            stripe.Refund.create,
            payment_intent=payment_intent_id,
            idempotency_key=f"refund-{payment_intent_id}",
        )
    except stripe.StripeError as exc:
        logger.error("Stripe refund failed for %s: %s", payment_intent_id, exc)
        raise BadRequestError("Stripe could not process the refund") from exc


def verify_stripe_webhook(payload: bytes, sig_header: str | None) -> stripe.Event:
    """Validate the webhook signature and return the parsed event.

    Raises:
        BadRequestError: If the signature header is missing or invalid, or the payload is malformed.
    """
    if not sig_header:
        raise BadRequestError("Missing Stripe signature")
    try:
        return stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError as exc:
        raise BadRequestError("Invalid payload") from exc
    except stripe.SignatureVerificationError as exc:
        raise BadRequestError("Invalid signature") from exc
