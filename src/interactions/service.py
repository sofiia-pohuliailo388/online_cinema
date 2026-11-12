"""Compatibility exports for interaction services."""

from src.interactions.services.comments import (
    create_comment,
    like_comment,
    list_comments,
)
from src.interactions.services.favorites import (
    add_favorite,
    remove_favorite,
)
from src.interactions.services.ratings import create_rating
from src.interactions.services.reactions import toggle_movie_reaction

__all__ = [
    "add_favorite",
    "create_comment",
    "create_rating",
    "like_comment",
    "list_comments",
    "remove_favorite",
    "toggle_movie_reaction",
]
