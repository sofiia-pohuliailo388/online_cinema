"""Pydantic schemas of the accounts domain (request and response bodies)."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.accounts.security import validate_password_strength


class EmailMixin(BaseModel):
    """Adds the ``email`` field, normalized to lower case."""

    email: EmailStr = Field(
        description="Account email (case-insensitive).",
        examples=["user@example.com"],
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Lowercase the email so that it is unique regardless of the letter case."""
        return value.lower()


class UserRegisterRequest(EmailMixin):
    """Body of the registration request."""

    password: str = Field(
        description=(
            "At least 8 characters: upper and lower case letter, digit and special character."
        ),
        examples=["Str0ng!Pass"],
    )

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        """Reject weak passwords (the response will be 422 with the reason)."""
        return validate_password_strength(value)


class UserLoginRequest(EmailMixin):
    """Body of the login request. The password strength is not checked on login."""

    password: str = Field(description="Account password.", examples=["Str0ng!Pass"])


class UserRead(BaseModel):
    """Public user data. Never contains the password or its hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="User id.", examples=[1])
    email: EmailStr = Field(description="User email.", examples=["user@example.com"])
    is_active: bool = Field(description="``False`` until the account is activated by email.")


class RefreshTokenRequest(BaseModel):
    """Body of the ``/refresh`` and ``/logout`` requests."""

    refresh_token: str = Field(
        description="Refresh token received on login.",
        examples=["kJ3xQ9vR2mT7wYpL0aZ8nC5dF1gH6sBu4eIoXjKq-Vw"],
    )


class AccessTokenResponse(BaseModel):
    """Response of ``/refresh``: a new short-lived access token."""

    access_token: str = Field(description="Short-lived JWT for the ``Authorization`` header.")
    token_type: str = Field(default="bearer", description="Token type.", examples=["bearer"])


class TokenPairResponse(AccessTokenResponse):
    """Pair of tokens issued on login."""

    refresh_token: str = Field(description="Long-lived token used to get a new access token.")


class ResendActivationRequest(EmailMixin):
    """Body of the ``/resend-activation`` request."""


class MessageResponse(BaseModel):
    """Plain text response for requests that must not reveal whether an account exists."""

    message: str = Field(
        description="Human-readable result of the request.",
        examples=["If the account exists and is not activated, a new link has been sent."],
    )
