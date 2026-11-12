"""Pydantic schemas of the movies domain.

Naming convention for every entity ``X``:
    * ``XBase``   - shared fields
    * ``XCreate`` - request body for POST
    * ``XUpdate`` - request body for PATCH (all fields optional)
    * ``XRead``   - response model (``from_attributes=True``)
"""

from pydantic import BaseModel, ConfigDict, Field


class GenreBase(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Action"])


class GenreCreate(GenreBase):
    pass


class GenreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class GenreRead(GenreBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
