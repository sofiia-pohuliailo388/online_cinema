from typing import Any, Optional
from fastapi import Query
from sqlalchemy import Select
from src.movies.models import Movie


"""Catalog filtering / sorting / search - CONTRACT used by P5 for favorites (owner: P4).

Usage::

    stmt = select(Movie).join(Favorite).where(Favorite.user_id == user.id)
    stmt = apply_movie_filters(stmt, filters)
"""


class MovieFilterParams:
    """Parameters for filtering, searching, and sorting movies in the catalog.
    Designed similarly to PaginationParams as a FastAPI dependency container.
    """

    def __init__(
        self,
        search: Optional[str] = Query(None, description="Search movies by title"),
        genre_id: Optional[int] = Query(None, description="Filter movies by genre ID"),
        year_from: Optional[int] = Query(
            None, description="Filter movies released from this year onward"
        ),
        year_to: Optional[int] = Query(None, description="Filter movies released up to this year"),
        min_imdb: Optional[float] = Query(
            None, description="Filter movies with a minimum IMDb rating"
        ),
        sort_by: Optional[str] = Query(
            "year", description="Field to sort by: year, imdb, price, votes, or name"
        ),
        sort_order: Optional[str] = Query(
            "desc", description="Sorting order direction: asc or desc"
        ),
    ):
        self.search = search
        self.genre_id = genre_id
        self.year_from = year_from
        self.year_to = year_to
        self.min_imdb = min_imdb
        self.sort_by = sort_by
        self.sort_order = sort_order


def apply_movie_filters(stmt: Select[Any], filters: Any) -> Select[Any]:
    """Apply filters (year, imdb, genre), sorting (price, year, votes) and search.

    Implements the official team contract used across domains (e.g., favorites).
    """
    if getattr(filters, "search", None):
        stmt = stmt.where(Movie.name.ilike(f"%{filters.search}%"))

    if getattr(filters, "genre_id", None) is not None:
        stmt = stmt.where(Movie.genres.any(id=filters.genre_id))

    if getattr(filters, "year_from", None) is not None:
        stmt = stmt.where(Movie.year >= filters.year_from)
    if getattr(filters, "year_to", None) is not None:
        stmt = stmt.where(Movie.year <= filters.year_to)

    if getattr(filters, "min_imdb", None) is not None:
        stmt = stmt.where(Movie.imdb >= filters.min_imdb)

    sort_column_map = {
        "year": Movie.year,
        "imdb": Movie.imdb,
        "price": Movie.price,
        "votes": Movie.votes,
        "name": Movie.name,
    }

    sort_by = getattr(filters, "sort_by", "year")
    sort_order = getattr(filters, "sort_order", "desc")

    sort_col = sort_column_map.get(sort_by, Movie.year)

    if sort_order == "asc":
        stmt = stmt.order_by(sort_col.asc())
    else:
        stmt = stmt.order_by(sort_col.desc())

    return stmt
