"""Security helpers of the accounts domain: password validation, hashing and JWT."""

from datetime import timezone, timedelta, datetime
from typing import Any

import bcrypt
import jwt
import secrets

from src.accounts.enums import UserGroupEnum
from src.core.config import settings
from src.core.exceptions import UnauthorizedError

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt limit
JWT_ALGORITHM = "HS256"


def validate_password_strength(password: str) -> str:
    """Check that a password is complex enough.

    Used both on registration and on password change/reset.

    Args:
        password: Plain-text password to validate.

    Returns:
        The same password, if it passed all checks.

    Raises:
        ValueError: If the password is too short, too long for bcrypt
            or misses an uppercase letter, a lowercase letter, a digit
            or a special character.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")
    if len(password.encode()) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes long")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain an uppercase letter")
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain a lowercase letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain a digit")
    if not any(not c.isalnum() for c in password):
        raise ValueError("Password must contain a special character")

    return password


def hash_password(password: str) -> str:
    """Hash a password with bcrypt (a random salt is generated and embedded in the hash).

    Args:
        password: Plain-text password. Must already be validated.

    Returns:
        The bcrypt hash as a string, ready to be stored in ``users.hashed_password``.
    """
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain-text password against a stored bcrypt hash.

    Args:
        plain_password: Password entered by the user.
        hashed_password: Hash stored in the database.

    Returns:
        ``True`` if the password matches the hash, ``False`` otherwise.
    """
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def create_access_token(user_id: int, group: UserGroupEnum) -> str:
    """Create a signed JWT access token.

    The payload is the contract agreed with the team:
    ``{"user_id": int, "group": "USER" | "MODERATOR" | "ADMIN", "exp": <unix time>}``.

    Args:
        user_id: Id of the user the token is issued for.
        group: Group (role) of the user.

    Returns:
        The encoded JWT. It expires after ``ACCESS_TOKEN_TTL_MINUTES`` minutes.
    """
    payload = {
        "user_id": user_id,
        "group": group.value,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Verify the signature and the expiration time of a JWT and return its payload.

    Args:
        token: Encoded JWT from the ``Authorization`` header.

    Returns:
        The decoded payload.

    Raises:
        UnauthorizedError: If the token is malformed, has a wrong signature or has expired.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc


def generate_token() -> str:
    """Generate a cryptographically secure random URL-safe token.

    Used for refresh tokens, account activation and password reset tokens.

    Returns:
        A random string of about 43 characters (256 bits of randomness).
    """
    return secrets.token_urlsafe(32)
