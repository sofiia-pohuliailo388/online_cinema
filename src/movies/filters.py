"""Catalog filtering / sorting / search - CONTRACT used by P5 for favorites (owner: P4).

Usage::

    stmt = select(Movie).join(Favorite).where(Favorite.user_id == user.id)
    stmt = apply_movie_filters(stmt, filters)
"""

from typing import Any

from sqlalchemy import Select


def apply_movie_filters(stmt: Select[Any], filters: Any) -> Select[Any]:
    """Apply filters (year, imdb, genre), sorting (price, year, votes) and search.

    TODO(P4): define ``MovieFilterParams`` (dataclass with Query fields, like
    ``PaginationParams``) and implement this function. Until then it returns ``stmt`` unchanged.
    """
    return stmt
