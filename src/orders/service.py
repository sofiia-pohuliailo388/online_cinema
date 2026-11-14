"""Business logic of the orders domain (owner: P6)."""
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from cart.models import Cart, CartItem
from core.exceptions import NotFoundError, ConflictError
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
