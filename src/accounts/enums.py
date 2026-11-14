"""Enums of the accounts domain (spec: UserGroupEnum, GenderEnum)."""

from enum import StrEnum


class UserGroupEnum(StrEnum):
    """User groups (roles). ADMIN inherits the permissions of all other groups."""

    USER = "USER"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"


class GenderEnum(StrEnum):
    """Gender values of a user profile."""

    MAN = "MAN"
    WOMAN = "WOMAN"
