"""Schemas for the user profile and admin user management (spec, section 1). Owner: P3."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.accounts.enums import GenderEnum, UserGroupEnum


class ProfileUpdate(BaseModel):
    """Body of ``PATCH /users/me/profile``: only the sent fields are changed."""

    first_name: str | None = Field(default=None, max_length=100, examples=["Sofiia"])
    last_name: str | None = Field(default=None, max_length=100, examples=["Pohuliailo"])
    gender: GenderEnum | None = Field(default=None, examples=[GenderEnum.WOMAN])
    date_of_birth: date | None = Field(default=None, examples=["2000-01-31"])
    info: str | None = Field(default=None, max_length=1000, examples=["I love sci-fi."])

    @field_validator("date_of_birth")
    @classmethod
    def not_in_future(cls, value: date | None) -> date | None:
        """A date of birth cannot be in the future."""
        if value is not None and value > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return value


class ProfileRead(BaseModel):
    """The current user's profile. ``avatar_url`` is a temporary link (about 1 hour)."""

    first_name: str | None
    last_name: str | None
    gender: GenderEnum | None
    date_of_birth: date | None
    info: str | None
    avatar_url: str | None = Field(description="Temporary link to the avatar, or null.")


class AdminUserRead(BaseModel):
    """A user as seen by an administrator."""

    id: int
    email: str
    is_active: bool
    group: UserGroupEnum
    created_at: datetime

    @classmethod
    def from_user(cls, user: Any) -> "AdminUserRead":
        """Build from a ``User`` with ``user.group`` loaded."""
        return cls(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            group=user.group.name,
            created_at=user.created_at,
        )


class ChangeGroupRequest(BaseModel):
    """Body of ``PATCH /admin/users/{user_id}/group``."""

    group: UserGroupEnum = Field(examples=[UserGroupEnum.MODERATOR])
