"""HTTP endpoints of the accounts domain: registration, login, tokens and passwords.

Owner: P2. The router is shared with P3 (profile and admin endpoints).
"""

from typing import Annotated

from fastapi import APIRouter, Query, status

from src.accounts import service
from src.accounts.dependencies import CurrentUser
from src.accounts.schemas import (
    AccessTokenResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    MessageResponse,
    RefreshTokenRequest,
    ResendActivationRequest,
    ResetPasswordRequest,
    TokenPairResponse,
    UserLoginRequest,
    UserRead,
    UserRegisterRequest,
)
from src.core.database import DbSession
from src.core.exceptions import ErrorResponse

router = APIRouter(prefix="/accounts", tags=["accounts"])

RESEND_ACTIVATION_MESSAGE = (
    "If the account exists and is not activated, a new activation link has been sent."
)
FORGOT_PASSWORD_MESSAGE = (
    "If the account exists and is active, a password reset link has been sent."
)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Email already registered",
        },
    },
)
async def register(data: UserRegisterRequest, db: DbSession) -> UserRead:
    """Register a new account.

    The account is created inactive. An email with an activation link, valid for 24 hours,
    is sent to the given address. The password must have at least 8 characters, an upper and
    a lower case letter, a digit and a special character. The email is case-insensitive.
    """
    user = await service.register_user(db, data.email, data.password)
    return UserRead.model_validate(user)


@router.get(
    "/activate",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid or expired activation token",
        },
    },
)
async def activate(
    token: Annotated[str, Query(description="Activation token from the email link")],
    db: DbSession,
) -> UserRead:
    """Activate an account with the token from the activation email.

    The token can be used only once. After the activation the user can log in.
    """
    user = await service.activate_user(db, token)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Invalid email or password",
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "Account is not activated",
        },
    },
)
async def login(data: UserLoginRequest, db: DbSession) -> TokenPairResponse:
    """Log in with email and password and get a pair of tokens.

    Pass the ``access_token`` in the ``Authorization: Bearer <access_token>`` header of the
    requests that need authentication. It is short-lived. The ``refresh_token`` is stored on
    the server (a user can have several, one per device) and is used to get a new access token.
    The email is case-insensitive. A wrong email and a wrong password give the same error.
    """
    access_token, refresh_token = await service.login_user(db, data.email, data.password)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/refresh",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Invalid or expired refresh token",
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "Account is not activated",
        },
    },
)
async def refresh(data: RefreshTokenRequest, db: DbSession) -> AccessTokenResponse:
    """Get a new access token with the refresh token received on login.

    The access token is short-lived, the refresh token lives much longer. The refresh token
    itself does not change: it stays valid until it expires or until ``/logout``.
    """
    access_token = await service.refresh_access_token(db, data.refresh_token)
    return AccessTokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshTokenRequest, db: DbSession) -> None:
    """Log out: delete the refresh token from the server.

    The deleted refresh token can no longer be used to get new access tokens. An access token
    that was already issued stays valid until its (short) lifetime ends. A repeated logout
    with the same token is not an error.
    """
    await service.logout_user(db, data.refresh_token)


@router.post("/resend-activation")
async def resend_activation(data: ResendActivationRequest, db: DbSession) -> MessageResponse:
    """Send a new activation link, for example if the previous one has expired.

    The old link stops working and the new one is valid for 24 hours. The answer is always the
    same, whether such an email exists, is already activated or not, so that nobody can find out
    which emails are registered.
    """
    await service.resend_activation(db, data.email)
    return MessageResponse(message=RESEND_ACTIVATION_MESSAGE)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Old password is incorrect",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Not authenticated or invalid token",
        },
    },
)
async def change_password(data: ChangePasswordRequest, user: CurrentUser, db: DbSession) -> None:
    """Change the password of the current user.

    Requires the ``Authorization: Bearer <access_token>`` header. The old password must be
    correct. The new password must have at least 8 characters, an upper and a lower case letter,
    a digit and a special character. After the change the user logs in with the new password.
    """
    await service.change_password(db, user.id, data.old_password, data.new_password)


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: DbSession) -> MessageResponse:
    """Send a password reset link to the given email.

    The link is valid for 1 hour and can be used only once. The answer is always the same,
    whether such an email exists, is activated or not, so that nobody can find out which
    emails are registered.
    """
    await service.forgot_password(db, data.email)
    return MessageResponse(message=FORGOT_PASSWORD_MESSAGE)


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid or expired reset token",
        },
    },
)
async def reset_password(data: ResetPasswordRequest, db: DbSession) -> None:
    """Set a new password with the token from the reset email.

    The token can be used only once. The new password must have at least 8 characters, an
    upper and a lower case letter, a digit and a special character. After the reset all
    refresh tokens of the user are deleted, so the user has to log in again.
    """
    await service.reset_password(db, data.token, data.new_password)
