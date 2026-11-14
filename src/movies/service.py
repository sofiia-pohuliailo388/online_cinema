"""Business logic of the movies domain.

Layer rules (same for every domain):
- Functions take ``db: AsyncSession`` as the first argument.

- All SQL queries and ``commit()`` happen here, never in routers.

- Errors are raised as ``src.core.exceptions`` (NotFoundError, ConflictError, ...).

- Return ORM objects; converting to schemas is the router's job.

"""

from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.cart.models import CartItem
from src.orders.models import OrderItem, Order, StatusEnum
from src.core.exceptions import ConflictError, NotFoundError
from src.core.pagination import PaginationParams, paginate
from src.movies.models import Genre, Movie, Star, Director, Certification
from src.interactions.models import MovieReaction, Rating
from src.movies.schemas import (
    GenreCreate,
    GenreUpdate,
    MovieCreate,
    MovieUpdate,
    DirectorUpdate,
    StarCreate,
    StarUpdate,
    DirectorCreate,
    CertificationCreate,
    CertificationUpdate,
)
from src.movies.filters import MovieFilterParams, apply_movie_filters


# --- GENRES SERVICE ---


async def list_genres(db: AsyncSession, pagination: PaginationParams) -> tuple[list[Any], int]:
    """Return a page of genres ordered by name with movie counts and the total count."""
    stmt = (
        select(
            Genre,
            func.count(Movie.id).label("movies_count"),
        )
        .outerjoin(Genre.movies)
        .group_by(Genre.id)
        .order_by(Genre.name)
    )

    items, total = await paginate(db, stmt, pagination)

    processed_genres = []
    for row in items:
        genre = row[0]
        genre.movies_count = row[1]
        processed_genres.append(genre)

    return processed_genres, total


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
    avg_rating_subq = (
        select(func.coalesce(func.avg(Rating.score), 0.0))
        .where(Rating.movie_id == Movie.id)
        .scalar_subquery()
    )

    likes_count_subq = (
        select(func.count(MovieReaction.id))
        .where(MovieReaction.movie_id == Movie.id, MovieReaction.is_like.is_(True))
        .scalar_subquery()
    )

    stmt = (
        select(
            Movie,
            avg_rating_subq.label("average_rating"),
            likes_count_subq.label("likes_count"),
        )
        .options(
            selectinload(Movie.genres),
            selectinload(Movie.stars),
            selectinload(Movie.directors),
            selectinload(Movie.certification),
        )
        .where(Movie.id == movie_id)
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
    avg_rating_subq = (
        select(func.coalesce(func.avg(Rating.score), 0.0))
        .where(Rating.movie_id == Movie.id)
        .scalar_subquery()
    )

    likes_count_subq = (
        select(func.count(MovieReaction.id))
        .where(MovieReaction.movie_id == Movie.id, MovieReaction.is_like.is_(True))
        .scalar_subquery()
    )

    stmt = (
        select(
            Movie,
            avg_rating_subq.label("average_rating"),
            likes_count_subq.label("likes_count"),
        )
        .options(
            selectinload(Movie.genres),
            selectinload(Movie.stars),
            selectinload(Movie.directors),
            selectinload(Movie.certification),
        )
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


async def delete_movie(db: AsyncSession, movie_id: int) -> dict | None:
    """Delete a movie with business safety checks:
    - Raises ConflictError (409) if the movie has been purchased (order status is PAID).
    - Returns a warning message if the movie is present in user carts.
    """
    movie = await get_movie(db, movie_id)

    paid_purchases_count = await db.scalar(
        select(func.count(OrderItem.id))
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            OrderItem.movie_id == movie_id,
            Order.status == StatusEnum.PAID,
        )
    )
    if paid_purchases_count and paid_purchases_count > 0:
        raise ConflictError("Cannot delete a movie that has been purchased by users.")

    cart_count = await db.scalar(
        select(func.count(CartItem.id)).where(CartItem.movie_id == movie_id)
    )
    warning = None
    if cart_count and cart_count > 0:
        warning = "Warning: This movie is currently in some users' carts."

    await db.delete(movie)
    await db.commit()

    return {"warning": warning} if warning else None


# --- STARS CRUD ---
async def list_stars(db: AsyncSession, pagination: PaginationParams) -> tuple[list[Star], int]:
    stmt = select(Star).order_by(Star.name)
    return await paginate(db, stmt, pagination)


async def get_star(db: AsyncSession, star_id: int) -> Star:
    star = await db.get(Star, star_id)
    if not star:
        raise NotFoundError(f"Star with id {star_id} not found")
    return star


async def create_star(db: AsyncSession, data: StarCreate) -> Star:
    existing = await db.scalar(select(Star).where(Star.name == data.name))
    if existing:
        raise ConflictError(f"Star '{data.name}' already exists")
    star = Star(**data.model_dump())
    db.add(star)
    await db.commit()
    await db.refresh(star)
    return star


async def update_star(db: AsyncSession, star_id: int, data: StarUpdate) -> Star:
    star = await get_star(db, star_id)
    if data.name is not None and data.name != star.name:
        existing = await db.scalar(select(Star).where(Star.name == data.name))
        if existing:
            raise ConflictError(f"Star '{data.name}' already exists")
        star.name = data.name
    await db.commit()
    await db.refresh(star)
    return star


async def delete_star(db: AsyncSession, star_id: int) -> None:
    star = await get_star(db, star_id)
    await db.delete(star)
    await db.commit()


# --- DIRECTORS CRUD ---
async def list_directors(
    db: AsyncSession, pagination: PaginationParams
) -> tuple[list[Director], int]:
    stmt = select(Director).order_by(Director.name)
    return await paginate(db, stmt, pagination)


async def get_director(db: AsyncSession, director_id: int) -> Director:
    director = await db.get(Director, director_id)
    if not director:
        raise NotFoundError(f"Director with id {director_id} not found")
    return director


async def create_director(db: AsyncSession, data: DirectorCreate) -> Director:
    existing = await db.scalar(select(Director).where(Director.name == data.name))
    if existing:
        raise ConflictError(f"Director '{data.name}' already exists")
    director = Director(**data.model_dump())
    db.add(director)
    await db.commit()
    await db.refresh(director)
    return director


async def update_director(db: AsyncSession, director_id: int, data: DirectorUpdate) -> Director:
    director = await get_director(db, director_id)
    if data.name is not None and data.name != director.name:
        existing = await db.scalar(select(Director).where(Director.name == data.name))
        if existing:
            raise ConflictError(f"Director '{data.name}' already exists")
        director.name = data.name
    await db.commit()
    await db.refresh(director)
    return director


async def delete_director(db: AsyncSession, director_id: int) -> None:
    director = await get_director(db, director_id)
    await db.delete(director)
    await db.commit()


# --- CERTIFICATIONS CRUD ---
async def list_certifications(
    db: AsyncSession, pagination: PaginationParams
) -> tuple[list[Certification], int]:
    stmt = select(Certification).order_by(Certification.name)
    return await paginate(db, stmt, pagination)


async def get_certification(db: AsyncSession, certification_id: int) -> Certification:
    cert = await db.get(Certification, certification_id)
    if not cert:
        raise NotFoundError(f"Certification with id {certification_id} not found")
    return cert


async def create_certification(db: AsyncSession, data: CertificationCreate) -> Certification:
    existing = await db.scalar(select(Certification).where(Certification.name == data.name))
    if existing:
        raise ConflictError(f"Certification '{data.name}' already exists")
    cert = Certification(**data.model_dump())
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    return cert


async def update_certification(
    db: AsyncSession, certification_id: int, data: CertificationUpdate
) -> Certification:
    cert = await get_certification(db, certification_id)
    if data.name is not None and data.name != cert.name:
        existing = await db.scalar(select(Certification).where(Certification.name == data.name))
        if existing:
            raise ConflictError(f"Certification '{data.name}' already exists")
        cert.name = data.name
    await db.commit()
    await db.refresh(cert)
    return cert


async def delete_certification(db: AsyncSession, certification_id: int) -> None:
    cert = await get_certification(db, certification_id)
    await db.delete(cert)
    await db.commit()
