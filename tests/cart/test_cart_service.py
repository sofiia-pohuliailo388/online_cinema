from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from src.movies.models import Movie
from src.cart.models import Cart, CartItem
from src.cart.service import (
    add_movie_in_cart,
    get_cart_with_items,
    remove_movie_from_cart,
    clear_cart,
    is_movie_in_carts
)
from src.core.exceptions import ConflictError, NotFoundError


@pytest.mark.asyncio
async def test_add_movie_creates_cart(db_session, movie, test_user):
    cart_item = await add_movie_in_cart(
        db_session,
        movie_id=movie.id,
        user_id=test_user.id,
    )

    cart = await db_session.scalar(
        select(Cart).where(Cart.user_id == test_user.id)
    )

    assert cart is not None
    assert cart_item.cart_id == cart.id
    assert cart_item.movie_id == movie.id


@pytest.mark.asyncio
async def test_add_same_movie_twice(db_session, movie, test_user):
    await add_movie_in_cart(db_session, movie.id, test_user.id)

    with pytest.raises(ConflictError):
        await add_movie_in_cart(db_session, movie.id, test_user.id)


@pytest.mark.asyncio
async def test_add_nonexistent_movie(db_session, test_user):
    with pytest.raises(NotFoundError):
        await add_movie_in_cart(
            db_session,
            movie_id=999999,
            user_id=test_user.id,
        )


@pytest.mark.asyncio
async def test_add_second_movie_to_existing_cart(
    db_session, movie, test_user
):
    await add_movie_in_cart(db_session, movie.id, test_user.id)

    second_movie = Movie(
        name="Interstellar",
        year=2014,
        time=169,
        imdb=8.7,
        votes=200000,
        description="Science fiction",
        price="12.99",
        certification_id=movie.certification_id,
    )
    db_session.add(second_movie)
    await db_session.commit()

    second_item = await add_movie_in_cart(
        db_session, second_movie.id, test_user.id
    )

    cart = await db_session.scalar(
        select(Cart).where(Cart.user_id == test_user.id)
    )

    assert second_item.cart_id == cart.id
    assert len(
        (await db_session.scalars(
            select(CartItem).where(CartItem.cart_id == cart.id)
        )).all()
    ) == 2


@pytest.mark.asyncio
async def test_add_purchased_movie(db_session, movie, test_user):
    with patch(
        "src.cart.service.is_movie_purchased",
        new_callable=AsyncMock,
        return_value=True,
    ):
        with pytest.raises(ConflictError):
            await add_movie_in_cart(
                db_session, movie.id, test_user.id
            )


@pytest.mark.asyncio
async def test_get_cart_with_items(db_session, movie, test_user):
    await add_movie_in_cart(db_session, movie.id, test_user.id)

    cart = await get_cart_with_items(db_session, test_user.id)

    assert cart.user_id == test_user.id
    assert len(cart.cart_items) == 1
    assert cart.cart_items[0].movie.id == movie.id


@pytest.mark.asyncio
async def test_get_nonexistent_cart(db_session, test_user):
    with pytest.raises(NotFoundError):
        await get_cart_with_items(db_session, test_user.id)


@pytest.mark.asyncio
async def test_remove_movie_from_cart(db_session, movie, test_user):
    await add_movie_in_cart(db_session, movie.id, test_user.id)

    await remove_movie_from_cart(db_session, test_user.id, movie.id)

    cart = await get_cart_with_items(db_session, test_user.id)

    assert len(cart.cart_items) == 0


@pytest.mark.asyncio
async def test_remove_nonexistent_movie(db_session, movie, test_user):
    await add_movie_in_cart(db_session, movie.id, test_user.id)

    with pytest.raises(NotFoundError):
        await remove_movie_from_cart(
            db_session, test_user.id, movie_id=999999
        )


@pytest.mark.asyncio
async def test_clear_cart(db_session, movie, test_user):
    await add_movie_in_cart(db_session, movie.id, test_user.id)

    await clear_cart(db_session, test_user.id)

    cart = await get_cart_with_items(db_session, test_user.id)

    assert len(cart.cart_items) == 0


@pytest.mark.asyncio
async def test_is_movie_in_carts(db_session, movie, test_user):
    assert await is_movie_in_carts(db_session, movie.id) is False

    await add_movie_in_cart(db_session, movie.id, test_user.id)

    assert await is_movie_in_carts(db_session, movie.id) is True
