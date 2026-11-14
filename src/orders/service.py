"""Business logic of the orders domain (owner: P6)."""
from decimal import Decimal

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from cart.models import Cart, CartItem
from cart.service import get_cart_with_items
from core.exceptions import NotFoundError, ConflictError
from movies.models import Movie
from orders.models import Order, OrderItem, StatusEnum


async def is_movie_purchased(db: AsyncSession, user_id: int, movie_id: int) -> bool:
    """CONTRACT: has the user a PAID order containing this movie?    """
    return bool(
        await db.scalar(
            select(
                select(Order.id)
                .join(OrderItem, Order.id == OrderItem.order_id)
                .where(
                    Order.user_id == user_id,
                    Order.status == StatusEnum.PAID,
                    OrderItem.movie_id == movie_id
                )
                .exists()
            )
        )
    )


async def is_movie_purchased_by_anyone(db: AsyncSession, movie_id: int) -> bool:
    """CONTRACT for P4: forbid deleting a movie that somebody has bought.    """
    return bool(
        await db.scalar(
            select(
                select(Order.id)
                .join(OrderItem, Order.id == OrderItem.order_id)
                .where(
                    Order.status == StatusEnum.PAID,
                    OrderItem.movie_id == movie_id
                )
                .exists()
            )
        )
    )


async def mark_order_paid(db: AsyncSession, order_id: int) -> None:
    """CONTRACT for P7: set status to ``paid`` and remove paid movies from the user's cart.

    Called from the Stripe webhook. Must be idempotent (safe to call twice).    """
    order = await db.scalar(select(Order).where(Order.id == order_id))
    if order is None:
        raise NotFoundError(f"Order {order_id} is not found")

    if order.status == StatusEnum.CANCELED:
        raise ConflictError(f"Order {order_id} is canceled")

    order.status = StatusEnum.PAID

    order_items = await db.scalars(select(OrderItem).where(OrderItem.order_id == order_id))

    movies_paid_ids = [order_item.movie_id for order_item in order_items]

    cart = await db.scalar(select(Cart).where(Cart.user_id == order.user_id))

    if cart is not None:
        stmt = (
            delete(CartItem)
            .where(
                CartItem.cart_id == cart.id,
                CartItem.movie_id.in_(movies_paid_ids)
            )
        )

        await db.execute(stmt)
        await db.commit()


async def create_order(db: AsyncSession, user_id: int):
    cart = await get_cart_with_items(db, user_id)
    if cart is None:
        raise NotFoundError("Cart is not found")

    if not cart.cart_items:
        raise ConflictError("Cart is empty")

    movie_ids = [cart_item.movie_id for cart_item in cart.cart_items]

    stmt = (
        select(OrderItem.movie_id).
        join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.user_id == user_id,
            Order.status == StatusEnum.PAID,
            OrderItem.movie_id.in_(movie_ids)
        )
    )

    purchased_movie_ids = set((await db.scalars(stmt)).all())

    not_purchased_movie_ids = [
        cart_item.movie_id
        for cart_item in cart.cart_items
        if cart_item.movie_id not in purchased_movie_ids
    ]

    if not not_purchased_movie_ids:
        raise ConflictError("All movies in the cart have already been purchased")

    pending_movie_ids = set(
        (await db.scalars(
            select(OrderItem.movie_id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.user_id == user_id,
                Order.status == StatusEnum.PENDING,
                OrderItem.movie_id.in_(not_purchased_movie_ids)
            )
        )).all()
    )

    if pending_movie_ids:
        raise ConflictError(f"Movies {pending_movie_ids} are already in pending orders")

    movies = (await db.scalars(select(Movie).where(Movie.id.in_(not_purchased_movie_ids)))).all()

    if len(movies) != len(not_purchased_movie_ids):
        raise NotFoundError("Some movies were not found")

    order = Order(user_id=user_id)
    db.add(order)
    await db.flush()

    order_items = [OrderItem(order_id=order.id, movie_id=movie.id, price_at_order=movie.price) for movie in movies]
    db.add_all(order_items)

    order.total_amount = sum(
        (order_item.price_at_order for order_item in order_items),
        Decimal("0.00")
    )

    await db.commit()

    return {
        "order": {
            "id": order.id,
            "status": order.status,
            "total_amount": order.total_amount
        },
        "excluded_movie_ids": list(purchased_movie_ids)
    }
