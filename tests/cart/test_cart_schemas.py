
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.cart.schemas import (
    CartItemCreateSchema,
    CartItemReadSchema,
    CartReadSchema,
)
from src.cart.service import add_movie_in_cart, get_cart_with_items


def test_create_schema_valid_movie_id():
    schema = CartItemCreateSchema(movie_id=5)

    assert schema.movie_id == 5


def test_create_schema_missing_movie_id():
    with pytest.raises(ValidationError):
        CartItemCreateSchema()


@pytest.mark.parametrize("movie_id", ["abc", None, [], {}])
def test_create_schema_invalid_movie_id(movie_id):
    with pytest.raises(ValidationError):
        CartItemCreateSchema(movie_id=movie_id)


@pytest.mark.asyncio
async def test_read_schema_from_orm(db_session, movie, test_user):
    await add_movie_in_cart(db_session, movie.id, test_user.id)

    cart = await get_cart_with_items(db_session, test_user.id)
    item = cart.cart_items[0]

    schema = CartItemReadSchema.model_validate(item)

    assert schema.movie_id == movie.id
    assert schema.name == movie.name
    assert schema.price == Decimal("9.99")
    assert schema.year == movie.year
    assert schema.genres == []
    assert schema.added_at == item.added_at


@pytest.mark.asyncio
async def test_cart_read_schema(db_session, movie, test_user):
    await add_movie_in_cart(db_session, movie.id, test_user.id)

    cart = await get_cart_with_items(db_session, test_user.id)

    schema = CartReadSchema.model_validate(cart)

    assert len(schema.cart_items) == 1
    assert schema.cart_items[0].movie_id == movie.id


def test_empty_cart_schema():
    schema = CartReadSchema(cart_items=[])

    assert schema.cart_items == []
