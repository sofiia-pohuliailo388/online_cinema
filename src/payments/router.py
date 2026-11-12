from fastapi import APIRouter, Request, status
from src.payments.services.stripe_client import (
    create_test_checkout_session,
    verify_stripe_webhook,
)

router = APIRouter(tags=["payments"], prefix="/payments")

################### Тестова бета-версія модулю для теста вебхуків
@router.post("/create-checkout-session")
async def create_session():
    success_url = "https://example.com/success"
    cancel_url = "https://example.com/cancel"

    result = create_test_checkout_session(
        success_url=success_url, cancel_url=cancel_url
    )
    return result


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    event = verify_stripe_webhook(payload, sig_header)

    print(f"Успішно верифіковано подію від Stripe: {event['type']}")
    print(f"ID події: {event['id']}")

    return {"status": "success", "event_type": event["type"]}
