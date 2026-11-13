"""Business logic of the cart domain (owner: P6)."""
from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.cart.models import Cart, CartItem
from src.core.exceptions import NotFoundError, ConflictError
from src.movies.models import Movie
from src.movies.service import get_movie
from src.orders.service import is_movie_purchased


async def is_movie_in_carts(db: AsyncSession, movie_id: int) -> bool:
    """CONTRACT for P4: is the movie in at least one user's cart?

    Used to warn a moderator before deleting a movie.
    """
    return bool(await db.scalar(select(exists().where(CartItem.movie_id == movie_id))))


async def get_cart_by_user_id(db: AsyncSession, user_id: int) -> Cart | None:
    return await db.scalar(select(Cart).where(Cart.user_id == user_id))


async def add_movie_in_cart(db: AsyncSession, movie_id: int, user_id: int) -> CartItem:
    if await get_movie(db, movie_id) is None:
        raise NotFoundError(f"Movie {movie_id} is not found")

    if await is_movie_purchased(db, user_id, movie_id):
        raise ConflictError(f"Movie {movie_id} is already purchased")

    cart = await get_cart_by_user_id(db, user_id)

    if cart is not None:
        if await db.scalar(
                select(CartItem).where(
                    CartItem.cart_id == cart.id,
                    CartItem.movie_id == movie_id
                )
        ):
            raise ConflictError(f"Movie {movie_id} already in cart {cart.id}")
    else:
        cart = Cart(user_id=user_id)
        db.add(cart)
        await db.flush()

    cart_item = CartItem(cart_id=cart.id, movie_id=movie_id)
    db.add(cart_item)
    await db.commit()

    return cart_item


async def get_cart_with_items(db: AsyncSession, user_id: int) -> Cart:
    cart = await db.scalar(
        select(Cart).options(selectinload(
            Cart.cart_items)
            .selectinload(CartItem.movie)
            .selectinload(Movie.genres)
        ).where(Cart.user_id == user_id)
    )
    if cart is None:
        raise NotFoundError("Cart is not found")

    return cart


async def remove_movie_from_cart(db: AsyncSession, user_id: int, movie_id: int) -> None:
    cart = await db.scalar(select(Cart).where(Cart.user_id == user_id))
    if cart is None:
        raise NotFoundError("Cart is not found")

    cart_item = await db.scalar(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.movie_id == movie_id
        )
    )

    if cart_item is None:
        raise NotFoundError("Cart item is not found")

    await db.delete(cart_item)
    await db.commit()


async def clear_cart(db: AsyncSession, user_id: int) -> None:
    cart = await db.scalar(select(Cart).where(Cart.user_id == user_id))
    if cart is None:
        raise NotFoundError("Cart is not found")

    cart_items = await db.scalars(select(CartItem).where(CartItem.cart_id == cart.id))

    for cart_item in cart_items:
        await db.delete(cart_item)

    await db.commit()
