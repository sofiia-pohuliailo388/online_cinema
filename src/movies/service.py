"""Business logic of the movies domain.

Layer rules (same for every domain):
- Functions take ``db: AsyncSession`` as the first argument.

- All SQL queries and ``commit()`` happen here, never in routers.

- Errors are raised as ``src.core.exceptions`` (NotFoundError, ConflictError, ...).

- Return ORM objects; converting to schemas is the router's job.

"""

from typing import Any
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ConflictError, NotFoundError
from src.core.pagination import PaginationParams, paginate
from src.movies.models import Genre, Movie, Star, Director
from src.interactions.models import MovieReaction, Rating
from src.movies.schemas import (
    GenreCreate,
    GenreUpdate,
    MovieCreate,
    MovieUpdate,
)
from src.movies.filters import MovieFilterParams, apply_movie_filters


# --- GENRES SERVICE ---


async def list_genres(db: AsyncSession, pagination: PaginationParams) -> tuple[list[Any], int]:
    """Return a page of genres ordered by name and the total count."""
    stmt = select(Genre).order_by(Genre.name)
    return await paginate(db, stmt, pagination)


async def get_genre(db: AsyncSession, genre_id: int) -> Genre:
    """Return a genre by id.

    Raises:
        NotFoundError: genre does not exist.
    """
    genre = await db.get(Genre, genre_id)
    if genre is None:
        raise NotFoundError(f"Genre with id={genre_id} not found")
    return genre


async def _ensure_name_is_free(db: AsyncSession, name: str) -> None:
    exists = await db.scalar(select(Genre.id).where(Genre.name == name))
    if exists is not None:
        raise ConflictError(f"Genre '{name}' already exists")


async def create_genre(db: AsyncSession, data: GenreCreate) -> Genre:
    """Create a genre with uniqueness check before commit.

    Raises:
        ConflictError: a genre with the same name already exists.
    """
    if not data.name:
        raise ConflictError("Genre name cannot be empty")

    await _ensure_name_is_free(db, data.name)
    genre = Genre(**data.model_dump())
    db.add(genre)
    await db.commit()
    await db.refresh(genre)
    return genre


async def update_genre(db: AsyncSession, genre_id: int, data: GenreUpdate) -> Genre:
    """Partially update a genre, preventing null values for name.

    Raises:
        NotFoundError: genre does not exist.
        ConflictError: new name is taken or null.
    """
    genre = await get_genre(db, genre_id)
    changes = data.model_dump(exclude_unset=True)

    if "name" in changes:
        if changes["name"] is None:
            raise ConflictError("Genre name cannot be null")
        if changes["name"] != genre.name:
            await _ensure_name_is_free(db, changes["name"])

    for field, value in changes.items():
        setattr(genre, field, value)

    await db.commit()
    await db.refresh(genre)
    return genre


async def delete_genre(db: AsyncSession, genre_id: int) -> None:
    """Delete a genre.

    Raises:
        NotFoundError: genre does not exist.
    """
    genre = await get_genre(db, genre_id)
    await db.delete(genre)
    await db.commit()


# --- MOVIES SERVICE ---


async def get_movie(db: AsyncSession, movie_id: int) -> Movie:
    """Retrieve a single movie by its ID with all relations and statistics loaded.

    Raises:
        NotFoundError: if the movie does not exist.
    """
    stmt = (
        select(
            Movie,
            func.coalesce(func.avg(Rating.score), 0.0).label("average_rating"),
            func.count(case((MovieReaction.is_like.is_(True), 1), else_=None)).label("likes_count"),
        )
        .outerjoin(Rating, Rating.movie_id == Movie.id)
        .outerjoin(MovieReaction, MovieReaction.movie_id == Movie.id)
        .options(
            selectinload(Movie.genres),
            selectinload(Movie.stars),
            selectinload(Movie.directors),
            selectinload(Movie.certification),
        )
        .where(Movie.id == movie_id)
        .group_by(Movie.id)
    )
    result = await db.execute(stmt)
    row = result.first()

    if not row:
        raise NotFoundError(f"Movie with ID {movie_id} not found")

    movie = row[0]
    movie.average_rating = float(row[1]) if row[1] is not None else 0.0
    movie.likes_count = int(row[2]) if row[2] is not None else 0

    return movie


