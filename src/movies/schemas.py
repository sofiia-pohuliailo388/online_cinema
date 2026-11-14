"""Pydantic schemas of the movies domain.

Naming convention for every entity ``X``:
- ``XBase``   - shared fields
- ``XCreate`` - request body for POST
- ``XUpdate`` - request body for PATCH (all fields optional)
- ``XRead``   - response model (``from_attributes=True``)

"""

from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


# --- GENRE SCHEMAS ---


class GenreBase(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Action"])


class GenreCreate(GenreBase):
    pass


class GenreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class GenreRead(GenreBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movies_count: int = 0


# --- CERTIFICATION SCHEMAS ---


class CertificationBase(BaseModel):
    name: str = Field(min_length=1, max_length=50, examples=["PG-13"])


class CertificationCreate(CertificationBase):
    pass


class CertificationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)


class CertificationRead(CertificationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


# --- STAR SCHEMAS ---


class StarBase(BaseModel):
    name: str = Field(min_length=1, max_length=255, examples=["Keanu Reeves"])


class StarCreate(StarBase):
    pass


class StarUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)


class StarRead(StarBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


# --- DIRECTOR SCHEMAS ---


class DirectorBase(BaseModel):
    name: str = Field(min_length=1, max_length=255, examples=["Christopher Nolan"])


class DirectorCreate(DirectorBase):
    pass


class DirectorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)


class DirectorRead(DirectorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


# --- MOVIE SCHEMAS ---


class MovieRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    average_rating: float | None = Field(
        default=None, description="Average user rating from ratings table"
    )
    likes_count: int = Field(default=0, description="Total likes count from movie_reactions")
    meta_score: float | None = None
    gross: Decimal | None = None
    description: str
    price: Decimal
    certification: CertificationRead
    genres: list[GenreRead] = []
    stars: list[StarRead] = []
    directors: list[DirectorRead] = []


class MovieCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: float | None = None
    gross: Decimal | None = None
    description: str
    price: Decimal
    certification_id: int
    genre_ids: list[int] = []
    star_ids: list[int] = []
    director_ids: list[int] = []


class MovieUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    year: int | None = None
    time: int | None = None
    imdb: float | None = None
    votes: int | None = None
    meta_score: float | None = None
    gross: Decimal | None = None
    description: str | None = None
    price: Decimal | None = None
    certification_id: int | None = None
    genre_ids: list[int] | None = None
    star_ids: list[int] | None = None
    director_ids: list[int] | None = None
