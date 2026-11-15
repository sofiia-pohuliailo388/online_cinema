
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.cart.models import CartItem
from src.core.exceptions import ConflictError, NotFoundError
from src.core.pagination import PaginationParams
from src.orders.models import Order, OrderItem, StatusEnum
from src.orders.service import (
    cancel_order,
    create_order,
    get_all_orders,
    get_order_by_id,
    get_user_orders,
    is_movie_purchased,
    is_movie_purchased_by_anyone,
    mark_order_paid,
)


async def test_create_order_success(
    db_session: AsyncSession, order_data: dict
) -> None:
    result = await create_order(db_session, order_data["user"].id)

    assert result["order"]["status"] == StatusEnum.PENDING
    assert result["order"]["total_amount"] == Decimal("12.50")
    assert result["excluded_movie_ids"] == []


async def test_create_order_empty_cart(
    db_session: AsyncSession, order_data: dict
) -> None:
    await db_session.execute(
        CartItem.__table__.delete().where(
            CartItem.cart_id == order_data["cart"].id
        )
    )
    await db_session.commit()

    with pytest.raises(ConflictError):
        await create_order(db_session, order_data["user"].id)


async def test_create_order_cart_not_found(
    db_session: AsyncSession, order_data: dict
) -> None:
    with pytest.raises(NotFoundError):
        await create_order(db_session, user_id=999)


async def test_create_order_duplicate_pending_movie(
    db_session: AsyncSession, order_data: dict
) -> None:
    await create_order(db_session, order_data["user"].id)

    with pytest.raises(ConflictError):
        await create_order(db_session, order_data["user"].id)


async def test_create_order_already_purchased_movie(
    db_session: AsyncSession, order_data: dict
) -> None:
    order = Order(
        user_id=order_data["user"].id,
        status=StatusEnum.PAID,
    )
    db_session.add(order)
    await db_session.flush()

    db_session.add(
        OrderItem(
            order_id=order.id,
            movie_id=order_data["movie"].id,
            price_at_order=Decimal("12.50"),
        )
    )
    await db_session.commit()

    with pytest.raises(ConflictError):
        await create_order(db_session, order_data["user"].id)


async def test_is_movie_purchased_true(
    db_session: AsyncSession, order_data: dict
) -> None:
    order = Order(
        user_id=order_data["user"].id,
        status=StatusEnum.PAID,
    )
    db_session.add(order)
    await db_session.flush()

    db_session.add(
        OrderItem(
            order_id=order.id,
            movie_id=order_data["movie"].id,
            price_at_order=Decimal("12.50"),
        )
    )
    await db_session.commit()

    assert await is_movie_purchased(
        db_session, order_data["user"].id, order_data["movie"].id
    )


async def test_is_movie_purchased_false(
    db_session: AsyncSession, order_data: dict
) -> None:
    assert not await is_movie_purchased(
        db_session, order_data["user"].id, order_data["movie"].id
    )


async def test_is_movie_purchased_by_anyone(
    db_session: AsyncSession, order_data: dict
) -> None:
    order = Order(
        user_id=order_data["user"].id,
        status=StatusEnum.PAID,
    )
    db_session.add(order)
    await db_session.flush()

    db_session.add(
        OrderItem(
            order_id=order.id,
            movie_id=order_data["movie"].id,
            price_at_order=Decimal("12.50"),
        )
    )
    await db_session.commit()

    assert await is_movie_purchased_by_anyone(
        db_session, order_data["movie"].id
    )


async def test_cancel_pending_order(
    db_session: AsyncSession, order_data: dict
) -> None:
    result = await create_order(db_session, order_data["user"].id)

    order = await cancel_order(
        db_session,
        order_data["user"].id,
        result["order"]["id"],
    )

    assert order.status == StatusEnum.CANCELED


async def test_cancel_paid_order(
    db_session: AsyncSession, order_data: dict
) -> None:
    result = await create_order(db_session, order_data["user"].id)
    order_id = result["order"]["id"]

    await mark_order_paid(db_session, order_id)

    with pytest.raises(ConflictError):
        await cancel_order(
            db_session, order_data["user"].id, order_id
        )


async def test_cancel_order_not_found(
    db_session: AsyncSession, order_data: dict
) -> None:
    with pytest.raises(NotFoundError):
        await cancel_order(db_session, order_data["user"].id, 999)


async def test_mark_order_paid(
    db_session: AsyncSession, order_data: dict
) -> None:
    result = await create_order(db_session, order_data["user"].id)
    order_id = result["order"]["id"]

    await mark_order_paid(db_session, order_id)

    order = await db_session.get(Order, order_id)
    assert order.status == StatusEnum.PAID

    remaining_items = (
        await db_session.scalars(
            select(CartItem).where(
                CartItem.cart_id == order_data["cart"].id
            )
        )
    ).all()

    assert remaining_items == []


async def test_mark_order_paid_twice(
    db_session: AsyncSession, order_data: dict
) -> None:
    result = await create_order(db_session, order_data["user"].id)
    order_id = result["order"]["id"]

    await mark_order_paid(db_session, order_id)
    await mark_order_paid(db_session, order_id)

    order = await db_session.get(Order, order_id)

    assert order.status == StatusEnum.PAID


async def test_mark_canceled_order_paid(
    db_session: AsyncSession, order_data: dict
) -> None:
    result = await create_order(db_session, order_data["user"].id)
    order_id = result["order"]["id"]

    await cancel_order(db_session, order_data["user"].id, order_id)

    with pytest.raises(ConflictError):
        await mark_order_paid(db_session, order_id)


async def test_get_user_orders(
    db_session: AsyncSession, order_data: dict
) -> None:
    await create_order(db_session, order_data["user"].id)

    orders, total = await get_user_orders(
        db_session,
        order_data["user"].id,
        PaginationParams(page=1, per_page=20),
    )

    assert total == 1
    assert len(orders) == 1


async def test_get_order_by_id(
    db_session: AsyncSession, order_data: dict
) -> None:
    result = await create_order(db_session, order_data["user"].id)

    order = await get_order_by_id(
        db_session,
        order_data["user"].id,
        result["order"]["id"],
    )

    assert order.id == result["order"]["id"]


async def test_get_all_orders(
    db_session: AsyncSession, order_data: dict
) -> None:
    await create_order(db_session, order_data["user"].id)

    orders, total = await get_all_orders(
        db_session,
        PaginationParams(page=1, per_page=20),
        status=StatusEnum.PENDING,
    )

    assert total == 1
    assert len(orders) == 1
    assert orders[0].status == StatusEnum.PENDING
