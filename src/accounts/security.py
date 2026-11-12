"""Security helpers of the accounts domain: password validation and hashing."""

import bcrypt

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt limit


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
