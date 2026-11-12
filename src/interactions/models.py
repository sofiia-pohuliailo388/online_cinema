"""SQLAlchemy models for movie interactions (owner: P5)."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.models import Base


class MovieReaction(Base):
    """A user's like or dislike reaction to a movie."""

    __tablename__ = "movie_reactions"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "movie_id",
            name="uq_movie_reactions_user_movie",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"))

    is_like: Mapped[bool] = mapped_column(Boolean, nullable=False)


class Comment(Base):
    """A user's comment on a movie or a reply to another comment."""

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"))

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("comments.id", ondelete="SET NULL"),
        nullable=True,
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class CommentLike(Base):
    """A user's like on a comment."""

    __tablename__ = "comment_likes"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "comment_id",
            name="uq_comment_likes_user_comment",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    comment_id: Mapped[int] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"))


class Rating(Base):
    """A user's rating of a movie on a 1-10 scale."""

    __tablename__ = "ratings"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "movie_id",
            name="uq_ratings_user_movie",
        ),
        CheckConstraint(
            "score >= 1 AND score <= 10",
            name="ratings_score_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"))

    score: Mapped[int] = mapped_column(Integer, nullable=False)


class Favorite(Base):
    """A movie added to a user's favorites."""

    __tablename__ = "favorites"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "movie_id",
            name="uq_favorites_user_movie",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"))
