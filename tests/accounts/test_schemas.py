"""Tests for the accounts Pydantic schemas."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.accounts.schemas import UserRead, UserRegisterRequest


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
        id=1, email="user@example.com", is_active=False, hashed_password="secret-hash"
    )

    data = UserRead.model_validate(db_user).model_dump()

    assert data == {"id": 1, "email": "user@example.com", "is_active": False}
