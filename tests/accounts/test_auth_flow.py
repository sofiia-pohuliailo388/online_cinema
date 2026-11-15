"""End-to-end tests of authorization (owner: P2).

* the whole life of an account, step by step, like a real client does it;
* real JWTs (no ``login_as``) against endpoints of other domains: cart and genres.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.enums import UserGroupEnum
from src.accounts.models import ActivationToken, User, UserGroup
from src.accounts.security import create_access_token
from src.core.config import settings
from tests.accounts.conftest import CreateUser

API = "/api/v1"
REGISTER_URL = f"{API}/accounts/register"
ACTIVATE_URL = f"{API}/accounts/activate"
RESEND_URL = f"{API}/accounts/resend-activation"
LOGIN_URL = f"{API}/accounts/login"
REFRESH_URL = f"{API}/accounts/refresh"
LOGOUT_URL = f"{API}/accounts/logout"
CART_URL = f"{API}/cart"
GENRES_URL = f"{API}/genres"

EMAIL = "flow@example.com"
PASSWORD = "Str0ng!Pass"
CREDENTIALS = {"email": EMAIL, "password": PASSWORD}


def token_from(email_message: dict[str, Any]) -> str:
    """Take the token out of the link of a sent email."""
    return email_message["context"]["link"].split("token=")[1]


def bearer(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def passes_authentication(client: AsyncClient, access_token: str) -> bool:
    """Tell whether the cart endpoint accepted the token.

    An authenticated user gets 200 (or 404 if the cart does not exist yet). What exactly the
    cart answers is the business of the cart domain, so only these two answers count as
    "the token was accepted". Anything else (401, a redirect) means it was not.
    """
    response = await client.get(CART_URL, headers=bearer(access_token))
    return response.status_code in (200, 404)


async def log_in(client: AsyncClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    """Log in through the API and return the pair of tokens."""
    response = await client.post(LOGIN_URL, json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()


# --- the whole life of an account ---


async def test_account_lifecycle_from_registration_to_logout(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    # 1. Registration: the account exists, but is inactive, and the link is sent by email.
    registered = await client.post(REGISTER_URL, json=CREDENTIALS)
    assert registered.status_code == 201
    assert registered.json()["is_active"] is False
    assert [message["to"] for message in sent_emails] == [EMAIL]

    # 2. Until the activation the user can not log in.
    assert (await client.post(LOGIN_URL, json=CREDENTIALS)).status_code == 403

    # 3. Activation with the link from the email.
    activated = await client.get(ACTIVATE_URL, params={"token": token_from(sent_emails[0])})
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True

    # 4. Login gives both tokens, and the access token opens a protected endpoint.
    tokens = await log_in(client, EMAIL)
    assert await passes_authentication(client, tokens["access_token"])

    # 5. Refresh gives a new access token that works too.
    refreshed = await client.post(REFRESH_URL, json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new_access_token = refreshed.json()["access_token"]
    assert await passes_authentication(client, new_access_token)

    # 6. Logout revokes the refresh token: it can not be used any more.
    assert (
        await client.post(LOGOUT_URL, json={"refresh_token": tokens["refresh_token"]})
    ).status_code == 204
    stale = await client.post(REFRESH_URL, json={"refresh_token": tokens["refresh_token"]})
    assert stale.status_code == 401
    assert stale.json() == {"detail": "Invalid or expired refresh token"}


async def test_logout_of_one_device_keeps_the_other_device_logged_in(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    await client.post(REGISTER_URL, json=CREDENTIALS)
    await client.get(ACTIVATE_URL, params={"token": token_from(sent_emails[0])})
    phone = await log_in(client, EMAIL)
    laptop = await log_in(client, EMAIL)

    await client.post(LOGOUT_URL, json={"refresh_token": phone["refresh_token"]})

    phone_refresh = await client.post(REFRESH_URL, json={"refresh_token": phone["refresh_token"]})
    laptop_refresh = await client.post(REFRESH_URL, json={"refresh_token": laptop["refresh_token"]})
    assert phone_refresh.status_code == 401
    assert laptop_refresh.status_code == 200


async def test_access_token_stays_valid_after_logout_until_it_expires(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    """Known design decision: only refresh tokens are stored, so an access token is not revoked."""
    await client.post(REGISTER_URL, json=CREDENTIALS)
    await client.get(ACTIVATE_URL, params={"token": token_from(sent_emails[0])})
    tokens = await log_in(client, EMAIL)

    await client.post(LOGOUT_URL, json={"refresh_token": tokens["refresh_token"]})

    assert await passes_authentication(client, tokens["access_token"])


# --- activation: expired token, resend ---


async def test_expired_activation_link_is_replaced_by_resend_activation(
    client: AsyncClient,
    db_session: AsyncSession,
    user_group: UserGroup,
    sent_emails: list[dict[str, Any]],
) -> None:
    await client.post(REGISTER_URL, json=CREDENTIALS)
    old_token = token_from(sent_emails[0])
    await db_session.execute(
        update(ActivationToken).values(expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
    )
    await db_session.commit()

    expired = await client.get(ACTIVATE_URL, params={"token": old_token})
    assert expired.status_code == 400
    assert expired.json() == {"detail": "Activation token has expired"}

    await client.post(RESEND_URL, json={"email": EMAIL})
    new_token = token_from(sent_emails[1])
    assert new_token != old_token
    assert (await client.get(ACTIVATE_URL, params={"token": old_token})).status_code == 400
    assert (await client.get(ACTIVATE_URL, params={"token": new_token})).status_code == 200
    assert (await client.post(LOGIN_URL, json=CREDENTIALS)).status_code == 200


async def test_weak_password_creates_no_account_and_sends_no_email(
    client: AsyncClient,
    db_session: AsyncSession,
    user_group: UserGroup,
    sent_emails: list[dict[str, Any]],
) -> None:
    response = await client.post(REGISTER_URL, json={"email": EMAIL, "password": "weak"})

    assert response.status_code == 422
    assert await db_session.scalar(select(User).where(User.email == EMAIL)) is None
    assert sent_emails == []


# --- inactive account ---


async def test_deactivated_account_loses_access(
    client: AsyncClient,
    db_session: AsyncSession,
    user_group: UserGroup,
    sent_emails: list[dict[str, Any]],
) -> None:
    await client.post(REGISTER_URL, json=CREDENTIALS)
    await client.get(ACTIVATE_URL, params={"token": token_from(sent_emails[0])})
    tokens = await log_in(client, EMAIL)

    await db_session.execute(update(User).values(is_active=False))
    await db_session.commit()

    assert (await client.get(CART_URL, headers=bearer(tokens["access_token"]))).status_code == 401
    refresh = await client.post(REFRESH_URL, json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 403
    assert (await client.post(LOGIN_URL, json=CREDENTIALS)).status_code == 403


async def test_token_of_inactive_user_is_rejected_by_other_domains(
    client: AsyncClient, create_user: CreateUser
) -> None:
    user = await create_user(email=EMAIL, is_active=False)
    token = create_access_token(user.id, UserGroupEnum.USER)

    response = await client.get(CART_URL, headers=bearer(token))

    assert response.status_code == 401
    assert response.json() == {"detail": "User not found or inactive"}


# --- real JWT against endpoints of other domains ---


async def test_protected_endpoint_of_another_domain_requires_a_token(
    client: AsyncClient,
) -> None:
    response = await client.get(CART_URL)

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


async def test_refresh_token_is_not_accepted_as_access_token(
    client: AsyncClient, create_user: CreateUser
) -> None:
    await create_user(email=EMAIL, password=PASSWORD)
    tokens = await log_in(client, EMAIL)

    response = await client.get(CART_URL, headers=bearer(tokens["refresh_token"]))

    assert response.status_code == 401


@pytest.mark.parametrize(
    "make_token",
    [
        lambda user_id: jwt.encode(
            {
                "user_id": user_id,
                "group": "USER",
                "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        ),
        lambda user_id: jwt.encode(
            {
                "user_id": user_id,
                "group": "ADMIN",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            "another-secret-key-that-is-long-enough",
            algorithm="HS256",
        ),
        lambda user_id: jwt.encode(
            {"user_id": user_id, "group": "USER"}, settings.SECRET_KEY, algorithm="HS256"
        ),
    ],
    ids=["expired", "forged_signature", "no_expiration"],
)
async def test_bad_access_tokens_are_rejected_by_other_domains(
    client: AsyncClient, create_user: CreateUser, make_token: Any
) -> None:
    user = await create_user(email=EMAIL)

    response = await client.get(CART_URL, headers=bearer(make_token(user.id)))

    assert response.status_code == 401


async def test_token_of_a_deleted_user_is_rejected(
    client: AsyncClient, db_session: AsyncSession, create_user: CreateUser
) -> None:
    user = await create_user(email=EMAIL)
    token = create_access_token(user.id, UserGroupEnum.USER)
    await db_session.delete(await db_session.get(User, user.id))
    await db_session.commit()

    response = await client.get(CART_URL, headers=bearer(token))

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("group", "expected_status"),
    [
        (UserGroupEnum.USER, 403),
        (UserGroupEnum.MODERATOR, 201),
        (UserGroupEnum.ADMIN, 201),
    ],
)
async def test_group_in_real_token_decides_access_to_moderator_endpoints(
    client: AsyncClient, create_user: CreateUser, group: UserGroupEnum, expected_status: int
) -> None:
    email = f"{group.value.lower()}@example.com"
    await create_user(group, email=email, password=PASSWORD)
    tokens = await log_in(client, email)

    response = await client.post(
        GENRES_URL, json={"name": "Drama"}, headers=bearer(tokens["access_token"])
    )

    assert response.status_code == expected_status
    if expected_status == 403:
        assert response.json() == {"detail": "Not enough permissions"}
