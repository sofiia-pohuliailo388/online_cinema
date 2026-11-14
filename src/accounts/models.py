"""SQLAlchemy models of the accounts domain (spec, section 1). Owner: P2."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.accounts.enums import GenderEnum, UserGroupEnum
from src.core.models import Base, TimestampMixin


class UserGroup(Base):
    """User group (role): USER, MODERATOR or ADMIN. One group has many users."""

    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[UserGroupEnum] = mapped_column(Enum(UserGroupEnum), unique=True)

    users: Mapped[list["User"]] = relationship(back_populates="group")


class User(TimestampMixin, Base):
    """Registered user. Inactive until the account is activated by email."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=False)
    group_id: Mapped[int] = mapped_column(ForeignKey("user_groups.id"))

    group: Mapped["UserGroup"] = relationship(back_populates="users")
    profile: Mapped["UserProfile | None"] = relationship(back_populates="user")
    notification: Mapped["Notifications"] = relationship(back_populates="user")
    activation_token: Mapped["ActivationToken | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_token: Mapped["PasswordResetToken | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserProfile(Base):
    """Optional extra information about a user (one-to-one with ``User``)."""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    avatar: Mapped[str | None] = mapped_column(String(255))
    gender: Mapped[GenderEnum | None] = mapped_column(Enum(GenderEnum))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    info: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="profile")


class TokenMixin:
    """Columns shared by all token tables: id, unique token string and expiration time."""

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ActivationToken(TokenMixin, Base):
    """One-time token for account activation, valid for 24 hours after issuance."""

    __tablename__ = "activation_tokens"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    user: Mapped["User"] = relationship(back_populates="activation_token")


class PasswordResetToken(TokenMixin, Base):
    """Short-lived one-time token for password reset."""

    __tablename__ = "password_reset_tokens"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    user: Mapped["User"] = relationship(back_populates="password_reset_token")


class RefreshToken(TokenMixin, Base):
    """JWT refresh token stored in the DB; a user may have several (one per device)."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
