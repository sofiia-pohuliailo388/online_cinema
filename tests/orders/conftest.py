
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.enums import UserGroupEnum
from src.accounts.models import User, UserGroup
from src.cart.models import Cart, CartItem
from src.movies.models import Certification, Movie


@pytest.fixture
async def order_data(db_session: AsyncSession) -> dict:
    group = UserGroup(name=UserGroupEnum.USER)
    db_session.add(group)
    await db_session.flush()

    user = User(
        id=1,
        email="orders@test.com",
        hashed_password="test-hash",
        is_active=True,
        group_id=group.id,
    )
    certification = Certification(name="PG-13")

    db_session.add_all([user, certification])
    await db_session.flush()

    movie = Movie(
        name="Test Movie",
        year=2024,
        time=120,
        imdb=8.0,
        votes=100,
        description="Test movie",
        price=Decimal("12.50"),
        certification_id=certification.id,
    )
    db_session.add(movie)
    await db_session.flush()

    cart = Cart(user_id=user.id)
    db_session.add(cart)
    await db_session.flush()

    db_session.add(
        CartItem(cart_id=cart.id, movie_id=movie.id)
    )
    await db_session.commit()

    return {
        "user": user,
        "movie": movie,
        "cart": cart,
    }
