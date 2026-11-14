"""HTTP endpoints of the accounts domain: registration and account activation."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from src.accounts import service
from src.accounts.schemas import UserRead, UserRegisterRequest, TokenPairResponse, UserLoginRequest
from src.core.database import DbSession
from src.core.exceptions import ErrorResponse

router = APIRouter(prefix="/accounts", tags=["accounts"])


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
    return await service.login_user(db, data.email, data.password)
