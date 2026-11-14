
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.enums import UserGroupEnum
from src.accounts.models import User, UserGroup
from src.movies.models import Certification, Movie
from src.orders.models import Order, OrderItem, StatusEnum


async def create_test_data(db_session: AsyncSession) -> tuple[User, Movie]:
    group = UserGroup(name=UserGroupEnum.USER)
    db_session.add(group)
    await db_session.flush()

    user = User(
        email="test@example.com",
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
        description="Test description",
        price=Decimal("12.50"),
        certification_id=certification.id,
    )
    db_session.add(movie)
    await db_session.flush()

    return user, movie


async def test_create_order_with_default_status(
    db_session: AsyncSession,
) -> None:
    user, _ = await create_test_data(db_session)

    order = Order(user_id=user.id)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    assert order.id is not None
    assert order.user_id == user.id
    assert order.status == StatusEnum.PENDING
    assert order.created_at is not None


async def test_create_order_item(
    db_session: AsyncSession,
) -> None:
    user, movie = await create_test_data(db_session)

    order = Order(
        user_id=user.id,
        total_amount=Decimal("12.50"),
    )
    db_session.add(order)
    await db_session.flush()

    item = OrderItem(
        order_id=order.id,
        movie_id=movie.id,
        price_at_order=Decimal("12.50"),
    )
    db_session.add(item)
    await db_session.commit()

    saved_item = await db_session.scalar(
        select(OrderItem).where(OrderItem.id == item.id)
    )

    assert saved_item is not None
    assert saved_item.order_id == order.id
    assert saved_item.movie_id == movie.id
    assert saved_item.price_at_order == Decimal("12.50")


async def test_order_status_can_be_changed(
    db_session: AsyncSession,
) -> None:
    user, _ = await create_test_data(db_session)

    order = Order(user_id=user.id)
    db_session.add(order)
    await db_session.commit()

    order.status = StatusEnum.PAID
    await db_session.commit()
    await db_session.refresh(order)

    assert order.status == StatusEnum.PAID
