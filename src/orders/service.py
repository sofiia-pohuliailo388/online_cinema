"""Business logic of the orders domain (owner: P6)."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.cart.models import Cart, CartItem
from src.core.exceptions import NotFoundError, ConflictError
from src.core.pagination import PaginationParams, paginate
from src.movies.models import Movie
from src.orders.models import Order, OrderItem, StatusEnum


async def is_movie_purchased(db: AsyncSession, user_id: int, movie_id: int) -> bool:
    """Check whether a user has purchased a movie.

    Returns:
        True if the user has a paid order containing the movie.
    """
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
    """Check whether a movie has been purchased by any user.

    Returns:
        True if at least one paid order contains the movie.
    """
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
    """Mark an order as paid and remove purchased movies from the cart.

    Repeated calls for an already paid order have no effect.

    Raises:
        NotFoundError: If the order does not exist.
        ConflictError: If the order has been canceled.
    """
    order = await db.scalar(select(Order).where(Order.id == order_id))
    if order is None:
        raise NotFoundError(f"Order {order_id} is not found")

    if order.status == StatusEnum.CANCELED:
        raise ConflictError(f"Order {order_id} is canceled")

    if order.status == StatusEnum.PAID:
        return

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


async def create_order(db: AsyncSession, user_id: int) -> dict:
    """Create an order from the user's cart.

    Exclude previously purchased movies and calculate the order total.

    Returns:
        Order details and IDs of excluded purchased movies.

    Raises:
        NotFoundError: If the cart or required movies do not exist.
        ConflictError: If the cart is empty, all movies are purchased,
            or selected movies exist in pending orders.
    """
    cart = await db.scalar(
        select(Cart)
        .where(Cart.user_id == user_id)
        .options(selectinload(Cart.cart_items))
    )
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

    order_items = [
        OrderItem(
            order_id=order.id,
            movie_id=movie.id,
            price_at_order=movie.price
        )
        for movie in movies
    ]
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


async def cancel_order(db: AsyncSession, user_id: int, order_id: int) -> Order:
    """Cancel a user's pending order.

    Returns:
        The canceled order.

    Raises:
        NotFoundError: If the order does not belong to the user or does not exist.
        ConflictError: If the order is already paid or canceled.
    """
    order = await db.scalar(
        select(Order)
        .where(Order.user_id == user_id, Order.id == order_id)
        .options(selectinload(Order.order_items))
    )
    if order is None:
        raise NotFoundError("Order is not found")
    if order.status == StatusEnum.CANCELED:
        raise ConflictError("Order is already canceled")
    if order.status == StatusEnum.PAID:
        raise ConflictError("Order is already paid")
    if order.status == StatusEnum.PENDING:
        order.status = StatusEnum.CANCELED

    await db.commit()

    return order


async def get_user_orders(
        db: AsyncSession,
        user_id: int,
        pagination: PaginationParams
) -> tuple[list[Order], int]:
    """Retrieve a user's orders with pagination.

    Returns:
        A tuple containing the orders and their total count.
    """
    stmt = (
        select(Order)
        .where(Order.user_id == user_id)
        .options(selectinload(Order.order_items))
        .order_by(Order.created_at.desc())
    )
    orders, total = await paginate(db, stmt, pagination)

    return orders, total


async def get_order_by_id(db: AsyncSession, user_id: int, order_id: int) -> Order:
    """Retrieve a specific order belonging to the user.

    Raises:
        NotFoundError: If the order does not exist or belongs to another user.
    """
    order = await db.scalar(
        select(Order)
        .where(
            Order.user_id == user_id,
            Order.id == order_id
        )
        .options(selectinload(Order.order_items))
    )
    if order is None:
        raise NotFoundError(f"Order {order_id} is not found")

    return order


async def get_all_orders(
        db: AsyncSession,
        pagination: PaginationParams,
        user_id: int | None = None,
        status: StatusEnum | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
) -> tuple[list[Order], int]:
    """Retrieve paginated orders with optional administrative filters.

    Filter by user, status, and creation date range.

    Returns:
        A tuple containing the filtered orders and their total count.
    """
    stmt = select(Order)
    if user_id is not None:
        stmt = stmt.where(Order.user_id == user_id)

    if status is not None:
        stmt = stmt.where(Order.status == status)

    if date_from is not None:
        stmt = stmt.where(Order.created_at >= date_from)

    if date_to is not None:
        stmt = stmt.where(Order.created_at <= date_to)

    stmt = stmt.options(selectinload(Order.order_items)).order_by(Order.created_at.desc())

    orders, total = await paginate(db, stmt, pagination)

    return orders, total
