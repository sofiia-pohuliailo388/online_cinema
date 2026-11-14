"""HTTP endpoints of the movies domain.

Layer rules (same for every domain):
- A router only: reads input, checks access via dependencies, calls ONE service

  function, converts the result to a ``*Read`` schema.
- No SQL, no ``commit()``, no ``HTTPException`` here.

- The endpoint docstring becomes its description in Swagger - write it for API users.

- Declare possible errors in ``responses=`` so they appear in Swagger.

"""

from typing import Annotated

from fastapi import APIRouter, Depends, status, Response

from src.accounts.dependencies import ModeratorUser
from src.core.database import DbSession
from src.core.exceptions import ErrorResponse
from src.core.pagination import Page, PaginationParams
from src.movies import service
from src.movies.filters import MovieFilterParams
from src.movies.schemas import (
    GenreCreate,
    GenreRead,
    GenreUpdate,
    MovieCreate,
    MovieRead,
    MovieUpdate,
)

router = APIRouter(tags=["movies"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Not found"}}
CONFLICT = {409: {"model": ErrorResponse, "description": "Already exists"}}
MODERATOR_ONLY = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Moderator or admin only"},
}


# --- GENRES ENDPOINTS ---


@router.get("/genres")
async def list_genres(
    db: DbSession, pagination: Annotated[PaginationParams, Depends()]
) -> Page[GenreRead]:
    """List all genres, ordered by name."""
    items, total = await service.list_genres(db, pagination)
    return Page[GenreRead].create(
        [GenreRead.model_validate(item) for item in items], total, pagination
    )


@router.get("/genres/{genre_id}", responses=NOT_FOUND)
async def get_genre(genre_id: int, db: DbSession) -> GenreRead:
    """Get one genre by id."""
    genre = await service.get_genre(db, genre_id)
    return GenreRead.model_validate(genre)


@router.get("/genres/{genre_id}/movies", responses=NOT_FOUND)
async def list_genre_movies(
    genre_id: int,
    db: DbSession,
    filter_params: Annotated[MovieFilterParams, Depends()],
    pagination: Annotated[PaginationParams, Depends()],
) -> Page[MovieRead]:
    """List all movies belonging to a specific genre."""
    await service.get_genre(db, genre_id)

    filter_params.genre_id = genre_id
    items, total = await service.list_movies(db, filter_params, pagination)
    return Page[MovieRead].create(
        [MovieRead.model_validate(item) for item in items], total, pagination
    )


@router.post(
    "/genres", status_code=status.HTTP_201_CREATED, responses={**MODERATOR_ONLY, **CONFLICT}
)
async def create_genre(data: GenreCreate, db: DbSession, _: ModeratorUser) -> GenreRead:
    """Create a genre. Moderator or admin only."""
    genre = await service.create_genre(db, data)
    return GenreRead.model_validate(genre)


@router.patch("/genres/{genre_id}", responses={**MODERATOR_ONLY, **NOT_FOUND, **CONFLICT})
async def update_genre(
    genre_id: int, data: GenreUpdate, db: DbSession, _: ModeratorUser
) -> GenreRead:
    """Rename a genre. Moderator or admin only."""
    genre = await service.update_genre(db, genre_id, data)
    return GenreRead.model_validate(genre)


@router.delete(
    "/genres/{genre_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**MODERATOR_ONLY, **NOT_FOUND},
)
async def delete_genre(genre_id: int, db: DbSession, _: ModeratorUser) -> None:
    """Delete a genre. Moderator or admin only."""
    await service.delete_genre(db, genre_id)


# --- MOVIES ENDPOINTS ---


@router.get("/movies")
async def list_movies(
    db: DbSession,
    filter_params: Annotated[MovieFilterParams, Depends()],
    pagination: Annotated[PaginationParams, Depends()],
) -> Page[MovieRead]:
    """Retrieve a paginated and filtered list of movies."""
    items, total = await service.list_movies(db, filter_params, pagination)
    return Page[MovieRead].create(
        [MovieRead.model_validate(item) for item in items], total, pagination
    )


@router.get("/movies/{movie_id}", responses=NOT_FOUND)
async def get_movie(movie_id: int, db: DbSession) -> MovieRead:
    """Retrieve a single movie by its ID with all relations loaded."""
    movie = await service.get_movie(db, movie_id)
    return MovieRead.model_validate(movie)


@router.post(
    "/movies",
    status_code=status.HTTP_201_CREATED,
    responses={**MODERATOR_ONLY, **CONFLICT, **NOT_FOUND},
)
async def create_movie(data: MovieCreate, db: DbSession, _: ModeratorUser) -> MovieRead:
    """Create a new movie. Moderator or admin only."""
    movie = await service.create_movie(db, data)
    return MovieRead.model_validate(movie)


@router.patch("/movies/{movie_id}", responses={**MODERATOR_ONLY, **NOT_FOUND, **CONFLICT})
async def update_movie(
    movie_id: int, data: MovieUpdate, db: DbSession, _: ModeratorUser
) -> MovieRead:
    """Update an existing movie. Moderator or admin only."""
    movie = await service.update_movie(db, movie_id, data)
    return MovieRead.model_validate(movie)


@router.delete(
    "/movies/{movie_id}",
    responses={**MODERATOR_ONLY, **NOT_FOUND, **CONFLICT},
)
async def delete_movie(
    movie_id: int, db: DbSession, _: ModeratorUser
) -> dict | None:
    """Delete a movie. Moderator or admin only."""
    result = await service.delete_movie(db, movie_id)
    if result:
        return result
    return Response(status_code=status.HTTP_204_NO_CONTENT)
