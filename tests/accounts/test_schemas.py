"""Tests for the accounts Pydantic schemas."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.accounts.schemas import (
    TokenPairResponse,
    UserLoginRequest,
    UserRead,
    UserRegisterRequest,
    AccessTokenResponse,
    RefreshTokenRequest,
    ResendActivationRequest,
    MessageResponse,
)


def test_register_request_accepts_valid_data() -> None:
    request = UserRegisterRequest(email="user@example.com", password="Str0ng!Pass")

    assert request.email == "user@example.com"
    assert request.password == "Str0ng!Pass"


def test_register_request_lowercases_email() -> None:
    request = UserRegisterRequest(email="User@Example.COM", password="Str0ng!Pass")

    assert request.email == "user@example.com"


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("Sh0rt!a", "at least 8 characters"),
        ("str0ng!pass", "uppercase letter"),
        ("Strong!Pass", "digit"),
    ],
    ids=["too_short", "no_uppercase", "no_digit"],
)
def test_register_request_rejects_weak_password(password: str, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        UserRegisterRequest(email="user@example.com", password=password)


def test_register_request_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        UserRegisterRequest(email="not-an-email", password="Str0ng!Pass")


def test_user_read_is_built_from_orm_object_without_password_hash() -> None:
    db_user = SimpleNamespace(
        id=1,
        email="user@example.com",
        is_active=False,
        hashed_password="secret-hash",
    )

    data = UserRead.model_validate(db_user).model_dump()

    assert data == {"id": 1, "email": "user@example.com", "is_active": False}


def test_login_request_lowercases_email() -> None:
    request = UserLoginRequest(email="User@Example.COM", password="whatever")

    assert request.email == "user@example.com"


def test_login_request_does_not_check_password_strength() -> None:
    # A user may have created the password under older rules: login must not reject it.
    request = UserLoginRequest(email="user@example.com", password="weak")

    assert request.password == "weak"


@pytest.mark.parametrize(
    "body",
    [{"email": "user@example.com"}, {"email": "not-an-email", "password": "x"}],
    ids=["missing_password", "invalid_email"],
)
def test_login_request_rejects_invalid_body(body: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        UserLoginRequest(**body)


def test_token_pair_response_defaults_to_bearer() -> None:
    response = TokenPairResponse(access_token="a", refresh_token="r")

    assert response.token_type == "bearer"


def test_refresh_token_request_requires_token() -> None:
    with pytest.raises(ValidationError):
        RefreshTokenRequest()


def test_access_token_response_defaults_to_bearer() -> None:
    assert AccessTokenResponse(access_token="a").token_type == "bearer"


def test_token_pair_response_has_all_three_fields() -> None:
    data = TokenPairResponse(access_token="a", refresh_token="r").model_dump()

    assert data == {"access_token": "a", "refresh_token": "r", "token_type": "bearer"}


def test_resend_activation_request_lowercases_email() -> None:
    assert ResendActivationRequest(email="User@Example.COM").email == "user@example.com"


def test_resend_activation_request_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        ResendActivationRequest(email="not-an-email")


def test_message_response_requires_message() -> None:
    with pytest.raises(ValidationError):
        MessageResponse()
