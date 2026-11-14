"""End-to-end tests of the accounts endpoints (registration and activation)."""

from typing import Any

import pytest
from httpx import AsyncClient

from src.accounts.models import UserGroup
from src.accounts.security import decode_token

REGISTER_URL = "/api/v1/accounts/register"
ACTIVATE_URL = "/api/v1/accounts/activate"
VALID_BODY = {"email": "user@example.com", "password": "Str0ng!Pass"}


async def test_register_creates_inactive_user_and_sends_email(
    client: AsyncClient,
    user_group: UserGroup,
    sent_emails: list[dict[str, Any]],
) -> None:
    response = await client.post(REGISTER_URL, json=VALID_BODY)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "user@example.com"
    assert body["is_active"] is False
    assert "password" not in body and "hashed_password" not in body
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "user@example.com"


async def test_register_lowercases_email(
    client: AsyncClient,
    user_group: UserGroup,
    sent_emails: list[dict[str, Any]],
) -> None:
    response = await client.post(
        REGISTER_URL,
        json={"email": "User@Example.COM", "password": "Str0ng!Pass"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"


async def test_register_duplicate_email_returns_409(
    client: AsyncClient,
    user_group: UserGroup,
    sent_emails: list[dict[str, Any]],
) -> None:
    await client.post(REGISTER_URL, json=VALID_BODY)

    response = await client.post(
        REGISTER_URL,
        json={"email": "USER@example.com", "password": "Str0ng!Pass"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "User with this email already exists"}


@pytest.mark.parametrize(
    "body",
    [
        {"email": "user@example.com", "password": "weak"},
        {"email": "user@example.com", "password": "alllowercase1!"},
        {"email": "not-an-email", "password": "Str0ng!Pass"},
        {"password": "Str0ng!Pass"},
    ],
    ids=["short_password", "no_uppercase", "invalid_email", "missing_email"],
)
async def test_register_rejects_invalid_body(
    client: AsyncClient,
    user_group: UserGroup,
    body: dict[str, str],
) -> None:
    response = await client.post(REGISTER_URL, json=body)

    assert response.status_code == 422


async def test_activate_with_link_from_email(
    client: AsyncClient,
    user_group: UserGroup,
    sent_emails: list[dict[str, Any]],
) -> None:
    await client.post(REGISTER_URL, json=VALID_BODY)
    token = sent_emails[0]["context"]["link"].split("token=")[1]

    response = await client.get(ACTIVATE_URL, params={"token": token})

    assert response.status_code == 200
    assert response.json()["is_active"] is True


async def test_activation_link_works_only_once(
    client: AsyncClient,
    user_group: UserGroup,
    sent_emails: list[dict[str, Any]],
) -> None:
    await client.post(REGISTER_URL, json=VALID_BODY)
    token = sent_emails[0]["context"]["link"].split("token=")[1]
    await client.get(ACTIVATE_URL, params={"token": token})

    response = await client.get(ACTIVATE_URL, params={"token": token})

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid activation token"}


async def test_activate_with_unknown_token_returns_400(client: AsyncClient) -> None:
    response = await client.get(ACTIVATE_URL, params={"token": "unknown"})

    assert response.status_code == 400


async def test_activate_without_token_returns_422(client: AsyncClient) -> None:
    response = await client.get(ACTIVATE_URL)

    assert response.status_code == 422


LOGIN_URL = "/api/v1/accounts/login"


async def register_and_activate(client: AsyncClient, sent_emails: list[dict[str, Any]]) -> None:
    """Go through the registration and the activation link, like a real user."""
    await client.post(REGISTER_URL, json=VALID_BODY)
    token = sent_emails[0]["context"]["link"].split("token=")[1]
    await client.get(ACTIVATE_URL, params={"token": token})


async def test_register_activate_login_flow(
    client: AsyncClient,
    user_group: UserGroup,
    sent_emails: list[dict[str, Any]],
) -> None:
    await register_and_activate(client, sent_emails)

    response = await client.post(LOGIN_URL, json=VALID_BODY)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "refresh_token", "token_type"}
    assert body["token_type"] == "bearer"
    assert decode_token(body["access_token"])["group"] == "USER"


async def test_login_email_is_case_insensitive(
    client: AsyncClient,
    user_group: UserGroup,
    sent_emails: list[dict[str, Any]],
) -> None:
    await register_and_activate(client, sent_emails)

    response = await client.post(
        LOGIN_URL,
        json={"email": "USER@Example.COM", "password": "Str0ng!Pass"},
    )

    assert response.status_code == 200


async def test_login_before_activation_returns_403(
    client: AsyncClient,
    user_group: UserGroup,
    sent_emails: list[dict[str, Any]],
) -> None:
    await client.post(REGISTER_URL, json=VALID_BODY)

    response = await client.post(LOGIN_URL, json=VALID_BODY)

    assert response.status_code == 403
    assert response.json() == {"detail": "Account is not activated"}


@pytest.mark.parametrize(
    "body",
    [
        {"email": "user@example.com", "password": "Wr0ng!Pass"},
        {"email": "nobody@example.com", "password": "Str0ng!Pass"},
    ],
    ids=["wrong_password", "unknown_email"],
)
async def test_login_with_bad_credentials_returns_401(
    client: AsyncClient,
    user_group: UserGroup,
    sent_emails: list[dict[str, Any]],
    body: dict[str, str],
) -> None:
    await register_and_activate(client, sent_emails)

    response = await client.post(LOGIN_URL, json=body)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


async def test_login_without_password_returns_422(client: AsyncClient) -> None:
    response = await client.post(LOGIN_URL, json={"email": "user@example.com"})

    assert response.status_code == 422


REFRESH_URL = "/api/v1/accounts/refresh"
LOGOUT_URL = "/api/v1/accounts/logout"


async def login_tokens(client: AsyncClient, sent_emails: list[dict[str, Any]]) -> dict[str, str]:
    await register_and_activate(client, sent_emails)
    response = await client.post(LOGIN_URL, json=VALID_BODY)
    return response.json()


async def test_refresh_returns_new_access_token(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    tokens = await login_tokens(client, sent_emails)

    response = await client.post(REFRESH_URL, json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "token_type"}
    assert decode_token(body["access_token"])["group"] == "USER"


async def test_refresh_with_unknown_token_returns_401(client: AsyncClient) -> None:
    response = await client.post(REFRESH_URL, json={"refresh_token": "unknown"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired refresh token"}


async def test_refresh_without_body_returns_422(client: AsyncClient) -> None:
    response = await client.post(REFRESH_URL, json={})

    assert response.status_code == 422


async def test_logout_revokes_refresh_token(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    tokens = await login_tokens(client, sent_emails)
    body = {"refresh_token": tokens["refresh_token"]}

    response = await client.post(LOGOUT_URL, json=body)

    assert response.status_code == 204
    assert response.content == b""
    assert (await client.post(REFRESH_URL, json=body)).status_code == 401


async def test_repeated_logout_is_not_an_error(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    tokens = await login_tokens(client, sent_emails)
    body = {"refresh_token": tokens["refresh_token"]}

    assert (await client.post(LOGOUT_URL, json=body)).status_code == 204
    assert (await client.post(LOGOUT_URL, json=body)).status_code == 204
