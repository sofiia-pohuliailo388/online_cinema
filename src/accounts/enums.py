"""Enums of the accounts domain (spec: UserGroupEnum, GenderEnum)."""
from enum import StrEnum


class UserGroupEnum(StrEnum):
    USER = "USER"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"


class GenderEnum(StrEnum):
    MAN = "MAN"
    WOMAN = "WOMAN"