async def list_movies(
    db: AsyncSession, filter_params: MovieFilterParams, pagination_params: PaginationParams
) -> tuple[list[Any], int]:
    """Retrieve a paginated, filtered, and searched list of movies with statistics and relations."""
    stmt = (
        select(
            Movie,
            func.coalesce(func.avg(Rating.score), 0.0).label("average_rating"),
            func.count(case((MovieReaction.is_like.is_(True), 1), else_=None)).label("likes_count"),
        )
        .outerjoin(Rating, Rating.movie_id == Movie.id)
        .outerjoin(MovieReaction, MovieReaction.movie_id == Movie.id)
        .options(
            selectinload(Movie.genres),
            selectinload(Movie.stars),
            selectinload(Movie.directors),
            selectinload(Movie.certification),
        )
        .group_by(Movie.id)
    )

    stmt = apply_movie_filters(stmt, filter_params)

    items, total = await paginate(db, stmt, pagination_params)

    processed_items = []
    for row in items:
        if isinstance(row, tuple):
            movie = row[0]
            movie.average_rating = float(row[1]) if row[1] is not None else 0.0
            movie.likes_count = int(row[2]) if row[2] is not None else 0
        else:
            movie = row
            movie.average_rating = 0.0
            movie.likes_count = 0
        processed_items.append(movie)

    return processed_items, total


async def create_movie(db: AsyncSession, data: MovieCreate) -> Movie:
    """Create a new movie with related genres, stars, directors, and certification.

    Raises:
        ConflictError: if a movie with the same unique constraints exists.
        NotFoundError: if certification, genres, stars or directors do not exist.
    """
    payload = data.model_dump(exclude={"genre_ids", "star_ids", "director_ids"})

    movie = Movie(**payload)

    if data.genre_ids:
        genres = await db.scalars(select(Genre).where(Genre.id.in_(data.genre_ids)))
        movie.genres = list(genres)

    if data.star_ids:
        stars = await db.scalars(select(Star).where(Star.id.in_(data.star_ids)))
        movie.stars = list(stars)

    if data.director_ids:
        directors = await db.scalars(select(Director).where(Director.id.in_(data.director_ids)))
        movie.directors = list(directors)

    db.add(movie)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise ConflictError(f"Could not create movie: {str(e)}")

    await db.refresh(movie)
    return await get_movie(db, movie.id)


async def update_movie(db: AsyncSession, movie_id: int, data: MovieUpdate) -> Movie:
    """Partially update an existing movie and its relationships.

    Raises:
        NotFoundError: if the movie does not exist.
    """
    movie = await db.get(Movie, movie_id)
    if not movie:
        raise NotFoundError(f"Movie with ID {movie_id} not found")

    changes = data.model_dump(exclude_unset=True)

    genre_ids = changes.pop("genre_ids", None)
    star_ids = changes.pop("star_ids", None)
    director_ids = changes.pop("director_ids", None)

    for field, value in changes.items():
        setattr(movie, field, value)

    if genre_ids is not None:
        genres = await db.scalars(select(Genre).where(Genre.id.in_(genre_ids)))
        movie.genres = list(genres)

    if star_ids is not None:
        stars = await db.scalars(select(Star).where(Star.id.in_(star_ids)))
        movie.stars = list(stars)

    if director_ids is not None:
        directors = await db.scalars(select(Director).where(Director.id.in_(director_ids)))
        movie.directors = list(directors)

    await db.commit()
    return await get_movie(db, movie_id)


async def delete_movie(db: AsyncSession, movie_id: int) -> None:
    """Delete a movie by ID.

    Raises:
        NotFoundError: if the movie does not exist.
    """
    movie = await db.get(Movie, movie_id)
    if not movie:
        raise NotFoundError(f"Movie with ID {movie_id} not found")

    await db.delete(movie)
    await db.commit()
