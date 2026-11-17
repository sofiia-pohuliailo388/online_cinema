from decimal import Decimal
from unittest.mock import AsyncMock, patch

from src.accounts.enums import UserGroupEnum
from src.core.exceptions import ConflictError
from src.payments.models import PaymentStatus
from src.payments.services.payments_service import PaymentResult

HEADERS = {"Stripe-Signature": "t"}
API = "/api/v1/payments"


def _event(event_type: str = "checkout.session.completed") -> dict:
    return {"id": "evt_1", "type": event_type, "data": {"object": {}}}


def _result() -> PaymentResult:
    return PaymentResult(payment_id=1, order_id=1, user_id=1, amount=Decimal("9.99"))


async def _post_webhook(client, handler, mail, event=None):
    with patch("src.payments.router.verify_stripe_webhook", return_value=event or _event()), \
         patch("src.payments.router.service.handle_checkout_completed", handler), \
         patch("src.payments.router.service.send_payment_confirmation", mail):
        return await client.post(f"{API}/webhook", content=b"{}", headers=HEADERS)


async def test_webhook_sends_confirmation(client):
    mail = AsyncMock()

    response = await _post_webhook(client, AsyncMock(return_value=_result()), mail)

    assert response.status_code == 200
    mail.assert_awaited_once()
    assert mail.await_args.args[1] == _result()


async def test_webhook_duplicate_sends_nothing(client):
    mail = AsyncMock()

    response = await _post_webhook(client, AsyncMock(return_value=None), mail)

    assert response.status_code == 200
    mail.assert_not_awaited()


async def test_webhook_conflict_returns_200_without_email(client):
    mail = AsyncMock()

    response = await _post_webhook(client, AsyncMock(side_effect=ConflictError("x")), mail)

    assert response.status_code == 200
    mail.assert_not_awaited()


async def test_webhook_ignores_other_events(client):
    handler, mail = AsyncMock(), AsyncMock()

    response = await _post_webhook(client, handler, mail, event=_event("charge.updated"))

    assert response.status_code == 200
    handler.assert_not_awaited()
    mail.assert_not_awaited()


async def test_webhook_without_signature_returns_400(client):
    response = await client.post(f"{API}/webhook", content=b"{}")

    assert response.status_code == 400


async def test_webhook_bad_signature_returns_400(client):
    response = await client.post(
        f"{API}/webhook", content=b"{}", headers={"Stripe-Signature": "bad"}
    )

    assert response.status_code == 400


async def test_checkout_returns_url(client, login_as):
    login_as(UserGroupEnum.USER)
    with patch(
        "src.payments.router.service.create_checkout",
        AsyncMock(return_value="https://checkout.stripe.com/s"),
    ) as mocked:
        response = await client.post(f"{API}/checkout/5")

    assert response.status_code == 200
    assert response.json() == {"checkout_url": "https://checkout.stripe.com/s"}
    assert mocked.await_args.args[3] == 5


async def test_checkout_requires_auth(client):
    response = await client.post(f"{API}/checkout/5")

    assert response.status_code in (401, 403)


async def test_checkout_unknown_order_returns_404(client, login_as):
    login_as(UserGroupEnum.USER)

    response = await client.post(f"{API}/checkout/999999")

    assert response.status_code == 404


async def test_failed_hint_is_public(client):
    response = await client.get(f"{API}/failed")

    assert response.status_code == 200
    assert "different payment method" in response.json()["message"]


async def test_my_payments_requires_auth(client):
    response = await client.get(f"{API}/me")

    assert response.status_code in (401, 403)


async def test_my_payments_empty(client, login_as):
    login_as(UserGroupEnum.USER)

    response = await client.get(f"{API}/me")

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


async def test_all_payments_forbidden_for_regular_user(client, login_as):
    login_as(UserGroupEnum.USER)

    response = await client.get(API)

    assert response.status_code == 403


async def test_all_payments_for_admin_with_filters(client, login_as):
    login_as(UserGroupEnum.ADMIN)

    response = await client.get(
        API, params={"status": PaymentStatus.refunded.value, "user_id": 1}
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0


async def test_all_payments_invalid_status_returns_422(client, login_as):
    login_as(UserGroupEnum.ADMIN)

    response = await client.get(API, params={"status": "nope"})

    assert response.status_code == 422


async def test_refund_forbidden_for_regular_user(client, login_as):
    login_as(UserGroupEnum.USER)

    response = await client.post(f"{API}/1/refund")

    assert response.status_code == 403


async def test_refund_not_found(client, login_as):
    login_as(UserGroupEnum.ADMIN)

    response = await client.post(f"{API}/9999/refund")

    assert response.status_code == 404
