import stripe
from fastapi import HTTPException, status
from src.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

########## Тестова версія модулю для перевірки роботи страйпу
def create_test_checkout_session(success_url: str, cancel_url: str) -> dict:
    """Створює тестову сесію чекауту без прив'язки до внутрішніх модель проєкту."""
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": "Test Product",
                        },
                        "unit_amount": 1000,
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe Checkout Error: {str(e)}",
        )


def verify_stripe_webhook(payload: bytes, sig_header: str) -> stripe.Event:
    """Перевіряє криптографічний підпис події вебхука від Stripe."""
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
        return event
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload"
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature"
        )
