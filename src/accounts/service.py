"""Business logic of the accounts domain (spec, section 1)."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.accounts.enums import UserGroupEnum
from src.accounts.models import User, UserGroup, ActivationToken, RefreshToken
from src.accounts.schemas import TokenPairResponse
from src.accounts.security import (
    hash_password,
    generate_token,
    verify_password,
    create_access_token,
)
from src.core.config import settings
from src.core.exceptions import (
    ConflictError,
    BadRequestError,
    UnauthorizedError,
    PermissionDeniedError,
)
from src.notifications.service import send_email


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Return a user by id with the group already loaded.

    Args:
        db: Database session.
        user_id: Id of the user to find.

    Returns:
        The user (with ``user.group`` loaded), or ``None`` if there is no such user.
    """
    result = await db.execute(
        select(User).options(selectinload(User.group)).where(User.id == user_id),
    )
    return result.scalar_one_or_none()


def build_activation_link(token: str) -> str:
    """Build the link from the activation email.

    Args:
        token: Activation token of the user.

    Returns:
        Absolute URL of the activation endpoint with the token as a query parameter.
    """
    return f"{settings.APP_BASE_URL}/api/v1/accounts/activate?token={token}"


async def register_user(db: AsyncSession, email: str, password: str) -> User:
    """Register a new inactive user and create an activation token for them.

    The user is put into the ``USER`` group. The account stays inactive until
    the activation token (valid for ``ACTIVATION_TOKEN_TTL_HOURS`` hours) is used.

    Args:
        db: Database session.
        email: Email of the new user (already normalized to lower case).
        password: Plain-text password, already validated for strength.

    Returns:
        The created user (``is_active=False``).

    Raises:
        ConflictError: If a user with this email already exists.
        RuntimeError: If the default ``USER`` group is missing (migrations were not applied).
    """
    existing_user = await db.scalar(select(User).where(User.email == email))
    if existing_user is not None:
        raise ConflictError("User with this email already exists")

    user_group = await db.scalar(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))
    if not user_group:
        raise RuntimeError("Default user group is missing")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        group_id=user_group.id,
    )
    db.add(user)
    await db.flush()

    activation_token = ActivationToken(
        user_id=user.id,
        token=generate_token(),
        expires_at=datetime.now(timezone.utc)
        + timedelta(hours=settings.ACTIVATION_TOKEN_TTL_HOURS),
    )
    db.add(activation_token)

    try:
        await db.commit()
    except IntegrityError as exc:
        # Two concurrent requests with the same email: the second one fails on the unique index.
        await db.rollback()
        raise ConflictError("User with this email already exists") from exc

    send_email(
        to=user.email,
        subject="Activation link",
        template="activation.html",
        context={
            "link": build_activation_link(activation_token.token),
        },
    )

    await db.refresh(user)

    return user


async def activate_user(db: AsyncSession, token: str) -> User:
    """Activate the account the activation token belongs to.

    The token is deleted after a successful activation, so it can be used only once.

    Args:
        db: Database session.
        token: Activation token from the email link.

    Returns:
        The activated user.

    Raises:
        BadRequestError: If the token does not exist or has expired.
    """
    activation_token = await db.scalar(
        select(ActivationToken).where(ActivationToken.token == token)
    )
    if activation_token is None:
        raise BadRequestError("Invalid activation token")

    expires_at = activation_token.expires_at
    if expires_at.tzinfo is None:
        # SQLite returns naive datetimes, Postgres aware ones.
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise BadRequestError("Activation token has expired")

    user = await db.scalar(select(User).where(User.id == activation_token.user_id))

    user.is_active = True
    await db.delete(activation_token)
    await db.commit()

    return user


async def login_user(db: AsyncSession, email: str, password: str) -> TokenPairResponse:
    """Check the credentials and issue a pair of tokens.

    The access token is a JWT. The refresh token is a random string stored in the DB,
    so it can be revoked on logout. A user may have several refresh tokens (one per device).

    Args:
        db: Database session.
        email: Email of the user (already normalized to lower case).
        password: Plain-text password.

    Returns:
        The access and refresh tokens.

    Raises:
        UnauthorizedError: If the email is unknown or the password is wrong
            (the same message for both, so that registered emails are not revealed).
        PermissionDeniedError: If the credentials are right, but the account is not activated.
    """
    user = await db.scalar(
        select(User).options(selectinload(User.group)).where(User.email == email)
    )
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")

    if not user.is_active:
        raise PermissionDeniedError("Account is not activated")

    access_token = create_access_token(user.id, user.group.name)
    refresh_token = generate_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token=refresh_token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS),
        )
    )
    await db.commit()

    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)
