"""SQLAlchemy models of the movies domain (spec, section 2).

TODO(P4): Movie, Star, Director, Certification and association tables
(movie_genres, movie_stars, movie_directors).
"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.models import Base


class Genre(Base):
    """Movie genre, e.g. "Action". Many-to-many with Movie via ``movie_genres``."""

    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
