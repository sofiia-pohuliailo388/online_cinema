"""Movie domain models: Genre, Star, Director, Certification, and Movie.

Owner: P4 (Movies)
"""

import uuid as uuid_pkg
from uuid import UUID
from decimal import Decimal
from sqlalchemy import (
    Table,
    Column,
    ForeignKey,
    String,
    Integer,
    Float,
    Text,
    Numeric,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.models import Base, TimestampMixin

# Association tables for many-to-many relationships
movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)

movie_directors = Table(
    "movie_directors",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "director_id", Integer, ForeignKey("directors.id", ondelete="CASCADE"), primary_key=True
    ),
)

movie_stars = Table(
    "movie_stars",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("star_id", Integer, ForeignKey("stars.id", ondelete="CASCADE"), primary_key=True),
)


class Genre(Base, TimestampMixin):
    """Genre model representing movie categories."""

    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie", secondary=movie_genres, back_populates="genres"
    )


class Star(Base, TimestampMixin):
    """Star (actor/actress) model representing movie cast members."""

    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie", secondary=movie_stars, back_populates="stars"
    )


class Director(Base, TimestampMixin):
    """Director model representing movie directors."""

    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie", secondary=movie_directors, back_populates="directors"
    )


class Certification(Base, TimestampMixin):
    """Certification model representing age or content ratings (e.g. PG-13, R)."""

    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship("Movie", back_populates="certification")


class Movie(Base, TimestampMixin):
    """Movie model representing main catalog data."""

    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(
        Uuid, default=uuid_pkg.uuid4, unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    gross: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id"), nullable=False)

    certification: Mapped["Certification"] = relationship("Certification", back_populates="movies")
    genres: Mapped[list["Genre"]] = relationship(
        "Genre", secondary=movie_genres, back_populates="movies"
    )
    directors: Mapped[list["Director"]] = relationship(
        "Director", secondary=movie_directors, back_populates="movies"
    )
    stars: Mapped[list["Star"]] = relationship(
        "Star", secondary=movie_stars, back_populates="movies"
    )

    __table_args__ = (UniqueConstraint("name", "year", "time", name="uq_movie_name_year_time"),)
