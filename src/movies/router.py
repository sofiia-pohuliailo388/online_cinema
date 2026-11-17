"""HTTP endpoints of the movies domain.

Layer rules (same for every domain):
- A router only: reads input, checks access via dependencies, calls ONE service

  function, converts the result to a ``*Read`` schema.
- No SQL, no ``commit()``, no ``HTTPException`` here.

- The endpoint docstring becomes its description in Swagger - write it for API users.

- Declare possible errors in ``responses=`` so they appear in Swagger.

"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse

from src.accounts.dependencies import ModeratorUser
from src.core.database import DbSession
from src.core.exceptions import ErrorResponse, Responses
from src.core.pagination import Page, PaginationParams
from src.movies import service
from src.movies.filters import MovieFilterParams
from src.movies.schemas import (
    CertificationCreate,
    CertificationRead,
    CertificationUpdate,
    DirectorCreate,
    DirectorRead,
    DirectorUpdate,
    GenreCreate,
    GenreRead,
    GenreUpdate,
    MovieCreate,
    MovieRead,
    MovieUpdate,
    StarCreate,
    StarRead,
    StarUpdate,
)

router = APIRouter(tags=["movies"])

NOT_FOUND: Responses = {404: {"model": ErrorResponse, "description": "Not found"}}
CONFLICT: Responses = {409: {"model": ErrorResponse, "description": "Already exists"}}
MODERATOR_ONLY: Responses = {
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
async def delete_movie(movie_id: int, db: DbSession, _: ModeratorUser) -> Response:
    """Delete a movie. Moderator or admin only.

    Returns 204, or 200 with ``{"warning": ...}`` if the movie was in some users' carts.
    """
    result = await service.delete_movie(db, movie_id)
    if result:
        return JSONResponse(content=result)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- STARS ENDPOINTS ---


@router.get("/stars")
async def list_stars(
    db: DbSession, pagination: Annotated[PaginationParams, Depends()]
) -> Page[StarRead]:
    """List all stars (actors), ordered by name."""
    items, total = await service.list_stars(db, pagination)
    return Page[StarRead].create(
        [StarRead.model_validate(item) for item in items], total, pagination
    )


@router.get("/stars/{star_id}", responses=NOT_FOUND)
async def get_star(star_id: int, db: DbSession) -> StarRead:
    """Get one star by id."""
    star = await service.get_star(db, star_id)
    return StarRead.model_validate(star)


@router.post(
    "/stars", status_code=status.HTTP_201_CREATED, responses={**MODERATOR_ONLY, **CONFLICT}
)
async def create_star(data: StarCreate, db: DbSession, _: ModeratorUser) -> StarRead:
    """Create a star. Moderator or admin only."""
    star = await service.create_star(db, data)
    return StarRead.model_validate(star)


@router.patch("/stars/{star_id}", responses={**MODERATOR_ONLY, **NOT_FOUND, **CONFLICT})
async def update_star(
    star_id: int, data: StarUpdate, db: DbSession, _: ModeratorUser
) -> StarRead:
    """Rename a star. Moderator or admin only."""
    star = await service.update_star(db, star_id, data)
    return StarRead.model_validate(star)


@router.delete(
    "/stars/{star_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**MODERATOR_ONLY, **NOT_FOUND},
)
async def delete_star(star_id: int, db: DbSession, _: ModeratorUser) -> None:
    """Delete a star (it is also removed from its movies). Moderator or admin only."""
    await service.delete_star(db, star_id)


# --- DIRECTORS ENDPOINTS ---


@router.get("/directors")
async def list_directors(
    db: DbSession, pagination: Annotated[PaginationParams, Depends()]
) -> Page[DirectorRead]:
    """List all directors, ordered by name."""
    items, total = await service.list_directors(db, pagination)
    return Page[DirectorRead].create(
        [DirectorRead.model_validate(item) for item in items], total, pagination
    )


@router.get("/directors/{director_id}", responses=NOT_FOUND)
async def get_director(director_id: int, db: DbSession) -> DirectorRead:
    """Get one director by id."""
    director = await service.get_director(db, director_id)
    return DirectorRead.model_validate(director)


@router.post(
    "/directors", status_code=status.HTTP_201_CREATED, responses={**MODERATOR_ONLY, **CONFLICT}
)
async def create_director(data: DirectorCreate, db: DbSession, _: ModeratorUser) -> DirectorRead:
    """Create a director. Moderator or admin only."""
    director = await service.create_director(db, data)
    return DirectorRead.model_validate(director)


@router.patch(
    "/directors/{director_id}", responses={**MODERATOR_ONLY, **NOT_FOUND, **CONFLICT}
)
async def update_director(
    director_id: int, data: DirectorUpdate, db: DbSession, _: ModeratorUser
) -> DirectorRead:
    """Rename a director. Moderator or admin only."""
    director = await service.update_director(db, director_id, data)
    return DirectorRead.model_validate(director)


@router.delete(
    "/directors/{director_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**MODERATOR_ONLY, **NOT_FOUND},
)
async def delete_director(director_id: int, db: DbSession, _: ModeratorUser) -> None:
    """Delete a director (they are also removed from their movies). Moderator or admin only."""
    await service.delete_director(db, director_id)


# --- CERTIFICATIONS ENDPOINTS ---


@router.get("/certifications")
async def list_certifications(
    db: DbSession, pagination: Annotated[PaginationParams, Depends()]
) -> Page[CertificationRead]:
    """List all certifications (e.g. PG-13, R), ordered by name."""
    items, total = await service.list_certifications(db, pagination)
    return Page[CertificationRead].create(
        [CertificationRead.model_validate(item) for item in items], total, pagination
    )


@router.get("/certifications/{certification_id}", responses=NOT_FOUND)
async def get_certification(certification_id: int, db: DbSession) -> CertificationRead:
    """Get one certification by id."""
    certification = await service.get_certification(db, certification_id)
    return CertificationRead.model_validate(certification)


@router.post(
    "/certifications",
    status_code=status.HTTP_201_CREATED,
    responses={**MODERATOR_ONLY, **CONFLICT},
)
async def create_certification(
    data: CertificationCreate, db: DbSession, _: ModeratorUser
) -> CertificationRead:
    """Create a certification. Moderator or admin only."""
    certification = await service.create_certification(db, data)
    return CertificationRead.model_validate(certification)


@router.patch(
    "/certifications/{certification_id}",
    responses={**MODERATOR_ONLY, **NOT_FOUND, **CONFLICT},
)
async def update_certification(
    certification_id: int, data: CertificationUpdate, db: DbSession, _: ModeratorUser
) -> CertificationRead:
    """Rename a certification. Moderator or admin only."""
    certification = await service.update_certification(db, certification_id, data)
    return CertificationRead.model_validate(certification)


@router.delete(
    "/certifications/{certification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**MODERATOR_ONLY, **NOT_FOUND, **CONFLICT},
)
async def delete_certification(certification_id: int, db: DbSession, _: ModeratorUser) -> None:
    """Delete a certification that no movie uses (otherwise 409). Moderator or admin only."""
    await service.delete_certification(db, certification_id)
