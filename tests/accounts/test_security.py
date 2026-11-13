"""Unit tests for ``src.accounts.security`` (password strength validation)."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from src.accounts.enums import UserGroupEnum
from src.accounts.security import (
    MAX_PASSWORD_BYTES,
    create_access_token,
    decode_token,
    hash_password,
    validate_password_strength,
    verify_password,
    generate_token,
)
from src.core.config import settings
from src.core.exceptions import UnauthorizedError


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


def test_hash_password_returns_bcrypt_hash_not_plain_text() -> None:
    hashed = hash_password("Str0ng!Pass")

    assert hashed != "Str0ng!Pass"
    assert hashed.startswith("$2b$")


def test_hash_password_uses_random_salt() -> None:
    assert hash_password("Str0ng!Pass") != hash_password("Str0ng!Pass")


def test_verify_password_accepts_correct_password() -> None:
    hashed = hash_password("Str0ng!Pass")

    assert verify_password("Str0ng!Pass", hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("Str0ng!Pass")

    assert verify_password("Wr0ng!Pass", hashed) is False


def test_verify_password_rejects_too_long_password() -> None:
    hashed = hash_password("Str0ng!Pass")

    assert verify_password("Aa1!" + "a" * MAX_PASSWORD_BYTES, hashed) is False


def test_access_token_contains_agreed_payload() -> None:
    token = create_access_token(user_id=42, group=UserGroupEnum.MODERATOR)

    payload = decode_token(token)

    assert payload["user_id"] == 42
    assert payload["group"] == "MODERATOR"
    assert set(payload) == {"user_id", "group", "exp"}


def test_access_token_expires_after_configured_ttl() -> None:
    token = create_access_token(user_id=1, group=UserGroupEnum.USER)

    exp = datetime.fromtimestamp(decode_token(token)["exp"], tz=timezone.utc)
    expected = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_TTL_MINUTES)

    assert abs((exp - expected).total_seconds()) < 5


def test_decode_token_rejects_expired_token() -> None:
    payload = {
        "user_id": 1,
        "group": "USER",
        "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    with pytest.raises(UnauthorizedError):
        decode_token(token)


def test_decode_token_rejects_wrong_signature() -> None:
    payload = {
        "user_id": 1,
        "group": "USER",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, "another-secret-key-that-is-long-enough", algorithm="HS256")

    with pytest.raises(UnauthorizedError):
        decode_token(token)


def test_decode_token_rejects_garbage() -> None:
    with pytest.raises(UnauthorizedError):
        decode_token("not-a-jwt")


def test_generate_token_returns_url_safe_string_that_fits_the_column() -> None:
    token = generate_token()

    assert len(token) <= 255
    assert token.replace("-", "").replace("_", "").isalnum()


def test_generate_token_is_unique() -> None:
    assert len({generate_token() for _ in range(100)}) == 100
