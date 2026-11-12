"""End-to-end tests of the accounts endpoints (registration and activation)."""

from typing import Any

import pytest
from httpx import AsyncClient

from src.accounts.models import UserGroup

REGISTER_URL = "/api/v1/accounts/register"
ACTIVATE_URL = "/api/v1/accounts/activate"
VALID_BODY = {"email": "user@example.com", "password": "Str0ng!Pass"}


async def test_register_creates_inactive_user_and_sends_email(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
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
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    response = await client.post(
        REGISTER_URL, json={"email": "User@Example.COM", "password": "Str0ng!Pass"}
    )

    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"


async def test_register_duplicate_email_returns_409(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    await client.post(REGISTER_URL, json=VALID_BODY)

    response = await client.post(
        REGISTER_URL, json={"email": "USER@example.com", "password": "Str0ng!Pass"}
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
    client: AsyncClient, user_group: UserGroup, body: dict[str, str]
) -> None:
    response = await client.post(REGISTER_URL, json=body)

    assert response.status_code == 422


async def test_activate_with_link_from_email(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    await client.post(REGISTER_URL, json=VALID_BODY)
    token = sent_emails[0]["context"]["link"].split("token=")[1]

    response = await client.get(ACTIVATE_URL, params={"token": token})

    assert response.status_code == 200
    assert response.json()["is_active"] is True


async def test_activation_link_works_only_once(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
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
