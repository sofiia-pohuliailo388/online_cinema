from typing import Any, Optional
from fastapi import Query
from sqlalchemy import Select, or_
from src.movies.models import Genre, Movie, Star, Director


class MovieFilterParams:
    """Parameters for filtering, searching, and sorting movies in the catalog.
    Designed similarly to PaginationParams as a FastAPI dependency container.
    """

    def __init__(
        self,
        search: Optional[str] = Query(None, description="Search movies by title, description, star, or director"),
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


def apply_movie_filters(stmt: Select[Any], filters: MovieFilterParams) -> Select[Any]:
    """Apply filters (year, imdb, genre), sorting (price, year, votes) and search
    (with ilike on name, description, and joins on stars/directors).

    Implements the official team contract used across domains (e.g., favorites).
    """
    if filters.search:
        search_query = f"%{filters.search}%"
        stmt = (
            stmt.outerjoin(Movie.stars)
            .outerjoin(Movie.directors)
            .where(
                or_(
                    Movie.name.ilike(search_query),
                    Movie.description.ilike(search_query),
                    Star.name.ilike(search_query),
                    Director.name.ilike(search_query),
                )
            )
            .distinct(Movie.id)
        )

    if filters.genre_id is not None:
        stmt = stmt.where(Movie.genres.any(Genre.id == filters.genre_id))

    if filters.year_from is not None:
        stmt = stmt.where(Movie.year >= filters.year_from)
    if filters.year_to is not None:
        stmt = stmt.where(Movie.year <= filters.year_to)

    if filters.min_imdb is not None:
        stmt = stmt.where(Movie.imdb >= filters.min_imdb)

    sort_column_map = {
        "year": Movie.year,
        "imdb": Movie.imdb,
        "price": Movie.price,
        "votes": Movie.votes,
        "name": Movie.name,
    }

    sort_by = filters.sort_by or "year"
    sort_order = filters.sort_order or "desc"

    sort_col = sort_column_map.get(sort_by, Movie.year)

    if sort_order == "asc":
        stmt = stmt.order_by(sort_col.asc())
    else:
        stmt = stmt.order_by(sort_col.desc())

    return stmt