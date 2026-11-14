
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.cart.models import Cart, CartItem


@pytest.mark.asyncio
async def test_cart_user_id_unique(db_session, test_user):
    db_session.add(Cart(user_id=test_user.id))
    await db_session.commit()

    db_session.add(Cart(user_id=test_user.id))

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_cart_item_movie_unique(db_session, test_user, movie):
    cart = Cart(user_id=test_user.id)
    db_session.add(cart)
    await db_session.flush()

    db_session.add(
        CartItem(cart_id=cart.id, movie_id=movie.id)
    )
    await db_session.commit()

    db_session.add(
        CartItem(cart_id=cart.id, movie_id=movie.id)
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_same_movie_in_different_carts(db_session, test_user, movie):
    # Другий користувач потрібен для другого кошика.
    # У цьому тесті перевіряємо, що обмеження діє
    # на пару (cart_id, movie_id), а не лише movie_id.
    from src.accounts.models import User

    second_user = User(
        email="second_cart_user@test.com",
        hashed_password="test_hash",
        is_active=True,
        group_id=test_user.group_id,
    )
    db_session.add(second_user)
    await db_session.flush()

    first_cart = Cart(user_id=test_user.id)
    second_cart = Cart(user_id=second_user.id)
    db_session.add_all([first_cart, second_cart])
    await db_session.flush()

    db_session.add_all([
        CartItem(cart_id=first_cart.id, movie_id=movie.id),
        CartItem(cart_id=second_cart.id, movie_id=movie.id),
    ])

    await db_session.commit()

    items = (
        await db_session.scalars(
            select(CartItem).where(CartItem.movie_id == movie.id)
        )
    ).all()

    assert len(items) == 2
    assert items[0].cart_id != items[1].cart_id
