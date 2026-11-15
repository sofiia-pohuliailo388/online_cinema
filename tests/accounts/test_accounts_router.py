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


RESEND_URL = "/api/v1/accounts/resend-activation"
RESEND_MESSAGE = "If the account exists and is not activated, a new activation link has been sent."


async def test_resend_activation_sends_new_working_link(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    await client.post(REGISTER_URL, json=VALID_BODY)
    old_token = sent_emails[0]["context"]["link"].split("token=")[1]

    response = await client.post(RESEND_URL, json={"email": VALID_BODY["email"]})

    assert response.status_code == 200
    assert response.json() == {"message": RESEND_MESSAGE}
    assert len(sent_emails) == 2
    new_token = sent_emails[1]["context"]["link"].split("token=")[1]
    assert new_token != old_token
    assert (await client.get(ACTIVATE_URL, params={"token": old_token})).status_code == 400
    assert (await client.get(ACTIVATE_URL, params={"token": new_token})).status_code == 200


async def test_resend_activation_answer_is_the_same_for_unknown_email(
    client: AsyncClient, sent_emails: list[dict[str, Any]]
) -> None:
    response = await client.post(RESEND_URL, json={"email": "nobody@example.com"})

    assert response.status_code == 200
    assert response.json() == {"message": RESEND_MESSAGE}
    assert sent_emails == []


async def test_resend_activation_answer_is_the_same_for_active_account(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    await register_and_activate(client, sent_emails)

    response = await client.post(RESEND_URL, json={"email": VALID_BODY["email"]})

    assert response.status_code == 200
    assert response.json() == {"message": RESEND_MESSAGE}
    assert len(sent_emails) == 1  # only the registration email


async def test_resend_activation_rejects_invalid_email(client: AsyncClient) -> None:
    response = await client.post(RESEND_URL, json={"email": "not-an-email"})

    assert response.status_code == 422


CHANGE_PASSWORD_URL = "/api/v1/accounts/change-password"
NEW_PASSWORD = "N3w!Str0ngPass"


def auth_headers(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_change_password_switches_login_to_the_new_password(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    tokens = await login_tokens(client, sent_emails)

    response = await client.post(
        CHANGE_PASSWORD_URL,
        json={"old_password": VALID_BODY["password"], "new_password": NEW_PASSWORD},
        headers=auth_headers(tokens),
    )

    assert response.status_code == 204
    old_login = await client.post(LOGIN_URL, json=VALID_BODY)
    new_login = await client.post(
        LOGIN_URL, json={"email": VALID_BODY["email"], "password": NEW_PASSWORD}
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200


async def test_change_password_with_wrong_old_password_returns_400(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    tokens = await login_tokens(client, sent_emails)

    response = await client.post(
        CHANGE_PASSWORD_URL,
        json={"old_password": "Wr0ng!Pass", "new_password": NEW_PASSWORD},
        headers=auth_headers(tokens),
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Old password is incorrect"}
    assert (await client.post(LOGIN_URL, json=VALID_BODY)).status_code == 200


async def test_change_password_rejects_weak_new_password(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    tokens = await login_tokens(client, sent_emails)

    response = await client.post(
        CHANGE_PASSWORD_URL,
        json={"old_password": VALID_BODY["password"], "new_password": "weak"},
        headers=auth_headers(tokens),
    )

    assert response.status_code == 422


async def test_change_password_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        CHANGE_PASSWORD_URL, json={"old_password": "x", "new_password": NEW_PASSWORD}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


async def test_change_password_rejects_invalid_token(client: AsyncClient) -> None:
    response = await client.post(
        CHANGE_PASSWORD_URL,
        json={"old_password": "x", "new_password": NEW_PASSWORD},
        headers={"Authorization": "Bearer garbage"},
    )

    assert response.status_code == 401


FORGOT_URL = "/api/v1/accounts/forgot-password"
RESET_URL = "/api/v1/accounts/reset-password"
FORGOT_MESSAGE = "If the account exists and is active, a password reset link has been sent."


def reset_token_from(email_message: dict[str, Any]) -> str:
    """Take the token out of the link of a sent password reset email."""
    return email_message["context"]["link"].split("token=")[1]


async def test_forgot_password_sends_reset_link(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    await register_and_activate(client, sent_emails)

    response = await client.post(FORGOT_URL, json={"email": VALID_BODY["email"]})

    assert response.status_code == 200
    assert response.json() == {"message": FORGOT_MESSAGE}
    assert len(sent_emails) == 2  # registration + reset
    assert sent_emails[1]["to"] == VALID_BODY["email"]
    assert sent_emails[1]["template"] == "password_reset.html"
    assert reset_token_from(sent_emails[1])


async def test_forgot_password_email_is_case_insensitive(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    await register_and_activate(client, sent_emails)

    response = await client.post(FORGOT_URL, json={"email": "USER@Example.com"})

    assert response.status_code == 200
    assert len(sent_emails) == 2


async def test_forgot_password_answer_is_the_same_for_unknown_email(
    client: AsyncClient, sent_emails: list[dict[str, Any]]
) -> None:
    response = await client.post(FORGOT_URL, json={"email": "nobody@example.com"})

    assert response.status_code == 200
    assert response.json() == {"message": FORGOT_MESSAGE}
    assert sent_emails == []


async def test_forgot_password_answer_is_the_same_for_inactive_account(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    await client.post(REGISTER_URL, json=VALID_BODY)  # registered, but not activated

    response = await client.post(FORGOT_URL, json={"email": VALID_BODY["email"]})

    assert response.status_code == 200
    assert response.json() == {"message": FORGOT_MESSAGE}
    assert len(sent_emails) == 1  # only the activation email


async def test_forgot_password_rejects_invalid_email(client: AsyncClient) -> None:
    response = await client.post(FORGOT_URL, json={"email": "not-an-email"})

    assert response.status_code == 422


async def test_reset_password_switches_login_to_the_new_password(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    await register_and_activate(client, sent_emails)
    await client.post(FORGOT_URL, json={"email": VALID_BODY["email"]})
    token = reset_token_from(sent_emails[1])

    response = await client.post(RESET_URL, json={"token": token, "new_password": NEW_PASSWORD})

    assert response.status_code == 204
    assert response.content == b""
    old_login = await client.post(LOGIN_URL, json=VALID_BODY)
    new_login = await client.post(
        LOGIN_URL, json={"email": VALID_BODY["email"], "password": NEW_PASSWORD}
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200


async def test_reset_token_works_only_once(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    await register_and_activate(client, sent_emails)
    await client.post(FORGOT_URL, json={"email": VALID_BODY["email"]})
    token = reset_token_from(sent_emails[1])
    await client.post(RESET_URL, json={"token": token, "new_password": NEW_PASSWORD})

    response = await client.post(RESET_URL, json={"token": token, "new_password": "An0ther!Pass99"})

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid or expired reset token"}
    login = await client.post(
        LOGIN_URL, json={"email": VALID_BODY["email"], "password": NEW_PASSWORD}
    )
    assert login.status_code == 200  # the first reset password is still the valid one


async def test_new_forgot_request_invalidates_the_previous_link(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    await register_and_activate(client, sent_emails)
    await client.post(FORGOT_URL, json={"email": VALID_BODY["email"]})
    await client.post(FORGOT_URL, json={"email": VALID_BODY["email"]})
    old_token = reset_token_from(sent_emails[1])
    new_token = reset_token_from(sent_emails[2])

    old_response = await client.post(
        RESET_URL, json={"token": old_token, "new_password": NEW_PASSWORD}
    )
    new_response = await client.post(
        RESET_URL, json={"token": new_token, "new_password": NEW_PASSWORD}
    )

    assert old_response.status_code == 400
    assert new_response.status_code == 204


async def test_reset_password_logs_out_all_devices(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    tokens = await login_tokens(client, sent_emails)
    second_device = (await client.post(LOGIN_URL, json=VALID_BODY)).json()
    await client.post(FORGOT_URL, json={"email": VALID_BODY["email"]})
    token = reset_token_from(sent_emails[1])

    await client.post(RESET_URL, json={"token": token, "new_password": NEW_PASSWORD})

    for device in (tokens, second_device):
        response = await client.post(REFRESH_URL, json={"refresh_token": device["refresh_token"]})
        assert response.status_code == 401


async def test_reset_password_with_unknown_token_returns_400(client: AsyncClient) -> None:
    response = await client.post(RESET_URL, json={"token": "unknown", "new_password": NEW_PASSWORD})

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid or expired reset token"}


async def test_reset_password_rejects_weak_password_and_keeps_the_token(
    client: AsyncClient, user_group: UserGroup, sent_emails: list[dict[str, Any]]
) -> None:
    await register_and_activate(client, sent_emails)
    await client.post(FORGOT_URL, json={"email": VALID_BODY["email"]})
    token = reset_token_from(sent_emails[1])

    weak = await client.post(RESET_URL, json={"token": token, "new_password": "weak"})
    retry = await client.post(RESET_URL, json={"token": token, "new_password": NEW_PASSWORD})

    assert weak.status_code == 422
    assert retry.status_code == 204


@pytest.mark.parametrize(
    "body",
    [{"token": "abc"}, {"new_password": NEW_PASSWORD}, {}],
    ids=["missing_password", "missing_token", "empty_body"],
)
async def test_reset_password_rejects_incomplete_body(
    client: AsyncClient, body: dict[str, str]
) -> None:
    response = await client.post(RESET_URL, json=body)

    assert response.status_code == 422
