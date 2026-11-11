"""Movies domain (owner: P4).

Catalog: movies, genres, stars, directors, certifications; moderator CRUD.
Genres are implemented fully as the REFERENCE EXAMPLE for the whole team:
copy the same layers (models -> schemas -> service -> router -> tests) in your domain.

Public contract for other domains: ``src.movies.filters.apply_movie_filters``.
"""
