"""Compatibility exports for interaction services."""

from src.interactions.services.comments import (
    create_comment,
    like_comment,
    list_comments,
)
from src.interactions.services.favorites import (
    add_favorite,
    list_favorites,
    remove_favorite,
)
from src.interactions.services.ratings import create_rating, get_average_rating
from src.interactions.services.reactions import (
    get_movie_likes_count,
    toggle_movie_reaction,
)


async def get_movie_interaction_stats(db, movie_id: int):
    """Return average rating and likes count for a movie."""
    average_rating = await get_average_rating(db, movie_id)
    likes_count = await get_movie_likes_count(db, movie_id)

    return {
        "movie_id": movie_id,
        "average_rating": average_rating,
        "likes_count": likes_count,
    }


__all__ = [
    "add_favorite",
    "create_comment",
    "create_rating",
    "get_movie_interaction_stats",
    "like_comment",
    "list_comments",
    "list_favorites",
    "remove_favorite",
    "toggle_movie_reaction",
]
