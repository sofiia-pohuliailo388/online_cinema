from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from movies.schemas import GenreRead


class CartItemCreateSchema(BaseModel):
    movie_id: int


class CartItemReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    movie_id: int
    name: str
    price: Decimal
    genres: list[GenreRead]
    year: int
    added_at: datetime


class CartReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cart_items: list[CartItemReadSchema]
