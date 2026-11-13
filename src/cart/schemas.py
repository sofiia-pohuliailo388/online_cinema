from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, model_validator

from src.cart.models import CartItem
from src.movies.schemas import GenreRead


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

    @model_validator(mode="before")
    @classmethod
    def movie_data_validator(cls, value: CartItem | dict) -> dict:
        if isinstance(value, dict):
            return value
        return {
            "movie_id": value.movie_id,
            "name": value.movie.name,
            "price": value.movie.price,
            "genres": value.movie.genres,
            "year": value.movie.year,
            "added_at": value.added_at,
        }


class CartReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cart_items: list[CartItemReadSchema]
