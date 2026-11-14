"""HTTP endpoints of the movie interactions domain."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from src.accounts.dependencies import CurrentUser
from src.core.database import DbSession
from src.core.pagination import Page, PaginationParams
from src.interactions import service
from src.interactions.schemas import (
    CommentCreate,
    CommentLikeRead,
    CommentRead,
    FavoriteRead,
    MovieInteractionStats,
    MovieReactionCreate,
    MovieReactionRead,
    RatingCreate,
    RatingRead,
)
from src.movies.filters import MovieFilterParams
from src.movies.schemas import MovieRead

router = APIRouter(tags=["interactions"])


@router.post(
    "/reactions",
    response_model=MovieReactionRead | None,
    status_code=status.HTTP_200_OK,
    summary="Toggle a movie like or dislike",
    description=(
        "Creates, changes, or removes the current user's reaction to a movie. "
        "Set is_like to true for a like or false for a dislike. "
        "Sending the same reaction again removes it."
    ),
)
async def toggle_reaction(
    data: MovieReactionCreate,
    db: DbSession,
    user: CurrentUser,
) -> MovieReactionRead | None:
    """Create, change, or remove the current user's movie reaction."""
    reaction = await service.toggle_movie_reaction(
        db=db,
        user_id=user.id,
        movie_id=data.movie_id,
        is_like=data.is_like,
    )
    return reaction


@router.post(
    "/ratings",
    response_model=RatingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a movie rating",
    description=(
        "Creates a new rating or updates the current user's existing rating. "
        "The score must be an integer between 1 and 10."
    ),
)
async def rate_movie(
    data: RatingCreate,
    db: DbSession,
    user: CurrentUser,
) -> RatingRead:
    """Create or update the current user's movie rating."""
    return await service.create_rating(
        db=db,
        user_id=user.id,
        movie_id=data.movie_id,
        score=data.score,
    )


@router.get(
    "/movies/{movie_id}/comments",
    response_model=list[CommentRead],
    summary="List movie comments",
    description=(
        "Returns all comments for the specified movie, "
        "ordered by creation date from newest to oldest."
    ),
)
async def get_movie_comments(
    movie_id: int,
    db: DbSession,
) -> list[CommentRead]:
    """Get comments for a movie."""
    return await service.list_comments(db=db, movie_id=movie_id)


@router.post(
    "/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a comment or reply",
    description=(
        "Creates a new comment or replies to an existing comment. "
        "To create a reply, provide parent_id. "
        "The parent comment must belong to the same movie. "
        "The comment author receives a notification when another user replies."
    ),
)
async def add_comment(
    data: CommentCreate,
    db: DbSession,
    user: CurrentUser,
) -> CommentRead:
    """Create a comment or a reply to another comment."""
    return await service.create_comment(
        db=db,
        user_id=user.id,
        movie_id=data.movie_id,
        text=data.text,
        parent_id=data.parent_id,
    )


@router.post(
    "/comments/{comment_id}/likes",
    response_model=CommentLikeRead | None,
    summary="Toggle a comment like",
    description=(
        "Adds or removes the current user's like on a comment. "
        "Sending the request again removes the existing like. "
        "The comment author receives a notification when another user likes it."
    ),
)
async def toggle_comment_like(
    comment_id: int,
    db: DbSession,
    user: CurrentUser,
) -> CommentLikeRead | None:
    """Add or remove the current user's like on a comment."""
    return await service.like_comment(
        db=db,
        user_id=user.id,
        comment_id=comment_id,
    )


@router.post(
    "/movies/{movie_id}/favorite",
    response_model=FavoriteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a movie to favorites",
    description=(
        "Adds the specified movie to the current user's favorites. "
        "Returns a conflict error if the movie is already in favorites."
    ),
)
async def add_movie_to_favorites(
    movie_id: int,
    db: DbSession,
    user: CurrentUser,
) -> FavoriteRead:
    """Add a movie to the current user's favorites."""
    return await service.add_favorite(
        db=db,
        user_id=user.id,
        movie_id=movie_id,
    )


@router.delete(
    "/movies/{movie_id}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a movie from favorites",
    description=(
        "Removes the specified movie from the current user's favorites. "
        "Returns not found if the movie is not in the favorites list."
    ),
)
async def delete_movie_from_favorites(
    movie_id: int,
    db: DbSession,
    user: CurrentUser,
) -> Response:
    """Remove a movie from the current user's favorites."""
    await service.remove_favorite(
        db=db,
        user_id=user.id,
        movie_id=movie_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/favorites",
    response_model=Page[MovieRead],
    summary="List favorite movies",
    description=(
        "Returns the current user's favorite movies with pagination. "
        "Supports the same search, filtering, and sorting parameters "
        "as the movie catalog."
    ),
)
async def get_favorites(
    db: DbSession,
    user: CurrentUser,
    filters: Annotated[MovieFilterParams, Depends()],
    pagination: Annotated[PaginationParams, Depends()],
) -> Page[MovieRead]:
    """Get the current user's favorite movies with filters and pagination."""
    items, total = await service.list_favorites(
        db=db,
        user_id=user.id,
        filters=filters,
        pagination=pagination,
    )
    return Page[MovieRead].create(
        [MovieRead.model_validate(item) for item in items],
        total,
        pagination,
    )


@router.get(
    "/movies/{movie_id}/interactions/stats",
    response_model=MovieInteractionStats,
    summary="Get movie interaction statistics",
    description=(
        "Returns interaction statistics for the specified movie, "
        "including its average user rating and total number of likes."
    ),
)
async def get_movie_stats(
    movie_id: int,
    db: DbSession,
) -> MovieInteractionStats:
    """Get average rating and likes count for a movie."""
    stats = await service.get_movie_interaction_stats(
        db=db,
        movie_id=movie_id,
    )
    return MovieInteractionStats(**stats)
