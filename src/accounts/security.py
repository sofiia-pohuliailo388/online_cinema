"""Security helpers of the accounts domain: password strength validation."""

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
