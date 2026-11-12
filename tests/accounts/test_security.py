"""Unit tests for ``src.accounts.security`` (password strength validation)."""

import pytest

from src.accounts.security import MAX_PASSWORD_BYTES, validate_password_strength


def test_validate_password_strength_accepts_strong_password() -> None:
    assert validate_password_strength("Str0ng!Pass") == "Str0ng!Pass"


def test_validate_password_strength_accepts_exactly_max_bytes() -> None:
    password = "Aa1!" + "a" * (MAX_PASSWORD_BYTES - 4)

    assert validate_password_strength(password) == password


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("Aa1!aaa", "at least 8 characters"),
        ("Aa1!" + "a" * MAX_PASSWORD_BYTES, "at most 72 bytes"),
        ("str0ng!pass", "uppercase letter"),
        ("STR0NG!PASS", "lowercase letter"),
        ("Strong!Pass", "digit"),
        ("Str0ngPass1", "special character"),
    ],
    ids=["too_short", "too_long", "no_upper", "no_lower", "no_digit", "no_special"],
)
def test_validate_password_strength_rejects_weak_password(password: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_password_strength(password)


def test_validate_password_strength_counts_bytes_not_characters() -> None:
    # 40 Cyrillic letters = 80 bytes in UTF-8, but only 43 characters in total.
    password = "Aa1!" + "я" * 40

    with pytest.raises(ValueError, match="at most 72 bytes"):
        validate_password_strength(password)
